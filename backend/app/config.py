from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LinkGuard"
    api_prefix: str = "/api"
    secret_key: str = "change-me-before-deploying"
    access_token_expire_minutes: int = 60 * 24 * 7
    database_url: str = "sqlite:///./linkguard.db"
    backend_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
    backend_cors_origin_regex: str | None = None
    crawler_timeout_seconds: float = 10.0
    crawler_max_redirects: int = 5
    crawler_max_response_bytes: int = 1_000_000
    scheduled_scans_enabled: bool = True
    scheduled_scan_minutes: int = 15
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    alert_from_email: str | None = None
    alert_to_email: str | None = None
    sms_webhook_url: str | None = None
    sms_webhook_token: str | None = None
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_phone: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


settings = Settings()
