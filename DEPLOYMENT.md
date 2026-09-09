# LinkGuard Deployment Guide

This project is ready to run as a split frontend/backend deployment or as Docker Compose.

## Required Environment Variables

Backend:

```env
APP_NAME=LinkGuard
API_PREFIX=/api
SECRET_KEY=replace-with-a-long-random-production-secret
ACCESS_TOKEN_EXPIRE_MINUTES=10080
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
BACKEND_CORS_ORIGINS=https://your-frontend-domain.com
BACKEND_CORS_ORIGIN_REGEX=
CRAWLER_TIMEOUT_SECONDS=10
CRAWLER_MAX_REDIRECTS=5
CRAWLER_MAX_RESPONSE_BYTES=1000000
SCHEDULED_SCANS_ENABLED=true
SCHEDULED_SCAN_MINUTES=15
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
ALERT_FROM_EMAIL=
ALERT_TO_EMAIL=
SMS_WEBHOOK_URL=
SMS_WEBHOOK_TOKEN=
```

Frontend:

```env
VITE_API_BASE_URL=https://your-backend-domain.com/api
```

## Local Docker Run

From the project root:

```bash
docker compose up --build
```

URLs:

```text
Frontend: http://localhost:8080
Backend:  http://localhost:8000
Docs:     http://localhost:8000/docs
```

## Backend Deployment

Good hosts for the FastAPI backend:

- Render
- Railway
- Fly.io

Use the `backend/Dockerfile` or a Python service with this start command:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set `DATABASE_URL` to a production PostgreSQL database URL.

The included `render.yaml` uses Render's free web service and free Postgres plans for testing. Free services can sleep after idle time, and free Postgres expires after 30 days, so upgrade those plans before relying on LinkGuard for always-on public monitoring.

For the first Vercel deployment, you can temporarily set:

```env
BACKEND_CORS_ORIGIN_REGEX=https://.*\.vercel\.app
```

After launch, replace it with the exact production frontend URL in `BACKEND_CORS_ORIGINS`.

## Frontend Deployment

Good hosts for the React frontend:

- Vercel
- Netlify
- Cloudflare Pages

Build command:

```bash
npm run build
```

Output directory:

```text
dist
```

Set `VITE_API_BASE_URL` to the deployed backend API URL before building.

## Database Migrations

Run migrations from the `backend` folder:

```bash
alembic upgrade head
```

Create a new migration after changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe change"
```

## Production Features Already Wired

- Signup/login uses signed bearer tokens and PBKDF2 password hashes.
- User-owned resources are scoped by the authenticated account.
- Scheduled scans run automatically when `SCHEDULED_SCANS_ENABLED=true`.
- Every warning or critical issue creates an in-app notification for the user.
- SMTP issue alerts are sent to each user's notification email when SMTP variables are configured.
- SMS alerts are sent to each user's phone number when `SMS_WEBHOOK_URL` is configured.
- Automatic monitoring runs while the backend process is awake; choose a deployment host that does not sleep for true always-on monitoring.

## SMS Webhook Contract

Configure `SMS_WEBHOOK_URL` to point at an SMS provider endpoint or small serverless function. LinkGuard sends:

```json
{
  "to": "+15551234567",
  "message": "LinkGuard critical: Portfolio needs attention. https://example.com - Latest scan classified this resource as critical."
}
```

If `SMS_WEBHOOK_TOKEN` is set, LinkGuard sends it as a bearer token.
- README markdown links can be imported with `POST /api/resources/imports/readme`.
- Demo data can be seeded with `POST /api/resources/demo/seed`.
- Chart data is available at `GET /api/dashboard/history`.

## Final Launch Checklist

See `PRODUCTION_CHECKLIST.md` before making the app public.
