# LinkGuard

LinkGuard is a Personal Web Presence Monitor for resumes, portfolios, GitHub profiles, project demos, certificates, and other professional links.

It checks whether important professional URLs are healthy, redirected, unreachable, or broken, then turns the result into a simple Professional Presence Health Score.

## Live Demo

- App: https://linkguard-two.vercel.app/
- API: https://linkguard-api-ocnq.onrender.com

Note: the current demo uses free hosting, so the backend may take extra time to wake up after inactivity.

## Features

- Add, edit, delete, and categorize professional URLs
- Scan one URL or all active URLs
- Detect healthy pages, 404s, server errors, timeouts, excessive redirects, request failures, and restricted pages
- Store users, resources, scan history, issues, and notifications
- Automatically create open issues for warning and critical scan results
- Automatically resolve issues when a later scan becomes healthy
- Run scheduled monitoring while the backend is awake
- Send in-app notifications, with email/SMS alert hooks for configured providers
- Calculate a transparent health score
- Protect the crawler from localhost, private IP, link-local, reserved, and metadata URLs
- React dashboard connected to the FastAPI backend

## Tech Stack

- Frontend: React, Vite, CSS, lucide-react icons
- Backend: FastAPI, Python, HTTPX, SQLAlchemy
- Database: SQLite locally, PostgreSQL in production
- Testing: pytest and unittest

## Project Structure

```text
linkguard/
├── backend/
│   ├── app/
│   │   ├── analyzer/
│   │   ├── crawler/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── index.html
│   └── package.json
├── docs/
│   └── roadmap.md
└── README.md
```

## Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

## Frontend Setup

Install Node.js first, then:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://127.0.0.1:5173
```

## Deployment

Deployment-ready config is included:

- Frontend API URL uses `VITE_API_BASE_URL`
- Backend CORS uses `BACKEND_CORS_ORIGINS`
- Backend database uses `DATABASE_URL`
- Dockerfiles are available for the frontend and backend
- Alembic migrations are available in `backend/alembic`
- Local full-stack Docker setup is available with `docker-compose.yml`
- Signup/login and account-scoped resources are included for public demo use
- Automatic monitoring creates in-app notifications and can send per-user email/SMS alerts

See `DEPLOYMENT.md` and `PRODUCTION_CHECKLIST.md` for environment variables and hosting steps.

## API Endpoints

```text
GET    /api/health
GET    /api/dashboard
GET    /api/issues

GET    /api/resources
POST   /api/resources
GET    /api/resources/{id}
PUT    /api/resources/{id}
DELETE /api/resources/{id}

POST   /api/resources/{id}/scan
POST   /api/resources/scan-all
GET    /api/resources/{id}/scans
```

## Health Scoring

Each latest scan starts from 100.

```text
critical issue       -40
warning issue        -10
timeout              -20
SSL error            -10
3+ redirects         -10
```

The overall score is the average of the latest scan score for every scanned resource.

## Demo Flow

1. Start the backend.
2. Start the frontend.
3. Add a portfolio URL, GitHub URL, certificate URL, and one intentionally broken URL.
4. Click Scan All.
5. Show status code, response time, redirects, and issue severity.
6. Show the Professional Presence Health Score.
7. Explain how the crawler blocks unsafe internal URLs such as `localhost`, `127.0.0.1`, and `169.254.169.254`.

## Why This Project Matters

LinkGuard is more than a broken-link checker. It is designed as a professional web presence monitor that can later grow into scheduled monitoring, GitHub README link scanning, content freshness detection, and AI-assisted profile improvement suggestions.

The current MVP proves the core product loop:

```text
URL input -> crawler -> database -> issue engine -> health score -> dashboard
```

## Next Improvements

- Google OAuth login
- GitHub API integration
- README and portfolio content comparison
- AI assistant for suggested profile updates
- Paid always-on backend hosting for serious public monitoring
