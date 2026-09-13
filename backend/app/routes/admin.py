import secrets

from fastapi import APIRouter, Header, HTTPException, status

from app.config import settings
from app.services.resource_store import store

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/scan-due")
async def scan_due_resources(x_linkguard_job_token: str | None = Header(default=None)) -> dict[str, int | str]:
    if not settings.scheduled_scan_job_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="External scan job is not configured.",
        )
    if not x_linkguard_job_token or not secrets.compare_digest(
        x_linkguard_job_token,
        settings.scheduled_scan_job_token,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid job token.")

    scans = await store.scan_due_resources()
    return {"status": "ok", "scanned": len(scans)}
