from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


def sqlalchemy_database_url() -> str:
    if settings.database_url.startswith("postgresql://"):
        return settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return settings.database_url


database_url = sqlalchemy_database_url()
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from app import models

    Base.metadata.create_all(bind=engine)
    _apply_sqlite_compatibility_upgrades()


def _apply_sqlite_compatibility_upgrades() -> None:
    if not database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "users" not in table_names:
        Base.metadata.tables["users"].create(bind=engine, checkfirst=True)
    else:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        with engine.begin() as connection:
            if "notification_email" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN notification_email VARCHAR(255)"))
                connection.execute(text("UPDATE users SET notification_email = email WHERE notification_email IS NULL"))
            if "notification_phone" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN notification_phone VARCHAR(40)"))
            if "notifications_enabled" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN notifications_enabled BOOLEAN NOT NULL DEFAULT 1"))
            if "sms_notifications_enabled" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN sms_notifications_enabled BOOLEAN NOT NULL DEFAULT 0"))
            if "scan_frequency_minutes" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN scan_frequency_minutes INTEGER NOT NULL DEFAULT 60"))

    if "notifications" not in table_names:
        Base.metadata.tables["notifications"].create(bind=engine, checkfirst=True)
    else:
        notification_columns = {column["name"] for column in inspector.get_columns("notifications")}
        if "sms_sent" not in notification_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE notifications ADD COLUMN sms_sent BOOLEAN NOT NULL DEFAULT 0"))

    if "resources" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("resources")}
    if "owner_key" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE resources ADD COLUMN owner_key VARCHAR(120) NOT NULL DEFAULT 'demo'"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_resources_owner_key ON resources (owner_key)"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
