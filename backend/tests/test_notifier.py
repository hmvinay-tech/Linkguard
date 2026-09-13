import unittest
from unittest.mock import Mock, patch

import httpx

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
    def test_retries_twilio_trial_template_error_with_allowed_template(self, post: Mock) -> None:
        request = httpx.Request("POST", "https://api.twilio.com/messages")
        rejected = httpx.Response(400, request=request, json={"code": 572006})
        accepted = httpx.Response(201, request=request, json={"sid": "SM123"})
        post.side_effect = [rejected, accepted]

        with patch.object(notifier.settings, "twilio_account_sid", "AC123"), patch.object(
            notifier.settings, "twilio_auth_token", "secret"
        ), patch.object(notifier.settings, "twilio_from_phone", "+15550000000"):
            sent = notifier.send_issue_sms("Portfolio", "https://example.com", "critical", "Down", "+15551112222")

        self.assertTrue(sent)
        self.assertEqual(post.call_count, 2)
        self.assertEqual(
            post.call_args_list[0].kwargs["data"]["Body"],
            "LinkGuard critical: Portfolio needs attention. https://example.com - Down",
        )
        self.assertEqual(post.call_args_list[1].kwargs["data"]["Body"], "sms_account_alerts")

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
