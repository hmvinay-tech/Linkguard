from email.message import EmailMessage
import smtplib

import httpx

from app.config import settings


def send_issue_alert(resource_name: str, resource_url: str, severity: str, message: str, recipient_email: str | None = None) -> bool:
    recipient = recipient_email or settings.alert_to_email
    if not all([settings.smtp_host, settings.alert_from_email, recipient]):
        return False

    email = EmailMessage()
    email["From"] = settings.alert_from_email
    email["To"] = recipient
    email["Subject"] = f"LinkGuard {severity} alert: {resource_name}"
    email.set_content(
        "\n".join(
            [
                f"Resource: {resource_name}",
                f"URL: {resource_url}",
                f"Severity: {severity}",
                "",
                message,
            ]
        )
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(email)

    return True


def send_issue_sms(resource_name: str, resource_url: str, severity: str, message: str, recipient_phone: str | None) -> bool:
    if not recipient_phone:
        return False

    sms_message = f"LinkGuard {severity}: {resource_name} needs attention. {resource_url} - {message}"
    if _send_twilio_sms(recipient_phone, sms_message):
        return True
    return _send_webhook_sms(recipient_phone, sms_message)


def _send_twilio_sms(recipient_phone: str, sms_message: str) -> bool:
    if not all([settings.twilio_account_sid, settings.twilio_auth_token, settings.twilio_from_phone]):
        return False

    response = httpx.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json",
        data={
            "To": recipient_phone,
            "From": settings.twilio_from_phone,
            "Body": sms_message,
        },
        auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        timeout=10,
    )
    response.raise_for_status()
    return True


def _send_webhook_sms(recipient_phone: str, sms_message: str) -> bool:
    if not settings.sms_webhook_url:
        return False

    headers = {}
    if settings.sms_webhook_token:
        headers["Authorization"] = f"Bearer {settings.sms_webhook_token}"

    response = httpx.post(
        settings.sms_webhook_url,
        json={"to": recipient_phone, "message": sms_message},
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()
    return True
