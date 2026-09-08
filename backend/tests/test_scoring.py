from datetime import datetime, timezone
import unittest

from app.analyzer.scoring import overall_health_score, score_scan
from app.schemas import ScanResult


def scan(classification: str, redirect_count: int = 0, error_type: str | None = None) -> ScanResult:
    return ScanResult(
        id=1,
        resource_id=1,
        status_code=200,
        response_time_ms=100,
        final_url="https://example.com",
        redirect_count=redirect_count,
        ssl_valid=True,
        error_type=error_type,
        classification=classification,
        scanned_at=datetime.now(timezone.utc),
    )


class ScoringTests(unittest.TestCase):
    def test_healthy_scan_scores_100(self) -> None:
        self.assertEqual(score_scan(scan("healthy")), 100)

    def test_warning_redirect_is_penalized(self) -> None:
        self.assertEqual(score_scan(scan("warning", redirect_count=3)), 80)

    def test_overall_score_averages_latest_scans(self) -> None:
        self.assertEqual(overall_health_score([scan("healthy"), scan("critical")]), 80)


if __name__ == "__main__":
    unittest.main()
