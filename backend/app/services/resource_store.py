from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.analyzer.scoring import overall_health_score
from app.crawler.http_checker import check_url
from app.database import SessionLocal
from app.models import IssueModel, NotificationModel, ResourceModel, ScanModel, UserModel
from app.schemas import (
    DemoSeedResult,
    DashboardSummary,
    Issue,
    IssueSeverity,
    LinkPreview,
    Notification,
    ReadmeImportResult,
    Resource,
    ResourceCategory,
    ResourceCreate,
    ResourceUpdate,
    ScanResult,
)
from app.services.notifier import send_issue_alert, send_issue_sms


DEMO_RESOURCES = [
    ResourceCreate(name="Portfolio", url="https://example.com", category=ResourceCategory.portfolio),
    ResourceCreate(name="GitHub Profile", url="https://github.com", category=ResourceCategory.github),
    ResourceCreate(name="Certificate", url="https://www.credly.com", category=ResourceCategory.certificate),
    ResourceCreate(name="Broken Demo Link", url="https://example.com/missing-page", category=ResourceCategory.project),
]


class ResourceStore:
    def __init__(self, session_factory: sessionmaker[Session] = SessionLocal) -> None:
        self._session_factory = session_factory

    def list_resources(self, owner_key: str = "demo") -> list[Resource]:
        with self._session_factory() as db:
            resources = db.scalars(
                select(ResourceModel)
                .where(ResourceModel.owner_key == owner_key)
                .order_by(ResourceModel.created_at.desc())
            ).all()
            return [Resource.model_validate(resource) for resource in resources]

    def create_resource(self, payload: ResourceCreate, owner_key: str = "demo") -> Resource:
        with self._session_factory() as db:
            resource = ResourceModel(
                owner_key=owner_key,
                name=payload.name,
                url=str(payload.url),
                category=payload.category.value,
                description=payload.description,
            )
            db.add(resource)
            db.commit()
            db.refresh(resource)
            return Resource.model_validate(resource)

    def update_resource(self, resource_id: int, payload: ResourceUpdate, owner_key: str = "demo") -> Resource | None:
        with self._session_factory() as db:
            resource = self._get_resource_model(db, resource_id, owner_key)
            if not resource:
                return None

            changes = payload.model_dump(exclude_unset=True)
            if "url" in changes and changes["url"] is not None:
                changes["url"] = str(changes["url"])
            if "category" in changes and changes["category"] is not None:
                changes["category"] = changes["category"].value

            for key, value in changes.items():
                setattr(resource, key, value)

            resource.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(resource)
            return Resource.model_validate(resource)

    def get_resource(self, resource_id: int, owner_key: str = "demo") -> Resource | None:
        with self._session_factory() as db:
            resource = self._get_resource_model(db, resource_id, owner_key)
            return Resource.model_validate(resource) if resource else None

    def delete_resource(self, resource_id: int, owner_key: str = "demo") -> bool:
        with self._session_factory() as db:
            resource = self._get_resource_model(db, resource_id, owner_key)
            if not resource:
                return False
            db.delete(resource)
            db.commit()
            return True

    async def scan_resource(self, resource_id: int, owner_key: str = "demo") -> ScanResult | None:
        with self._session_factory() as db:
            resource = self._get_resource_model(db, resource_id, owner_key)
            if not resource:
                return None

            result = await check_url(resource.url)
            scan = ScanModel(resource_id=resource_id, **result.__dict__)
            db.add(scan)
            db.commit()
            db.refresh(scan)

            scan_schema = ScanResult.model_validate(scan)
            self._sync_issue(db, resource, scan_schema)
            db.commit()
            return scan_schema

    async def scan_all_resources(self, owner_key: str = "demo") -> list[ScanResult]:
        scans: list[ScanResult] = []
        for resource in self.list_resources(owner_key):
            if not resource.active:
                continue
            scan = await self.scan_resource(resource.id, owner_key)
            if scan:
                scans.append(scan)
        return scans

    def list_scans(self, resource_id: int, owner_key: str = "demo") -> list[ScanResult]:
        with self._session_factory() as db:
            if not self._get_resource_model(db, resource_id, owner_key):
                return []
            scans = db.scalars(
                select(ScanModel).where(ScanModel.resource_id == resource_id).order_by(ScanModel.scanned_at.desc())
            ).all()
            return [ScanResult.model_validate(scan) for scan in scans]

    async def scan_all_workspaces(self) -> list[ScanResult]:
        scans: list[ScanResult] = []
        for owner_key in self.list_owner_keys():
            scans.extend(await self.scan_all_resources(owner_key))
        return scans

    async def scan_due_resources(self) -> list[ScanResult]:
        due_resources = self.list_due_resources()
        scans: list[ScanResult] = []
        for resource_id, owner_key in due_resources:
            scan = await self.scan_resource(resource_id, owner_key)
            if scan:
                scans.append(scan)
        return scans

    def list_due_resources(self) -> list[tuple[int, str]]:
        now = datetime.now(timezone.utc)
        due: list[tuple[int, str]] = []
        with self._session_factory() as db:
            resources = db.scalars(select(ResourceModel).where(ResourceModel.active.is_(True))).all()
            for resource in resources:
                latest_scan = db.scalar(
                    select(ScanModel)
                    .where(ScanModel.resource_id == resource.id)
                    .order_by(desc(ScanModel.scanned_at), desc(ScanModel.id))
                    .limit(1)
                )
                frequency_minutes = self._scan_frequency_for_resource(db, resource)
                if not latest_scan or (now - latest_scan.scanned_at).total_seconds() >= frequency_minutes * 60:
                    due.append((resource.id, resource.owner_key))
        return due

    def list_owner_keys(self) -> list[str]:
        with self._session_factory() as db:
            return list(db.scalars(select(ResourceModel.owner_key).distinct()).all())

    def list_open_issues(self, owner_key: str = "demo") -> list[Issue]:
        with self._session_factory() as db:
            issues = db.scalars(
                select(IssueModel)
                .join(ResourceModel)
                .where(IssueModel.status == "open", ResourceModel.owner_key == owner_key)
                .order_by(IssueModel.detected_at.desc())
            ).all()
            return [Issue.model_validate(issue) for issue in issues]

    def dashboard(self, owner_key: str = "demo") -> DashboardSummary:
        with self._session_factory() as db:
            resources_count = db.scalar(
                select(func.count()).select_from(ResourceModel).where(ResourceModel.owner_key == owner_key)
            ) or 0
            scans = [ScanResult.model_validate(scan) for scan in self._latest_scans(db, owner_key)]
            issues = [
                Issue.model_validate(issue)
                for issue in db.scalars(
                    select(IssueModel)
                    .join(ResourceModel)
                    .where(IssueModel.status == "open", ResourceModel.owner_key == owner_key)
                    .order_by(IssueModel.detected_at.desc())
                ).all()
            ]
            return DashboardSummary(
                health_score=overall_health_score(scans),
                total_resources=resources_count,
                healthy=sum(1 for scan in scans if scan.classification == "healthy"),
                warnings=sum(1 for scan in scans if scan.classification == "warning"),
                critical=sum(1 for scan in scans if scan.classification == "critical"),
                latest_scans=scans,
                open_issues=issues,
                recent_notifications=self._list_notifications(db, owner_key),
            )

    def list_notifications(self, owner_key: str = "demo") -> list[Notification]:
        with self._session_factory() as db:
            return self._list_notifications(db, owner_key)

    def mark_notifications_read(self, owner_key: str = "demo") -> None:
        with self._session_factory() as db:
            notifications = db.scalars(
                select(NotificationModel).where(NotificationModel.owner_key == owner_key, NotificationModel.read.is_(False))
            ).all()
            for notification in notifications:
                notification.read = True
            db.commit()

    def dashboard_history(self, owner_key: str = "demo") -> list[dict]:
        with self._session_factory() as db:
            scans = db.scalars(
                select(ScanModel)
                .join(ResourceModel)
                .where(ResourceModel.owner_key == owner_key)
                .order_by(ScanModel.scanned_at.asc(), ScanModel.id.asc())
            ).all()
            history = []
            for scan in scans[-50:]:
                item = ScanResult.model_validate(scan)
                history.append(
                    {
                        "id": item.id,
                        "resource_id": item.resource_id,
                        "scanned_at": item.scanned_at,
                        "classification": item.classification,
                        "response_time_ms": item.response_time_ms,
                    }
                )
            return history

    def seed_demo_resources(self, owner_key: str = "demo") -> DemoSeedResult:
        result = self.import_links(
            [LinkPreview(name=item.name, url=item.url, category=item.category) for item in DEMO_RESOURCES],
            owner_key,
        )
        return DemoSeedResult(created=result.imported, skipped_existing=result.skipped_existing)

    def import_links(self, links: list[LinkPreview], owner_key: str = "demo") -> ReadmeImportResult:
        created: list[Resource] = []
        skipped: list[str] = []
        with self._session_factory() as db:
            existing_urls = set(
                db.scalars(select(ResourceModel.url).where(ResourceModel.owner_key == owner_key)).all()
            )
            for link in links:
                normalized_url = str(link.url)
                if normalized_url in existing_urls:
                    skipped.append(normalized_url)
                    continue
                resource = ResourceModel(
                    owner_key=owner_key,
                    name=link.name,
                    url=normalized_url,
                    category=link.category.value,
                    description="Imported from README links.",
                )
                db.add(resource)
                db.flush()
                db.refresh(resource)
                existing_urls.add(normalized_url)
                created.append(Resource.model_validate(resource))
            db.commit()
        return ReadmeImportResult(imported=created, skipped_existing=skipped)

    def _latest_scans(self, db: Session, owner_key: str = "demo") -> list[ScanModel]:
        scans = db.scalars(
            select(ScanModel)
            .join(ResourceModel)
            .where(ResourceModel.owner_key == owner_key)
            .order_by(desc(ScanModel.scanned_at), desc(ScanModel.id))
        ).all()
        latest_by_resource: dict[int, ScanModel] = {}
        for scan in scans:
            latest_by_resource.setdefault(scan.resource_id, scan)
        return list(latest_by_resource.values())

    def _sync_issue(self, db: Session, resource: ResourceModel, scan: ScanResult) -> None:
        existing = db.scalar(
            select(IssueModel).where(IssueModel.resource_id == scan.resource_id, IssueModel.status == "open")
        )

        if scan.classification == "healthy":
            if existing:
                existing.status = "resolved"
                existing.resolved_at = datetime.now(timezone.utc)
            return

        severity = IssueSeverity.critical.value if scan.classification == "critical" else IssueSeverity.warning.value
        message = scan.error_type or f"Latest scan classified this resource as {scan.classification}."

        if existing:
            changed = existing.severity != severity or existing.message != message or existing.issue_type != scan.classification
            existing.severity = severity
            existing.message = message
            existing.issue_type = scan.classification
            if changed:
                self._send_issue_alert(db, resource, severity, message)
            return

        db.add(
            IssueModel(
                resource_id=scan.resource_id,
                issue_type=scan.classification,
                severity=severity,
                message=message,
                detected_at=datetime.now(timezone.utc),
            )
        )
        self._send_issue_alert(db, resource, severity, message)

    def _get_resource_model(self, db: Session, resource_id: int, owner_key: str) -> ResourceModel | None:
        return db.scalar(
            select(ResourceModel).where(ResourceModel.id == resource_id, ResourceModel.owner_key == owner_key)
        )

    def _send_issue_alert(self, db: Session, resource: ResourceModel, severity: str, message: str) -> None:
        title = f"{resource.name} needs attention"
        notification_message = f"{resource.url} is now {severity}: {message}"
        email_sent = False
        sms_sent = False
        try:
            recipient = self._notification_email_for_resource(db, resource)
            email_sent = send_issue_alert(resource.name, resource.url, severity, message, recipient)
        except Exception:
            pass
        try:
            recipient_phone = self._notification_phone_for_resource(db, resource)
            sms_sent = send_issue_sms(resource.name, resource.url, severity, message, recipient_phone)
        except Exception:
            pass
        db.add(
            NotificationModel(
                owner_key=resource.owner_key,
                resource_id=resource.id,
                severity=severity,
                title=title,
                message=notification_message,
                email_sent=email_sent,
                sms_sent=sms_sent,
            )
        )

    def _notification_email_for_resource(self, db: Session, resource: ResourceModel) -> str | None:
        if not resource.owner_key.startswith("user:"):
            return None
        try:
            user_id = int(resource.owner_key.split(":", 1)[1])
        except ValueError:
            return None
        user = db.get(UserModel, user_id)
        if not user or not user.notifications_enabled:
            return None
        return user.notification_email or user.email

    def _notification_phone_for_resource(self, db: Session, resource: ResourceModel) -> str | None:
        if not resource.owner_key.startswith("user:"):
            return None
        try:
            user_id = int(resource.owner_key.split(":", 1)[1])
        except ValueError:
            return None
        user = db.get(UserModel, user_id)
        if not user or not user.notifications_enabled or not user.sms_notifications_enabled:
            return None
        return user.notification_phone

    def _scan_frequency_for_resource(self, db: Session, resource: ResourceModel) -> int:
        if not resource.owner_key.startswith("user:"):
            return 60
        try:
            user_id = int(resource.owner_key.split(":", 1)[1])
        except ValueError:
            return 60
        user = db.get(UserModel, user_id)
        return user.scan_frequency_minutes if user else 60

    def _list_notifications(self, db: Session, owner_key: str) -> list[Notification]:
        notifications = db.scalars(
            select(NotificationModel)
            .where(NotificationModel.owner_key == owner_key)
            .order_by(desc(NotificationModel.created_at), desc(NotificationModel.id))
            .limit(20)
        ).all()
        return [Notification.model_validate(notification) for notification in notifications]


store = ResourceStore()
