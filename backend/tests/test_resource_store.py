import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.crawler.http_checker import HttpCheckResult
from app.database import Base
from app.schemas import ResourceCategory, ResourceCreate, ResourceUpdate
from app.services.resource_store import ResourceStore


class ResourceStoreTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        self.store = ResourceStore(sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False))

    async def test_resource_lifecycle_scan_and_dashboard(self) -> None:
        resource = self.store.create_resource(
            ResourceCreate(name="Portfolio", url="https://example.com", category=ResourceCategory.portfolio)
        )

        updated = self.store.update_resource(resource.id, ResourceUpdate(name="Main Portfolio"))

        self.assertIsNotNone(updated)
        self.assertEqual(updated.name, "Main Portfolio")

        fake_result = HttpCheckResult(
            status_code=404,
            response_time_ms=120,
            final_url="https://example.com/missing",
            redirect_count=0,
            ssl_valid=True,
            error_type=None,
            classification="critical",
            scanned_at=datetime.now(timezone.utc),
        )

        with patch("app.services.resource_store.check_url", AsyncMock(return_value=fake_result)):
            scan = await self.store.scan_resource(resource.id)

        dashboard = self.store.dashboard()

        self.assertEqual(scan.classification, "critical")
        self.assertEqual(dashboard.total_resources, 1)
        self.assertEqual(dashboard.critical, 1)
        self.assertEqual(len(dashboard.open_issues), 1)
        self.assertEqual(len(dashboard.recent_notifications), 1)
        self.assertIn("Main Portfolio", dashboard.recent_notifications[0].title)
        self.assertFalse(dashboard.recent_notifications[0].email_sent)
        self.assertFalse(dashboard.recent_notifications[0].sms_sent)

    async def test_marks_notifications_read(self) -> None:
        resource = self.store.create_resource(
            ResourceCreate(name="Broken", url="https://example.com/missing", category=ResourceCategory.project)
        )
        fake_result = HttpCheckResult(
            status_code=404,
            response_time_ms=80,
            final_url="https://example.com/missing",
            redirect_count=0,
            ssl_valid=True,
            error_type=None,
            classification="critical",
            scanned_at=datetime.now(timezone.utc),
        )

        with patch("app.services.resource_store.check_url", AsyncMock(return_value=fake_result)):
            await self.store.scan_resource(resource.id)

        self.store.mark_notifications_read()
        notifications = self.store.list_notifications()

        self.assertEqual(len(notifications), 1)
        self.assertTrue(notifications[0].read)


if __name__ == "__main__":
    unittest.main()
