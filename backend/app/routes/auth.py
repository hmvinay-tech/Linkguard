from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import UserModel
from app.schemas import TokenResponse, UserCreate, UserLogin, UserPublic, UserSettingsUpdate
from app.services.auth import authenticate_user, create_user, get_current_user, update_user_settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
def signup(payload: UserCreate, db: Session = Depends(get_db)) -> TokenResponse:
    return create_user(db, payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    return authenticate_user(db, payload)


@router.get("/me", response_model=UserPublic)
def me(user: UserModel = Depends(get_current_user)) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        notification_email=user.notification_email,
        notification_phone=user.notification_phone,
        notifications_enabled=user.notifications_enabled,
        sms_notifications_enabled=user.sms_notifications_enabled,
        scan_frequency_minutes=user.scan_frequency_minutes,
    )


@router.put("/me", response_model=UserPublic)
def update_me(
    payload: UserSettingsUpdate,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPublic:
    return update_user_settings(db, user, payload)
