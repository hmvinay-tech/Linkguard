# LinkGuard Development Roadmap

## Phase 1: MVP Foundation

- FastAPI backend
- URL resource management
- HTTP crawler with timeout, redirect, DNS, SSL, and status classification
- Issue generation
- Health score calculation
- Dashboard API
- React dashboard shell

## Phase 2: Scheduled Monitoring

- Add user-configurable scan frequency
- Introduce APScheduler
- Compare current scan with previous scan
- Open and resolve issues based on state changes
- Current status: environment-gated scheduler scaffold is implemented with `SCHEDULED_SCANS_ENABLED`.

## Phase 3: GitHub Integration

- GitHub OAuth
- Repository import
- README URL extraction
- Demo and documentation link scanning
- Repository activity freshness checks
- Current status: README markdown import is implemented for pasted README content.

## Phase 4: Website Crawling

- Same-domain crawler
- Maximum depth and page limits
- robots.txt awareness
- Broken internal links and images

## Phase 5: Content Freshness

- Text extraction
- Content hashing
- Project metadata comparison
- Potential inconsistency detection
- Potentially stale content detection

## Phase 6: Notifications

- Critical issue emails
- Warning digest
- Weekly summary
- Health score change alerts
- Current status: SMTP alert hook is implemented for warning and critical issues.

## Phase 7: AI Assistant

- Analyze structured content differences
- Suggest README and portfolio updates
- Summarize top presence risks

## Phase 8: Production

- PostgreSQL
- Alembic migrations
- Redis and Celery worker
- Vercel frontend
- Render or Railway backend
- Logs, backups, and failed-job monitoring
- Current status: Postgres-ready config, Dockerfiles, Compose, env examples, and Alembic baseline are implemented.
