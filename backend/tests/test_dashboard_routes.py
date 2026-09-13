import unittest
from unittest.mock import Mock, patch

from app.models import UserModel
from app.routes import dashboard


class DashboardRouteTests(unittest.TestCase):
    def test_system_status_reports_configuration_without_secrets(self) -> None:
        db = Mock()
        user = UserModel(id=1, email="test@example.com", password_hash="hash")

        with (
            patch.object(dashboard.settings, "scheduled_scans_enabled", True),
            patch.object(dashboard.settings, "scheduled_scan_minutes", 15),
            patch.object(dashboard.settings, "scheduled_scan_job_token", "secret-token"),
            patch.object(dashboard.settings, "smtp_host", "smtp.example.com"),
            patch.object(dashboard.settings, "alert_from_email", "alerts@example.com"),
            patch.object(dashboard.settings, "twilio_account_sid", "AC123"),
            patch.object(dashboard.settings, "twilio_auth_token", "twilio-secret"),
            patch.object(dashboard.settings, "twilio_from_phone", "+15551112222"),
            patch.object(dashboard.settings, "sms_webhook_url", None),
        ):
            response = dashboard.system_status(user=user, db=db)

        self.assertTrue(response.backend_live)
        self.assertTrue(response.database_connected)
        self.assertTrue(response.scheduled_scans_enabled)
        self.assertEqual(response.scheduled_scan_minutes, 15)
        self.assertTrue(response.scheduled_scan_token_configured)
        self.assertTrue(response.email_configured)
        self.assertTrue(response.sms_configured)

    def test_system_status_reports_database_failure(self) -> None:
        db = Mock()
        db.execute.side_effect = RuntimeError("database is down")
        user = UserModel(id=1, email="test@example.com", password_hash="hash")

        response = dashboard.system_status(user=user, db=db)

        self.assertFalse(response.database_connected)


if __name__ == "__main__":
    unittest.main()
