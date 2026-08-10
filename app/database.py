from collections.abc import Generator
from contextlib import closing
import sqlite3

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, close_all_sessions, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import BACKUP_DIR, DATABASE_DIALECT, DATABASE_PATH, DATABASE_URL, DATA_DIR


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy database models."""


engine_kwargs: dict = {"pool_pre_ping": True}
if DATABASE_DIALECT == "sqlite":
    engine_kwargs["connect_args"] = {"timeout": 30, "check_same_thread": False}
    # NullPool closes SQLite connections immediately after each request. This
    # prevents lingering Windows file handles and Python ResourceWarning noise
    # while preserving PostgreSQL pooling in production.
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs.update({"pool_size": 5, "max_overflow": 10, "pool_recycle": 1800})

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


if DATABASE_DIALECT == "sqlite":
    @event.listens_for(engine, "connect")
    def configure_sqlite_connection(dbapi_connection, connection_record) -> None:
        del connection_record
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA busy_timeout = 30000")
        finally:
            cursor.close()


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    if column_name not in _table_columns(connection, table_name):
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _run_sqlite_schema_migrations() -> None:
    if DATABASE_DIALECT != "sqlite":
        return
    with closing(sqlite3.connect(DATABASE_PATH, timeout=30)) as connection:
        migrations = {
            "hr_admin_accounts": {
                "role": "TEXT NOT NULL DEFAULT 'ADMIN'",
                "must_change_password": "BOOLEAN NOT NULL DEFAULT 0",
                "task_freelancer_id": "INTEGER",
            },
            "leave_records": {"duration_minutes": "INTEGER NOT NULL DEFAULT 480", "comp_leave_minutes_used": "INTEGER NOT NULL DEFAULT 0", "source_request_id": "INTEGER"},
            "monthly_dtr": {"approved_overtime_minutes": "INTEGER NOT NULL DEFAULT 0", "comp_leave_earned_minutes": "INTEGER NOT NULL DEFAULT 0", "comp_leave_used_minutes": "INTEGER NOT NULL DEFAULT 0", "comp_leave_opening_balance_minutes": "INTEGER NOT NULL DEFAULT 0", "comp_leave_closing_balance_minutes": "INTEGER NOT NULL DEFAULT 0", "daily_task_entries": "INTEGER NOT NULL DEFAULT 0", "daily_task_minutes": "INTEGER NOT NULL DEFAULT 0", "task_missing_days": "INTEGER NOT NULL DEFAULT 0", "task_variance_days": "INTEGER NOT NULL DEFAULT 0", "task_review_status": "TEXT NOT NULL DEFAULT 'UNREVIEWED'", "pending_overtime_claims": "INTEGER NOT NULL DEFAULT 0", "pending_leave_requests": "INTEGER NOT NULL DEFAULT 0"},
            "dtr_daily_lines": {"approved_overtime_minutes": "INTEGER NOT NULL DEFAULT 0", "comp_leave_earned_minutes": "INTEGER NOT NULL DEFAULT 0", "comp_leave_used_minutes": "INTEGER NOT NULL DEFAULT 0", "task_minutes": "INTEGER NOT NULL DEFAULT 0", "task_entry_count": "INTEGER NOT NULL DEFAULT 0", "task_summary": "TEXT", "task_variance_minutes": "INTEGER NOT NULL DEFAULT 0"},
            "daily_tasks": {"portal_task_id": "INTEGER", "synced_project_task_id": "INTEGER", "completion_percentage": "INTEGER NOT NULL DEFAULT 0"},
            "overtime_claims": {"planned_start_utc": "DATETIME", "planned_end_utc": "DATETIME", "actual_time_out_utc": "DATETIME", "claimed_time_out_utc": "DATETIME", "approved_time_out_utc": "DATETIME", "missing_time_out_reason": "TEXT", "final_submitted_at": "DATETIME"},
            "dtr_task_lines": {"completion_percentage": "INTEGER NOT NULL DEFAULT 0"},
            "portal_projects": {"project_category": "TEXT"},
        }
        for table_name, columns in migrations.items():
            for column_name, definition in columns.items():
                _ensure_column(connection, table_name, column_name, definition)
        connection.execute("UPDATE hr_admin_accounts SET role = 'ADMIN' WHERE role IS NULL OR TRIM(role) = ''")
        connection.execute("CREATE INDEX IF NOT EXISTS ix_daily_tasks_synced_project_task ON daily_tasks (synced_project_task_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS ix_daily_tasks_portal_task_id ON daily_tasks (portal_task_id)")
        connection.commit()


def initialize_database() -> None:
    """Create the schema for SQLite development or PostgreSQL production."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if DATABASE_DIALECT == "sqlite":
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(DATABASE_PATH, timeout=30)) as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 30000")

    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _run_sqlite_schema_migrations()

    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_attendance_event_daily_type ON attendance_events (freelancer_id, attendance_date, event_type)")

def dispose_database() -> None:
    """Close pooled database connections during shutdown and test cleanup."""
    close_all_sessions()
    engine.dispose()


def get_db() -> Generator[Session, None, None]:
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()


def database_is_available() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
