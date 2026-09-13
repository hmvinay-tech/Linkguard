import unittest
from unittest.mock import Mock, patch
import smtplib

import httpx
from fastapi import HTTPException

from app.models import UserModel
from app.routes import auth


def sms_user(phone: str | None = "+15551112222", enabled: bool = True) -> UserModel:
    return UserModel(
        id=1,
        email="test@example.com",
        password_hash="hash",
        notification_phone=phone,
        sms_notifications_enabled=enabled,
    )


def email_user(email: str = "test@example.com", notification_email: str | None = "alerts@example.com", enabled: bool = True) -> UserModel:
    return UserModel(
        id=1,
        email=email,
        password_hash="hash",
        notification_email=notification_email,
        notifications_enabled=enabled,
    )


class AuthRouteTests(unittest.TestCase):
    @patch("app.routes.auth.send_issue_sms", return_value=True)
    def test_send_test_sms_succeeds(self, send_issue_sms: Mock) -> None:
        response = auth.send_test_sms(sms_user())

        self.assertEqual(response.status, "sent")
        send_issue_sms.assert_called_once()

    def test_send_test_sms_requires_enabled_sms_and_phone(self) -> None:
        with self.assertRaises(HTTPException) as context:
            auth.send_test_sms(sms_user(phone=None))

        self.assertEqual(context.exception.status_code, 400)

        with self.assertRaises(HTTPException) as disabled_context:
            auth.send_test_sms(sms_user(enabled=False))

        self.assertEqual(disabled_context.exception.status_code, 400)

    @patch("app.routes.auth.send_issue_sms", return_value=False)
    def test_send_test_sms_reports_missing_provider_config(self, send_issue_sms: Mock) -> None:
        with self.assertRaises(HTTPException) as context:
            auth.send_test_sms(sms_user())

        self.assertEqual(context.exception.status_code, 503)
        send_issue_sms.assert_called_once()

    @patch("app.routes.auth.send_issue_sms")
    def test_send_test_sms_reports_provider_rejection(self, send_issue_sms: Mock) -> None:
        request = httpx.Request("POST", "https://api.twilio.com/messages")
        response = httpx.Response(400, request=request, text="trial number is not verified")
        send_issue_sms.side_effect = httpx.HTTPStatusError("bad request", request=request, response=response)

        with self.assertRaises(HTTPException) as context:
            auth.send_test_sms(sms_user())

        self.assertEqual(context.exception.status_code, 502)
        self.assertIn("Status 400", context.exception.detail)

    @patch("app.routes.auth.send_issue_alert", return_value=True)
    def test_send_test_email_succeeds(self, send_issue_alert: Mock) -> None:
        response = auth.send_test_email(email_user())

        self.assertEqual(response.status, "sent")
        send_issue_alert.assert_called_once()

    def test_send_test_email_requires_enabled_alerts(self) -> None:
        with self.assertRaises(HTTPException) as context:
            auth.send_test_email(email_user(enabled=False))

        self.assertEqual(context.exception.status_code, 400)

    @patch("app.routes.auth.send_issue_alert", return_value=False)
    def test_send_test_email_reports_missing_provider_config(self, send_issue_alert: Mock) -> None:
        with self.assertRaises(HTTPException) as context:
            auth.send_test_email(email_user())

        self.assertEqual(context.exception.status_code, 503)
        send_issue_alert.assert_called_once()

    @patch("app.routes.auth.send_issue_alert")
    def test_send_test_email_reports_provider_failure(self, send_issue_alert: Mock) -> None:
        send_issue_alert.side_effect = smtplib.SMTPException("bad smtp credentials")

        with self.assertRaises(HTTPException) as context:
            auth.send_test_email(email_user())

        self.assertEqual(context.exception.status_code, 502)


if __name__ == "__main__":
    unittest.main()
