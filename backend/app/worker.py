"""
Celery Worker Configuration

Configures Celery for background task processing including:
- Crawl jobs
- SEO audits
- Keyword research
- Content generation
- Report generation
"""

from celery import Celery
from celery.schedules import crontab

from app.config import settings


# Create Celery app
celery_app = Celery(
    "seoman",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.crawl_tasks",
        "app.tasks.audit_tasks",
        "app.tasks.keyword_tasks",
        "app.tasks.content_tasks",
        "app.tasks.export_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 min soft limit
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    worker_max_tasks_per_child=100,
    
    # Result backend settings
    result_expires=86400,  # 24 hours
    result_extended=True,
    
    # Rate limiting
    task_default_rate_limit="100/m",
    
    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # Queue routing
    task_routes={
        "app.tasks.crawl_tasks.*": {"queue": "crawl"},
        "app.tasks.audit_tasks.*": {"queue": "audit"},
        "app.tasks.keyword_tasks.*": {"queue": "keyword"},
        "app.tasks.content_tasks.*": {"queue": "content"},
        "app.tasks.export_tasks.*": {"queue": "export"},
    },
    
    # Default queue
    task_default_queue="default",
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Check for stale crawl jobs every 5 minutes
    "check-stale-crawls": {
        "task": "app.tasks.crawl_tasks.check_stale_crawls",
        "schedule": crontab(minute="*/5"),
    },
    
    # Process scheduled audits every hour
    "process-scheduled-audits": {
        "task": "app.tasks.audit_tasks.process_scheduled_audits",
        "schedule": crontab(minute=0),
    },
    
    # Update keyword rankings daily at 3 AM
    "update-keyword-rankings": {
        "task": "app.tasks.keyword_tasks.update_all_rankings",
        "schedule": crontab(hour=3, minute=0),
    },
    
    # Clean up old exports weekly
    "cleanup-old-exports": {
        "task": "app.tasks.export_tasks.cleanup_old_exports",
        "schedule": crontab(day_of_week=0, hour=2, minute=0),
    },
    
    # Generate weekly reports every Monday at 6 AM
    "generate-weekly-reports": {
        "task": "app.tasks.export_tasks.generate_weekly_reports",
        "schedule": crontab(day_of_week=1, hour=6, minute=0),
    },
}


# Task base class with common functionality
class SEOmanTask(celery_app.Task):
    """Base task class with error handling and logging."""
    
    abstract = True
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        # Log failure
        self.update_state(
            state="FAILURE",
            meta={
                "exc_type": type(exc).__name__,
                "exc_message": str(exc),
            }
        )
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry."""
        pass
    
    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        pass


# Register base class
celery_app.Task = SEOmanTask
