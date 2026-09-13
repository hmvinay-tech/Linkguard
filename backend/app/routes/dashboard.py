from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import UserModel
from app.schemas import DashboardSummary, Issue, Notification, SystemStatus
from app.services.auth import get_current_user, owner_key_for_user
from app.services.resource_store import store

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard(user: UserModel = Depends(get_current_user)) -> DashboardSummary:
    return store.dashboard(owner_key_for_user(user))


@router.get("/issues", response_model=list[Issue])
def list_issues(user: UserModel = Depends(get_current_user)) -> list[Issue]:
    return store.list_open_issues(owner_key_for_user(user))


@router.get("/dashboard/history", response_model=list[dict])
def dashboard_history(user: UserModel = Depends(get_current_user)) -> list[dict]:
    return store.dashboard_history(owner_key_for_user(user))


@router.get("/dashboard/system-status", response_model=SystemStatus)
def system_status(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SystemStatus:
    del user
    database_connected = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_connected = False

    return SystemStatus(
        backend_live=True,
        database_connected=database_connected,
        scheduled_scans_enabled=settings.scheduled_scans_enabled,
        scheduled_scan_minutes=settings.scheduled_scan_minutes,
        scheduled_scan_token_configured=bool(settings.scheduled_scan_job_token),
        email_configured=bool(settings.smtp_host and settings.alert_from_email),
        sms_configured=bool(
            (settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from_phone)
            or settings.sms_webhook_url
        ),
    )


@router.get("/notifications", response_model=list[Notification])
def list_notifications(user: UserModel = Depends(get_current_user)) -> list[Notification]:
    return store.list_notifications(owner_key_for_user(user))


@router.post("/notifications/read", response_model=list[Notification])
def mark_notifications_read(user: UserModel = Depends(get_current_user)) -> list[Notification]:
    owner_key = owner_key_for_user(user)
    store.mark_notifications_read(owner_key)
    return store.list_notifications(owner_key)
