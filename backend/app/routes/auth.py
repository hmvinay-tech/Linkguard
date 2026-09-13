import logging
import smtplib

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import UserModel
from app.schemas import TestEmailResponse, TestSmsResponse, TokenResponse, UserCreate, UserLogin, UserPublic, UserSettingsUpdate
from app.services.auth import authenticate_user, create_user, delete_user_account, get_current_user, update_user_settings
from app.services.notifier import send_issue_alert, send_issue_sms

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


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


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    delete_user_account(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/me/test-sms", response_model=TestSmsResponse)
def send_test_sms(user: UserModel = Depends(get_current_user)) -> TestSmsResponse:
    if not user.notifications_enabled or not user.sms_notifications_enabled or not user.notification_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Save a phone number and choose SMS alerts first.",
        )

    try:
        sent = send_issue_sms(
            "Test alert",
            "https://linkguard-two.vercel.app/",
            "info",
            "This is a LinkGuard test SMS. Your SMS alert setup is connected.",
            user.notification_phone,
        )
    except httpx.HTTPStatusError as error:
        response_text = error.response.text[:160] if error.response is not None else ""
        provider_status = error.response.status_code if error.response else "unknown"
        logger.warning("SMS provider rejected test SMS: %s %s", provider_status, response_text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"SMS provider rejected the message. Check Twilio logs. Status {provider_status}.",
        ) from error
    except httpx.HTTPError as error:
        logger.warning("SMS provider request failed for test SMS: %s", error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="SMS provider request failed. Check Twilio credentials and sender number.",
        ) from error

    if not sent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMS provider is not configured on the backend.",
        )

    return TestSmsResponse(status="sent")


@router.post("/me/test-email", response_model=TestEmailResponse)
def send_test_email(user: UserModel = Depends(get_current_user)) -> TestEmailResponse:
    recipient = user.notification_email or user.email
    if not user.notifications_enabled or user.sms_notifications_enabled or not recipient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Save an email address and choose email alerts first.",
        )

    try:
        sent = send_issue_alert(
            "Test alert",
            "https://linkguard-two.vercel.app/",
            "info",
            "This is a LinkGuard test email. Your email alert setup is connected.",
            recipient,
        )
    except (OSError, smtplib.SMTPException) as error:
        logger.warning("Email provider request failed for test email: %s", error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Email provider request failed. Check SMTP credentials and sender email.",
        ) from error

    if not sent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email provider is not configured on the backend.",
        )

    return TestEmailResponse(status="sent")
