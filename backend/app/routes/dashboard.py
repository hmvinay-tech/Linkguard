from fastapi import APIRouter, Depends

from app.models import UserModel
from app.schemas import DashboardSummary, Issue, Notification
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


@router.get("/notifications", response_model=list[Notification])
def list_notifications(user: UserModel = Depends(get_current_user)) -> list[Notification]:
    return store.list_notifications(owner_key_for_user(user))


@router.post("/notifications/read", response_model=list[Notification])
def mark_notifications_read(user: UserModel = Depends(get_current_user)) -> list[Notification]:
    owner_key = owner_key_for_user(user)
    store.mark_notifications_read(owner_key)
    return store.list_notifications(owner_key)
