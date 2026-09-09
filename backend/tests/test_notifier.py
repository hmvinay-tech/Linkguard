import unittest
from unittest.mock import Mock, patch

from app.services import notifier


class NotifierTests(unittest.TestCase):
    @patch("app.services.notifier.httpx.post")
    def test_sends_twilio_sms_when_credentials_exist(self, post: Mock) -> None:
        with patch.object(notifier.settings, "twilio_account_sid", "AC123"), patch.object(
            notifier.settings, "twilio_auth_token", "secret"
        ), patch.object(notifier.settings, "twilio_from_phone", "+15550000000"):
            sent = notifier.send_issue_sms("Portfolio", "https://example.com", "critical", "Down", "+15551112222")

        self.assertTrue(sent)
        post.assert_called_once()
        _, kwargs = post.call_args
        self.assertEqual(kwargs["data"]["To"], "+15551112222")
        self.assertEqual(kwargs["data"]["From"], "+15550000000")
        self.assertEqual(kwargs["auth"], ("AC123", "secret"))

    @patch("app.services.notifier.httpx.post")
    def test_falls_back_to_sms_webhook(self, post: Mock) -> None:
        with patch.object(notifier.settings, "twilio_account_sid", None), patch.object(
            notifier.settings, "twilio_auth_token", None
        ), patch.object(notifier.settings, "twilio_from_phone", None), patch.object(
            notifier.settings, "sms_webhook_url", "https://sms.example.com/send"
        ), patch.object(notifier.settings, "sms_webhook_token", "token"):
            sent = notifier.send_issue_sms("Portfolio", "https://example.com", "warning", "Slow", "+15551112222")

        self.assertTrue(sent)
        post.assert_called_once()
        post.assert_called_with(
            "https://sms.example.com/send",
            json={
                "to": "+15551112222",
                "message": "LinkGuard warning: Portfolio needs attention. https://example.com - Slow",
            },
            headers={"Authorization": "Bearer token"},
            timeout=10,
        )


if __name__ == "__main__":
    unittest.main()
