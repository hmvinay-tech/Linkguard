from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routes import auth, dashboard, resources
from app.scheduler import start_scheduler, stop_scheduler

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resources.router, prefix=settings.api_prefix)
app.include_router(dashboard.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)


@app.on_event("startup")
def startup() -> None:
    init_db()
    start_scheduler()


@app.on_event("shutdown")
def shutdown() -> None:
    stop_scheduler()


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
