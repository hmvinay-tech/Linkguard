"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-06
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("notification_email", sa.String(length=255), nullable=True),
        sa.Column("notification_phone", sa.String(length=40), nullable=True),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False),
        sa.Column("sms_notifications_enabled", sa.Boolean(), nullable=False),
        sa.Column("scan_frequency_minutes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "resources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_resources_id"), "resources", ["id"], unique=False)
    op.create_index(op.f("ix_resources_owner_key"), "resources", ["owner_key"], unique=False)

    op.create_table(
        "issues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("issue_type", sa.String(length=60), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_issues_id"), "issues", ["id"], unique=False)
    op.create_index(op.f("ix_issues_resource_id"), "issues", ["resource_id"], unique=False)

    op.create_table(
        "scans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("final_url", sa.Text(), nullable=True),
        sa.Column("redirect_count", sa.Integer(), nullable=False),
        sa.Column("ssl_valid", sa.Boolean(), nullable=True),
        sa.Column("error_type", sa.Text(), nullable=True),
        sa.Column("classification", sa.String(length=40), nullable=False),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scans_id"), "scans", ["id"], unique=False)
    op.create_index(op.f("ix_scans_resource_id"), "scans", ["resource_id"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_key", sa.String(length=120), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("email_sent", sa.Boolean(), nullable=False),
        sa.Column("sms_sent", sa.Boolean(), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)
    op.create_index(op.f("ix_notifications_owner_key"), "notifications", ["owner_key"], unique=False)
    op.create_index(op.f("ix_notifications_resource_id"), "notifications", ["resource_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notifications_resource_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_owner_key"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_id"), table_name="notifications")
    op.drop_table("notifications")
    op.drop_index(op.f("ix_scans_resource_id"), table_name="scans")
    op.drop_index(op.f("ix_scans_id"), table_name="scans")
    op.drop_table("scans")
    op.drop_index(op.f("ix_issues_resource_id"), table_name="issues")
    op.drop_index(op.f("ix_issues_id"), table_name="issues")
    op.drop_table("issues")
    op.drop_index(op.f("ix_resources_owner_key"), table_name="resources")
    op.drop_index(op.f("ix_resources_id"), table_name="resources")
    op.drop_table("resources")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
