from app.schemas import ScanResult


PENALTIES = {
    "critical": 40,
    "warning": 10,
    "healthy": 0,
}


def score_scan(scan: ScanResult) -> int:
    score = 100 - PENALTIES.get(scan.classification, 20)

    if scan.error_type:
        if "timeout" in scan.error_type:
            score -= 20
        elif "ssl" in scan.error_type:
            score -= 10

    if scan.redirect_count >= 3:
        score -= 10

    return max(0, min(100, score))


def overall_health_score(scans: list[ScanResult]) -> int:
    if not scans:
        return 100
    return round(sum(score_scan(scan) for scan in scans) / len(scans))
