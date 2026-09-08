import asyncio

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.services.resource_store import store

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if not settings.scheduled_scans_enabled or _scheduler:
        return

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        lambda: asyncio.run(store.scan_due_resources()),
        "interval",
        minutes=settings.scheduled_scan_minutes,
        id="scan-all-resources",
        replace_existing=True,
    )
    _scheduler.start()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
