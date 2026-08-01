import os
from pathlib import Path

APP_NAME = "BIMFM Portal"
APP_VERSION = "2.3.9-release20.14-supervisor-dashboard-member-tools"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backups"
DATABASE_PATH = Path(
    os.getenv("BIMFM_HR_DATABASE", str(DATA_DIR / "hr.db"))
).expanduser().resolve()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip() or f"sqlite:///{DATABASE_PATH.as_posix()}"
# Render and some providers still expose the legacy postgres:// scheme.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgres://"):]
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgresql://"):]
DATABASE_DIALECT = DATABASE_URL.split(":", 1)[0].split("+", 1)[0].lower()

DEFAULT_TIMEZONE = "Asia/Manila"

SESSION_SECRET = os.getenv(
    "BIMFM_SESSION_SECRET",
    "CHANGE-THIS-BEFORE-PRODUCTION-LOCAL-DEVELOPMENT-ONLY",
)

COOKIE_HTTPS_ONLY = (
    os.getenv("BIMFM_COOKIE_HTTPS_ONLY", "false").strip().lower()
    == "true"
)

MAX_FAILED_LOGIN_ATTEMPTS = 5
ACCOUNT_LOCK_MINUTES = 15


# Legacy synchronization settings are retained only so old deployments and
# historical API clients fail gracefully. Release 20.14 reads live project data
# from PostgreSQL-native portal tables and does not require a sync agent.
PROJECT_SYNC_TOKEN = os.getenv("BIMFM_PROJECT_SYNC_TOKEN", "").strip()
PROJECT_SYNC_SOURCE_SYSTEM = os.getenv(
    "BIMFM_PROJECT_SYNC_SOURCE_SYSTEM",
    "BIMFM_TASK_MANAGER",
).strip().upper()
PROJECT_SYNC_USING_DEFAULT_TOKEN = not bool(PROJECT_SYNC_TOKEN)

# Optional one-time administrator bootstrap for cloud deployment.
# Set these in Render Environment. The account is created only when no
# administrator exists, and the password is never stored in source control.
BOOTSTRAP_ADMIN_USERNAME = os.getenv("BIMFM_BOOTSTRAP_ADMIN_USERNAME", "").strip().lower()
BOOTSTRAP_ADMIN_DISPLAY_NAME = os.getenv("BIMFM_BOOTSTRAP_ADMIN_DISPLAY_NAME", "").strip()
BOOTSTRAP_ADMIN_PASSWORD = os.getenv("BIMFM_BOOTSTRAP_ADMIN_PASSWORD", "")


# Production hardening
ENVIRONMENT = os.getenv("BIMFM_ENV", "development").strip().lower()
IS_PRODUCTION = ENVIRONMENT == "production"
LOG_LEVEL = os.getenv("BIMFM_LOG_LEVEL", "INFO").strip().upper()
API_RATE_LIMIT_PER_MINUTE = int(os.getenv("BIMFM_API_RATE_LIMIT_PER_MINUTE", "120"))
LOGIN_RATE_LIMIT_PER_MINUTE = int(os.getenv("BIMFM_LOGIN_RATE_LIMIT_PER_MINUTE", "20"))
TRUST_PROXY_HEADERS = os.getenv("BIMFM_TRUST_PROXY_HEADERS", "false").strip().lower() == "true"
