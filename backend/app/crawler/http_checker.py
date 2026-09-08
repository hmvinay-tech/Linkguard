from dataclasses import dataclass
from datetime import datetime, timezone
import time
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.crawler.url_safety import UnsafeUrlError, validate_public_url

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36 LinkGuard/1.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

RESTRICTED_PLATFORM_HOSTS = ("linkedin.com", "www.linkedin.com")


@dataclass(frozen=True)
class HttpCheckResult:
    status_code: int | None
    response_time_ms: int | None
    final_url: str | None
    redirect_count: int
    ssl_valid: bool | None
    error_type: str | None
    classification: str
    scanned_at: datetime


async def check_url(url: str) -> HttpCheckResult:
    scanned_at = datetime.now(timezone.utc)

    try:
        validate_public_url(url)
    except UnsafeUrlError as exc:
        return _error_result("unsafe_url", str(exc), scanned_at)

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            max_redirects=settings.crawler_max_redirects,
            timeout=settings.crawler_timeout_seconds,
            headers=DEFAULT_HEADERS,
        ) as client:
            response = await client.get(url)
    except httpx.TooManyRedirects:
        elapsed = _elapsed_ms(started)
        return HttpCheckResult(None, elapsed, None, settings.crawler_max_redirects + 1, None, "too_many_redirects", "warning", scanned_at)
    except httpx.TimeoutException:
        return _error_result("timeout", "Request timed out.", scanned_at, started)
    except httpx.ConnectError as exc:
        message = str(exc).lower()
        error_type = "ssl_error" if "ssl" in message or "certificate" in message else "connection_error"
        return _error_result(error_type, str(exc), scanned_at, started)
    except httpx.RequestError as exc:
        return _error_result("request_error", str(exc), scanned_at, started)

    redirect_count = len(response.history)
    classification = classify_response(response.status_code, redirect_count, str(response.url))
    error_type = restricted_platform_message(response.status_code, str(response.url))
    ssl_valid = response.url.scheme == "https"
    return HttpCheckResult(
        status_code=response.status_code,
        response_time_ms=_elapsed_ms(started),
        final_url=str(response.url),
        redirect_count=redirect_count,
        ssl_valid=ssl_valid,
        error_type=error_type,
        classification=classification,
        scanned_at=scanned_at,
    )


def classify_response(status_code: int | None, redirect_count: int = 0, url: str | None = None) -> str:
    if status_code is None:
        return "critical"
    if is_restricted_platform(url) and status_code in {401, 403, 429, 999}:
        return "warning"
    if status_code == 403:
        return "warning"
    if status_code >= 500:
        return "critical"
    if status_code == 404:
        return "critical"
    if 400 <= status_code < 500:
        return "warning"
    if redirect_count >= 3:
        return "warning"
    return "healthy"


def restricted_platform_message(status_code: int, url: str) -> str | None:
    if is_restricted_platform(url) and status_code in {401, 403, 429, 999}:
        return "restricted_platform: LinkedIn often blocks automated checks, but the profile URL may still work in a browser."
    return None


def is_restricted_platform(url: str | None) -> bool:
    if not url:
        return False
    host = urlparse(url).hostname or ""
    return host.lower() in RESTRICTED_PLATFORM_HOSTS


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


def _error_result(error_type: str, message: str, scanned_at: datetime, started: float | None = None) -> HttpCheckResult:
    return HttpCheckResult(
        status_code=None,
        response_time_ms=_elapsed_ms(started) if started else None,
        final_url=None,
        redirect_count=0,
        ssl_valid=False if error_type == "ssl_error" else None,
        error_type=f"{error_type}: {message}" if message else error_type,
        classification="critical",
        scanned_at=scanned_at,
    )
