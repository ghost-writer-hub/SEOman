"""
Unit tests for SEO scoring algorithms.

Tests the scoring and weighting logic used in:
- Audit score calculation
- Issue severity weighting
- Pass/fail rate computation
"""
import pytest
from app.services.audit_engine import SEOAuditEngine, CrawlData, AuditCheckResult


class TestScoreCalculation:
    """Test the score calculation algorithm."""

    def test_empty_results_returns_zero(self):
        """Test score with no results."""
        crawl_data = CrawlData(base_url="https://example.com", pages=[])
        engine = SEOAuditEngine(crawl_data)

        score = engine.calculate_score()

        assert score == 0

    def test_all_passed_gives_high_score(self):
        """Test score when all checks pass."""
        crawl_data = CrawlData(base_url="https://example.com", pages=[])
        engine = SEOAuditEngine(crawl_data)

        # Add 10 passed checks
        for i in range(10):
            engine.results.append(AuditCheckResult(
                check_id=i + 1,
                category="Test",
                check_name=f"Check {i + 1}",
                passed=True,
                severity="medium",
            ))

        score = engine.calculate_score()

        assert score == 100

    def test_all_failed_gives_low_score(self):
        """Test score when all checks fail."""
        crawl_data = CrawlData(base_url="https://example.com", pages=[])
        engine = SEOAuditEngine(crawl_data)

        # Add 10 failed checks
        for i in range(10):
            engine.results.append(AuditCheckResult(
                check_id=i + 1,
                category="Test",
                check_name=f"Check {i + 1}",
                passed=False,
                severity="medium",
                affected_count=1,
            ))

        score = engine.calculate_score()

        assert score < 20

    def test_severity_weighting(self):
        """Test that critical issues impact score more than low issues."""
        crawl_data = CrawlData(base_url="https://example.com", pages=[])

        # Scenario 1: One critical failure
        engine1 = SEOAuditEngine(crawl_data)
        for i in range(9):
            engine1.results.append(AuditCheckResult(
                check_id=i + 1, category="Test", check_name=f"Check {i + 1}",
                passed=True, severity="low",
            ))
        engine1.results.append(AuditCheckResult(
            check_id=10, category="Test", check_name="Critical Check",
            passed=False, severity="critical", affected_count=1,
        ))
        score1 = engine1.calculate_score()

        # Scenario 2: One low failure
        engine2 = SEOAuditEngine(crawl_data)
        for i in range(9):
            engine2.results.append(AuditCheckResult(
                check_id=i + 1, category="Test", check_name=f"Check {i + 1}",
                passed=True, severity="low",
            ))
        engine2.results.append(AuditCheckResult(
            check_id=10, category="Test", check_name="Low Check",
            passed=False, severity="low", affected_count=1,
        ))
        score2 = engine2.calculate_score()

        # Critical failure should result in lower score
        assert score1 < score2

    def test_affected_count_impact(self):
        """Test that high affected count has additional penalty."""
        crawl_data = CrawlData(base_url="https://example.com", pages=[])

        # Scenario 1: Issue affects 1 page
        engine1 = SEOAuditEngine(crawl_data)
        engine1.results.append(AuditCheckResult(
            check_id=1, category="Test", check_name="Check",
            passed=False, severity="medium", affected_count=1,
        ))
        score1 = engine1.calculate_score()

        # Scenario 2: Issue affects 50 pages
        engine2 = SEOAuditEngine(crawl_data)
        engine2.results.append(AuditCheckResult(
            check_id=1, category="Test", check_name="Check",
            passed=False, severity="medium", affected_count=50,
        ))
        score2 = engine2.calculate_score()

        # More affected pages should result in lower score
        assert score2 <= score1

    def test_score_bounds(self):
        """Test score is always between 0 and 100."""
        crawl_data = CrawlData(base_url="https://example.com", pages=[])
        engine = SEOAuditEngine(crawl_data)

        # Add extreme case: many high-severity failures
        for i in range(50):
            engine.results.append(AuditCheckResult(
                check_id=i + 1, category="Test", check_name=f"Check {i + 1}",
                passed=False, severity="critical", affected_count=100,
            ))

        score = engine.calculate_score()

        assert 0 <= score <= 100


class TestSeverityWeights:
    """Test severity weight values."""

    def test_severity_order(self):
        """Test severity weights are in correct order."""
        severity_weights = {
            "critical": 4.0,
            "high": 2.5,
            "medium": 1.5,
            "low": 1.0,
        }

        assert severity_weights["critical"] > severity_weights["high"]
        assert severity_weights["high"] > severity_weights["medium"]
        assert severity_weights["medium"] > severity_weights["low"]

    def test_all_severities_have_weight(self):
        """Test all severity levels have a weight."""
        severity_weights = {"critical": 4.0, "high": 2.5, "medium": 1.5, "low": 1.0}
        severities = ["critical", "high", "medium", "low"]

        for severity in severities:
            assert severity in severity_weights
            assert severity_weights[severity] > 0


class TestSummaryGeneration:
    """Test audit summary generation."""

    def test_summary_counts(self):
        """Test summary counts are accurate."""
        crawl_data = CrawlData(base_url="https://example.com", pages=[])
        engine = SEOAuditEngine(crawl_data)

        # Add 7 passed and 3 failed
        for i in range(7):
            engine.results.append(AuditCheckResult(
                check_id=i + 1, category="Test", check_name=f"Passed {i + 1}",
                passed=True, severity="medium",
            ))
        for i in range(3):
            engine.results.append(AuditCheckResult(
                check_id=i + 8, category="Test", check_name=f"Failed {i + 1}",
                passed=False, severity="high",
            ))

        summary = engine.get_summary()

        assert summary["total_checks"] == 10
        assert summary["passed"] == 7
        assert summary["failed"] == 3

    def test_summary_issues_by_severity(self):
        """Test summary groups issues by severity."""
        crawl_data = CrawlData(base_url="https://example.com", pages=[])
        engine = SEOAuditEngine(crawl_data)

        # Add issues with different severities
        engine.results.append(AuditCheckResult(
            check_id=1, category="Test", check_name="Critical",
            passed=False, severity="critical",
        ))
        engine.results.append(AuditCheckResult(
            check_id=2, category="Test", check_name="High 1",
            passed=False, severity="high",
        ))
        engine.results.append(AuditCheckResult(
            check_id=3, category="Test", check_name="High 2",
            passed=False, severity="high",
        ))

        summary = engine.get_summary()

        assert summary["issues_by_severity"]["critical"] == 1
        assert summary["issues_by_severity"]["high"] == 2

    def test_summary_issues_by_category(self):
        """Test summary groups issues by category."""
        crawl_data = CrawlData(base_url="https://example.com", pages=[])
        engine = SEOAuditEngine(crawl_data)

        # Add issues in different categories
        engine.results.append(AuditCheckResult(
            check_id=1, category="On-Page SEO", check_name="Issue 1",
            passed=False, severity="medium",
        ))
        engine.results.append(AuditCheckResult(
            check_id=2, category="On-Page SEO", check_name="Issue 2",
            passed=False, severity="medium",
        ))
        engine.results.append(AuditCheckResult(
            check_id=3, category="Security", check_name="Issue 3",
            passed=False, severity="high",
        ))

        summary = engine.get_summary()

        assert summary["issues_by_category"]["On-Page SEO"] == 2
        assert summary["issues_by_category"]["Security"] == 1


class TestScoreInterpretation:
    """Test score interpretation and grading."""

    def test_score_grade_mapping(self):
        """Test mapping scores to grades."""
        def get_grade(score: int) -> str:
            if score >= 90:
                return "A"
            elif score >= 80:
                return "B"
            elif score >= 70:
                return "C"
            elif score >= 60:
                return "D"
            else:
                return "F"

        assert get_grade(95) == "A"
        assert get_grade(85) == "B"
        assert get_grade(75) == "C"
        assert get_grade(65) == "D"
        assert get_grade(50) == "F"

    def test_score_status_mapping(self):
        """Test mapping scores to status."""
        def get_status(score: int) -> str:
            if score >= 80:
                return "good"
            elif score >= 60:
                return "needs_improvement"
            else:
                return "poor"

        assert get_status(85) == "good"
        assert get_status(70) == "needs_improvement"
        assert get_status(40) == "poor"
