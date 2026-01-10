"""
Alert Tasks

Background tasks for monitoring and alert processing.
"""
import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

import httpx
from celery import shared_task
from sqlalchemy import select

from app.database import async_session_maker
from app.models.alert import (
    AlertEvent,
    AlertEventStatus,
    AlertRule,
    AlertSeverity,
    AlertType,
    UptimeCheck,
)
from app.models.audit import AuditRun
from app.models.crawl import CrawlJob, CrawlPage, JobStatus
from app.models.keyword import Keyword
from app.services.alert_service import AlertService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# === Uptime Monitoring ===


@shared_task(bind=True)
def check_site_uptime(self):
    """Check uptime for all sites with active uptime rules."""
    return run_async(_check_site_uptime())


async def _check_site_uptime():
    """Check uptime for sites with uptime alert rules."""
    async with async_session_maker() as session:
        service = AlertService(session)
        notification_service = NotificationService()

        # Get all active uptime rules
        rules = await service.get_active_rules_by_type(AlertType.UPTIME)

        logger.info(f"[ALERTS] Checking uptime for {len(rules)} rules")

        results = []
        for rule in rules:
            try:
                result = await _check_single_site_uptime(
                    session, service, notification_service, rule
                )
                results.append(result)
            except Exception as e:
                logger.error(f"[ALERTS] Error checking uptime for rule {rule.id}: {e}")
                results.append({"rule_id": str(rule.id), "error": str(e)})

        await session.commit()
        return {"checked": len(rules), "results": results}


async def _check_single_site_uptime(
    session, service: AlertService, notifier: NotificationService, rule: AlertRule
):
    """Check uptime for a single site."""
    site = rule.site
    url = f"https://{site.primary_domain}"

    conditions = rule.conditions
    timeout = conditions.get("timeout_seconds", 30)
    consecutive_failures = conditions.get("consecutive_failures", 2)

    # Perform HTTP check
    is_up = False
    status_code = None
    response_time_ms = None
    error_message = None

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            start = datetime.now(timezone.utc)
            response = await client.get(url)
            elapsed = datetime.now(timezone.utc) - start

            status_code = response.status_code
            response_time_ms = int(elapsed.total_seconds() * 1000)
            is_up = 200 <= status_code < 400

    except httpx.TimeoutException:
        error_message = "Request timeout"
    except httpx.ConnectError:
        error_message = "Connection refused"
    except Exception as e:
        error_message = str(e)

    # Record the check
    await service.record_uptime_check(
        site, is_up, status_code, response_time_ms, error_message
    )

    # Check if we should trigger an alert
    if not is_up:
        recent_failures = await service.get_recent_downtime_count(
            site.id, consecutive_failures
        )

        if recent_failures >= consecutive_failures:
            # Check cooldown
            if await service.can_trigger_alert(rule):
                # Create alert event
                event = await service.create_event(
                    rule=rule,
                    severity=AlertSeverity.CRITICAL,
                    title=f"Site Down: {site.primary_domain}",
                    message=f"The site {site.primary_domain} is not responding.",
                    details={
                        "url": url,
                        "status_code": status_code,
                        "error": error_message,
                        "consecutive_failures": recent_failures,
                    },
                )

                # Send notifications
                notification_results = await notifier.send_notifications(event, rule)
                event.notifications_sent = notification_results

                logger.warning(f"[ALERTS] Alert triggered: Site down - {site.primary_domain}")

    return {
        "rule_id": str(rule.id),
        "site": site.primary_domain,
        "is_up": is_up,
        "status_code": status_code,
        "response_time_ms": response_time_ms,
    }


# === Ranking Drop Monitoring ===


@shared_task(bind=True)
def check_ranking_drops(self):
    """Check for ranking drops after daily ranking update."""
    return run_async(_check_ranking_drops())


async def _check_ranking_drops():
    """Check for significant ranking drops."""
    async with async_session_maker() as session:
        service = AlertService(session)
        notification_service = NotificationService()

        # Get all active ranking drop rules
        rules = await service.get_active_rules_by_type(AlertType.RANKING_DROP)

        logger.info(f"[ALERTS] Checking ranking drops for {len(rules)} rules")

        alerts_triggered = 0
        for rule in rules:
            try:
                triggered = await _check_ranking_drops_for_rule(
                    session, service, notification_service, rule
                )
                if triggered:
                    alerts_triggered += 1
            except Exception as e:
                logger.error(
                    f"[ALERTS] Error checking ranking drops for rule {rule.id}: {e}"
                )

        await session.commit()
        return {"rules_checked": len(rules), "alerts_triggered": alerts_triggered}


async def _check_ranking_drops_for_rule(
    session, service: AlertService, notifier: NotificationService, rule: AlertRule
):
    """Check ranking drops for a single rule."""
    conditions = rule.conditions
    position_drop_threshold = conditions.get("position_drop", 10)
    keyword_ids = conditions.get("keyword_ids")  # None = all tracked keywords
    min_position = conditions.get("min_position", 100)

    site = rule.site

    # Build query for keywords
    query = select(Keyword).where(
        Keyword.site_id == site.id,
        Keyword.is_tracked == True,
        Keyword.current_position.isnot(None),
        Keyword.previous_position.isnot(None),
    )

    if keyword_ids:
        query = query.where(Keyword.id.in_([UUID(kid) for kid in keyword_ids]))

    result = await session.execute(query)
    keywords = result.scalars().all()

    # Find keywords with significant drops
    significant_drops = []
    for kw in keywords:
        if kw.previous_position and kw.previous_position <= min_position:
            drop = kw.current_position - kw.previous_position
            if drop >= position_drop_threshold:
                significant_drops.append(
                    {
                        "keyword": kw.text,
                        "old_position": kw.previous_position,
                        "new_position": kw.current_position,
                        "drop": drop,
                    }
                )

    if significant_drops and await service.can_trigger_alert(rule):
        # Create alert event
        top_drops = sorted(significant_drops, key=lambda x: x["drop"], reverse=True)[
            :5
        ]

        severity = (
            AlertSeverity.WARNING
            if len(significant_drops) < 5
            else AlertSeverity.CRITICAL
        )

        event = await service.create_event(
            rule=rule,
            severity=severity,
            title=f"Ranking Drops Detected: {site.primary_domain}",
            message=f"{len(significant_drops)} keyword(s) dropped {position_drop_threshold}+ positions.",
            details={
                "total_drops": len(significant_drops),
                "top_drops": top_drops,
                "site": site.primary_domain,
            },
        )

        notification_results = await notifier.send_notifications(event, rule)
        event.notifications_sent = notification_results

        logger.warning(f"[ALERTS] Alert triggered: Ranking drops - {site.primary_domain}")
        return True

    return False


# === Audit Score Drop Monitoring ===


@shared_task(bind=True)
def check_audit_score_drops(self):
    """Check for audit score drops after audits complete."""
    return run_async(_check_audit_score_drops())


async def _check_audit_score_drops():
    """Check for audit score drops."""
    async with async_session_maker() as session:
        service = AlertService(session)
        notification_service = NotificationService()

        # Get all active audit score drop rules
        rules = await service.get_active_rules_by_type(AlertType.AUDIT_SCORE_DROP)

        logger.info(f"[ALERTS] Checking audit score drops for {len(rules)} rules")

        alerts_triggered = 0
        for rule in rules:
            try:
                triggered = await _check_audit_score_for_rule(
                    session, service, notification_service, rule
                )
                if triggered:
                    alerts_triggered += 1
            except Exception as e:
                logger.error(
                    f"[ALERTS] Error checking audit score for rule {rule.id}: {e}"
                )

        await session.commit()
        return {"rules_checked": len(rules), "alerts_triggered": alerts_triggered}


async def _check_audit_score_for_rule(
    session, service: AlertService, notifier: NotificationService, rule: AlertRule
):
    """Check audit score for a single rule."""
    conditions = rule.conditions
    threshold = conditions.get("threshold", 70)
    drop_percentage = conditions.get("drop_percentage")

    site = rule.site

    # Get last two completed audits
    result = await session.execute(
        select(AuditRun)
        .where(
            AuditRun.site_id == site.id,
            AuditRun.status == JobStatus.COMPLETED,
            AuditRun.score.isnot(None),
        )
        .order_by(AuditRun.completed_at.desc())
        .limit(2)
    )
    audits = result.scalars().all()

    if len(audits) < 2:
        return False

    current_score = audits[0].score
    previous_score = audits[1].score

    should_alert = False
    alert_reason = ""

    # Check threshold
    if current_score < threshold:
        should_alert = True
        alert_reason = f"Score dropped below threshold of {threshold}"

    # Check percentage drop
    if drop_percentage and previous_score > 0:
        actual_drop = ((previous_score - current_score) / previous_score) * 100
        if actual_drop >= drop_percentage:
            should_alert = True
            alert_reason = f"Score dropped by {actual_drop:.1f}%"

    if should_alert and await service.can_trigger_alert(rule):
        severity = (
            AlertSeverity.WARNING if current_score >= 50 else AlertSeverity.CRITICAL
        )

        event = await service.create_event(
            rule=rule,
            severity=severity,
            title=f"Audit Score Drop: {site.primary_domain}",
            message=alert_reason,
            details={
                "previous_score": previous_score,
                "current_score": current_score,
                "threshold": threshold,
                "audit_id": str(audits[0].id),
                "site": site.primary_domain,
            },
        )

        notification_results = await notifier.send_notifications(event, rule)
        event.notifications_sent = notification_results

        logger.warning(f"[ALERTS] Alert triggered: Audit score drop - {site.primary_domain}")
        return True

    return False


# === Index Status Monitoring ===


@shared_task(bind=True)
def check_index_status(self):
    """Check for deindexed pages."""
    return run_async(_check_index_status())


async def _check_index_status():
    """Check for pages that have been deindexed."""
    async with async_session_maker() as session:
        service = AlertService(session)
        notification_service = NotificationService()

        # Get all active index status rules
        rules = await service.get_active_rules_by_type(AlertType.INDEX_STATUS)

        logger.info(f"[ALERTS] Checking index status for {len(rules)} rules")

        alerts_triggered = 0
        for rule in rules:
            try:
                triggered = await _check_index_status_for_rule(
                    session, service, notification_service, rule
                )
                if triggered:
                    alerts_triggered += 1
            except Exception as e:
                logger.error(
                    f"[ALERTS] Error checking index status for rule {rule.id}: {e}"
                )

        await session.commit()
        return {"rules_checked": len(rules), "alerts_triggered": alerts_triggered}


async def _check_index_status_for_rule(
    session, service: AlertService, notifier: NotificationService, rule: AlertRule
):
    """Check index status for a single rule."""
    conditions = rule.conditions
    check_noindex = conditions.get("check_noindex", True)
    check_404 = conditions.get("check_404", True)
    deindex_threshold = conditions.get("check_deindex_count", 5)

    site = rule.site

    # Get the two most recent completed crawls
    result = await session.execute(
        select(CrawlJob)
        .where(
            CrawlJob.site_id == site.id,
            CrawlJob.status == JobStatus.COMPLETED,
        )
        .order_by(CrawlJob.completed_at.desc())
        .limit(2)
    )
    crawls = result.scalars().all()

    if len(crawls) < 2:
        return False

    current_crawl, previous_crawl = crawls[0], crawls[1]

    issues = []

    if check_noindex:
        # Find pages that were indexable before but now have noindex
        result = await session.execute(
            select(CrawlPage.url).where(
                CrawlPage.crawl_job_id == current_crawl.id,
                CrawlPage.noindex == True,
            )
        )
        current_noindex = set(row[0] for row in result.all())

        result = await session.execute(
            select(CrawlPage.url).where(
                CrawlPage.crawl_job_id == previous_crawl.id,
                CrawlPage.noindex == False,
            )
        )
        previous_indexable = set(row[0] for row in result.all())

        newly_noindex = current_noindex & previous_indexable
        if newly_noindex:
            issues.append(
                {
                    "type": "newly_noindex",
                    "urls": list(newly_noindex)[:10],
                    "count": len(newly_noindex),
                }
            )

    if check_404:
        # Find pages that now return 404
        result = await session.execute(
            select(CrawlPage.url).where(
                CrawlPage.crawl_job_id == current_crawl.id,
                CrawlPage.status_code == 404,
            )
        )
        current_404 = set(row[0] for row in result.all())

        result = await session.execute(
            select(CrawlPage.url).where(
                CrawlPage.crawl_job_id == previous_crawl.id,
                CrawlPage.status_code.between(200, 399),
            )
        )
        previous_ok = set(row[0] for row in result.all())

        newly_404 = current_404 & previous_ok
        if newly_404:
            issues.append(
                {
                    "type": "newly_404",
                    "urls": list(newly_404)[:10],
                    "count": len(newly_404),
                }
            )

    total_issues = sum(i["count"] for i in issues)

    if total_issues >= deindex_threshold and await service.can_trigger_alert(rule):
        severity = (
            AlertSeverity.WARNING if total_issues < 20 else AlertSeverity.CRITICAL
        )

        event = await service.create_event(
            rule=rule,
            severity=severity,
            title=f"Index Status Changes: {site.primary_domain}",
            message=f"{total_issues} page(s) have index status changes.",
            details={
                "total_issues": total_issues,
                "issues": issues,
                "site": site.primary_domain,
            },
        )

        notification_results = await notifier.send_notifications(event, rule)
        event.notifications_sent = notification_results

        logger.warning(
            f"[ALERTS] Alert triggered: Index status changes - {site.primary_domain}"
        )
        return True

    return False


# === Auto-resolve alerts ===


@shared_task(bind=True)
def auto_resolve_alerts(self):
    """Auto-resolve alerts when conditions are no longer met."""
    return run_async(_auto_resolve_alerts())


async def _auto_resolve_alerts():
    """Check active alerts and resolve if conditions improved."""
    async with async_session_maker() as session:
        # Get active uptime alerts for sites that are now up
        result = await session.execute(
            select(AlertEvent).where(
                AlertEvent.alert_type == AlertType.UPTIME,
                AlertEvent.status == AlertEventStatus.ACTIVE,
            )
        )
        uptime_alerts = result.scalars().all()

        resolved = 0
        for alert in uptime_alerts:
            # Check if site is now up
            result = await session.execute(
                select(UptimeCheck)
                .where(UptimeCheck.site_id == alert.site_id)
                .order_by(UptimeCheck.checked_at.desc())
                .limit(3)
            )
            recent_checks = result.scalars().all()

            if len(recent_checks) >= 3 and all(c.is_up for c in recent_checks):
                alert.status = AlertEventStatus.RESOLVED
                alert.resolved_at = datetime.now(timezone.utc)
                alert.resolution_notes = (
                    "Automatically resolved: Site is responding normally."
                )
                resolved += 1
                logger.info(f"[ALERTS] Auto-resolved uptime alert for site {alert.site_id}")

        await session.commit()
        return {"resolved": resolved}
