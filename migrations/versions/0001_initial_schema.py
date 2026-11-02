"""Create initial account, monitor, and check result tables.

Revision ID: 0001_initial
Revises:
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

monitor_state = postgresql.ENUM(
    "unknown", "up", "degraded", "down", name="monitor_state", create_type=False
)
check_outcome = postgresql.ENUM(
    "success",
    "http_error",
    "timeout",
    "dns_error",
    "tls_error",
    "connection_error",
    "internal_error",
    name="check_outcome",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    monitor_state.create(bind, checkfirst=True)
    check_outcome.create(bind, checkfirst=True)

    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), server_default="user", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('user', 'admin')", name="ck_account_role"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "monitors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("method", sa.String(length=10), server_default="GET", nullable=False),
        sa.Column("interval_seconds", sa.Integer(), server_default="300", nullable=False),
        sa.Column("timeout_ms", sa.Integer(), server_default="5000", nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("consecutive_failures", sa.Integer(), server_default="0", nullable=False),
        sa.Column("consecutive_successes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("current_state", monitor_state, server_default="unknown", nullable=False),
        sa.Column(
            "next_check_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "interval_seconds BETWEEN 60 AND 86400", name="ck_monitor_interval"
        ),
        sa.CheckConstraint("timeout_ms BETWEEN 500 AND 15000", name="ck_monitor_timeout"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_monitors_due",
        "monitors",
        ["next_check_at"],
        unique=False,
        postgresql_where=sa.text("enabled = true"),
    )
    op.create_index(
        "ix_monitors_account_created",
        "monitors",
        ["account_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "check_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("monitor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("outcome", check_outcome, nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["monitor_id"], ["monitors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_check_results_monitor_time",
        "check_results",
        ["monitor_id", "checked_at"],
        unique=False,
    )
    op.create_index(
        "ix_check_results_time", "check_results", ["checked_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_check_results_time", table_name="check_results")
    op.drop_index("ix_check_results_monitor_time", table_name="check_results")
    op.drop_table("check_results")
    op.drop_index("ix_monitors_account_created", table_name="monitors")
    op.drop_index("ix_monitors_due", table_name="monitors")
    op.drop_table("monitors")
    op.drop_table("accounts")
    check_outcome.drop(op.get_bind(), checkfirst=True)
    monitor_state.drop(op.get_bind(), checkfirst=True)
