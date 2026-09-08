# LinkGuard Production Checklist

## Required Before Public Launch

- Set a strong `SECRET_KEY` in the backend environment.
- Use PostgreSQL through `DATABASE_URL`; do not use SQLite for production.
- Set `BACKEND_CORS_ORIGINS` to the exact deployed frontend URL.
- Set `VITE_API_BASE_URL` to the deployed backend URL ending in `/api`.
- Run `alembic upgrade head` during backend release.
- Confirm signup, login, logout, add link, scan link, README import, and demo seed in the deployed app.

## Optional Production Features

- Set SMTP variables to enable per-user issue-alert emails.
- Set `SMS_WEBHOOK_URL` to enable per-user SMS alerts.
- Confirm broken-link alerts appear in the dashboard Notifications section.
- Keep `SCHEDULED_SCANS_ENABLED=true` for automatic monitoring.
- Start with `SCHEDULED_SCAN_MINUTES=60` for hourly scans, or `1440` for daily scans.
- Use a backend host/plan that does not sleep if you want monitoring to run all the time.
- Add uptime/log monitoring on the backend host.
- Add database backups on the Postgres provider.

## Security Notes

- The current auth uses signed bearer tokens and PBKDF2 password hashes without extra dependencies.
- Store tokens only over HTTPS in production.
- Rotate `SECRET_KEY` if it is ever committed or exposed.
- For a larger SaaS launch, replace local auth with a managed identity provider such as Auth0, Clerk, or Supabase Auth.
