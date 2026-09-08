from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ResourceCategory(str, Enum):
    resume = "resume"
    portfolio = "portfolio"
    github = "github"
    project = "project"
    certificate = "certificate"
    social = "social"
    other = "other"


class IssueSeverity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class ResourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: HttpUrl
    category: ResourceCategory = ResourceCategory.other
    description: str | None = Field(default=None, max_length=500)


class ResourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    url: HttpUrl | None = None
    category: ResourceCategory | None = None
    description: str | None = Field(default=None, max_length=500)
    active: bool | None = None


class Resource(ResourceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_key: str = "demo"
    active: bool = True
    created_at: datetime
    updated_at: datetime


class ScanResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resource_id: int
    status_code: int | None = None
    response_time_ms: int | None = None
    final_url: str | None = None
    redirect_count: int = 0
    ssl_valid: bool | None = None
    error_type: str | None = None
    classification: str
    scanned_at: datetime


class Issue(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resource_id: int
    issue_type: str
    severity: IssueSeverity
    message: str
    status: str = "open"
    detected_at: datetime
    resolved_at: datetime | None = None


class Notification(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_key: str
    resource_id: int | None = None
    severity: IssueSeverity
    title: str
    message: str
    email_sent: bool = False
    sms_sent: bool = False
    read: bool = False
    created_at: datetime


class DashboardSummary(BaseModel):
    health_score: int
    total_resources: int
    healthy: int
    warnings: int
    critical: int
    latest_scans: list[ScanResult]
    open_issues: list[Issue]
    recent_notifications: list[Notification] = []


class ReadmeImportRequest(BaseModel):
    markdown: str = Field(min_length=1, max_length=100_000)


class LinkPreview(BaseModel):
    name: str
    url: HttpUrl
    category: ResourceCategory = ResourceCategory.project


class ReadmeImportResult(BaseModel):
    imported: list[Resource]
    skipped_existing: list[str]


class DemoSeedResult(BaseModel):
    created: list[Resource]
    skipped_existing: list[str]


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class UserPublic(BaseModel):
    id: int
    email: str
    notification_email: str | None = None
    notification_phone: str | None = None
    notifications_enabled: bool = True
    sms_notifications_enabled: bool = False
    scan_frequency_minutes: int = 60


class UserSettingsUpdate(BaseModel):
    notification_email: str | None = Field(default=None, max_length=255)
    notification_phone: str | None = Field(default=None, max_length=40)
    notifications_enabled: bool | None = None
    sms_notifications_enabled: bool | None = None
    scan_frequency_minutes: int | None = Field(default=None, ge=15, le=10080)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
