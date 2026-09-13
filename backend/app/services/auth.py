from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import IssueModel, NotificationModel, ResourceModel, ScanModel, UserModel
from app.schemas import TokenResponse, UserCreate, UserLogin, UserPublic, UserSettingsUpdate

AUTH_RATE_LIMIT_ATTEMPTS = 8
AUTH_RATE_LIMIT_WINDOW_SECONDS = 15 * 60
_auth_attempts: dict[str, list[float]] = {}


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str, salt: bytes | None = None) -> str:
    password_salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), password_salt, 210_000)
    return f"pbkdf2_sha256${_b64encode(password_salt)}${_b64encode(digest)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, salt, digest = password_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    expected = hash_password(password, _b64decode(salt))
    return hmac.compare_digest(expected, password_hash)


def create_user(db: Session, payload: UserCreate) -> TokenResponse:
    email = normalize_email(payload.email)
    _check_auth_rate_limit(f"signup:{email}")
    existing = db.scalar(select(UserModel).where(UserModel.email == email))
    if existing:
        _record_auth_failure(f"signup:{email}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    user = UserModel(email=email, password_hash=hash_password(payload.password), notification_email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


def authenticate_user(db: Session, payload: UserLogin) -> TokenResponse:
    email = normalize_email(payload.email)
    rate_limit_key = f"login:{email}"
    _check_auth_rate_limit(rate_limit_key)
    user = db.scalar(select(UserModel).where(UserModel.email == email))
    if not user or not verify_password(payload.password, user.password_hash):
        _record_auth_failure(rate_limit_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    _clear_auth_failures(rate_limit_key)
    return _token_response(user)


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> UserModel:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user_id = verify_access_token(authorization.split(" ", 1)[1])
    user = db.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return user


def owner_key_for_user(user: UserModel) -> str:
    return f"user:{user.id}"


def update_user_settings(db: Session, user: UserModel, payload: UserSettingsUpdate) -> UserPublic:
    changes = payload.model_dump(exclude_unset=True)
    if "notification_email" in changes and changes["notification_email"]:
        changes["notification_email"] = normalize_email(changes["notification_email"])
    if "notification_phone" in changes and changes["notification_phone"]:
        changes["notification_phone"] = changes["notification_phone"].strip()
    for key, value in changes.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return _user_public(user)


def delete_user_account(db: Session, user: UserModel) -> None:
    owner_key = owner_key_for_user(user)
    resource_ids = list(db.scalars(select(ResourceModel.id).where(ResourceModel.owner_key == owner_key)).all())

    if resource_ids:
        db.execute(delete(ScanModel).where(ScanModel.resource_id.in_(resource_ids)))
        db.execute(delete(IssueModel).where(IssueModel.resource_id.in_(resource_ids)))
        db.execute(delete(NotificationModel).where(NotificationModel.resource_id.in_(resource_ids)))
        db.execute(delete(ResourceModel).where(ResourceModel.id.in_(resource_ids)))

    db.execute(delete(NotificationModel).where(NotificationModel.owner_key == owner_key))
    db.delete(user)
    db.commit()


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": user_id, "exp": int(expires_at.timestamp())}
    payload_data = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _sign(payload_data)
    return f"{payload_data}.{signature}"


def verify_access_token(token: str) -> int:
    try:
        payload_data, signature = token.split(".", 1)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from None

    if not hmac.compare_digest(_sign(payload_data), signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        payload = json.loads(_b64decode(payload_data))
        expires_at = int(payload["exp"])
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from None

    if expires_at < int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    return user_id


def _token_response(user: UserModel) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        user=_user_public(user),
    )


def _user_public(user: UserModel) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        notification_email=user.notification_email,
        notification_phone=user.notification_phone,
        notifications_enabled=user.notifications_enabled,
        sms_notifications_enabled=user.sms_notifications_enabled,
        scan_frequency_minutes=user.scan_frequency_minutes,
    )


def _sign(payload_data: str) -> str:
    signature = hmac.new(settings.secret_key.encode("utf-8"), payload_data.encode("utf-8"), hashlib.sha256).digest()
    return _b64encode(signature)


def _check_auth_rate_limit(key: str) -> None:
    now = time.monotonic()
    attempts = [attempt for attempt in _auth_attempts.get(key, []) if now - attempt < AUTH_RATE_LIMIT_WINDOW_SECONDS]
    _auth_attempts[key] = attempts
    if len(attempts) >= AUTH_RATE_LIMIT_ATTEMPTS:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Try again later.")


def _record_auth_failure(key: str) -> None:
    _auth_attempts.setdefault(key, []).append(time.monotonic())


def _clear_auth_failures(key: str) -> None:
    _auth_attempts.pop(key, None)


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))
