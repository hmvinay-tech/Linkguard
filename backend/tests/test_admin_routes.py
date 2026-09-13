import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.routes import admin


class AdminRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_scan_due_resources_requires_configured_token(self) -> None:
        with patch.object(admin.settings, "scheduled_scan_job_token", None):
            with self.assertRaises(HTTPException) as context:
                await admin.scan_due_resources(x_linkguard_job_token="secret")

        self.assertEqual(context.exception.status_code, 503)

    async def test_scan_due_resources_rejects_wrong_token(self) -> None:
        with patch.object(admin.settings, "scheduled_scan_job_token", "secret"):
            with self.assertRaises(HTTPException) as context:
                await admin.scan_due_resources(x_linkguard_job_token="wrong")

        self.assertEqual(context.exception.status_code, 401)

    async def test_scan_due_resources_scans_with_correct_token(self) -> None:
        with patch.object(admin.settings, "scheduled_scan_job_token", "secret"), patch.object(
            admin.store,
            "scan_due_resources",
            new=AsyncMock(return_value=[object(), object()]),
        ):
            response = await admin.scan_due_resources(x_linkguard_job_token="secret")

        self.assertEqual(response, {"status": "ok", "scanned": 2})


if __name__ == "__main__":
    unittest.main()
