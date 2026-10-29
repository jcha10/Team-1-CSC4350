"""
All runtime configuration, read once from environment variables (and a
local backend/.env file if present). Every other module imports settings
from here instead of calling os.environ directly, so this file is the
complete list of knobs an operator can turn.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./smiley.db")

# Only needed if the frontend is served from a different origin than the
# API. The default dev setup (Vite proxy) and the production setup (FastAPI
# serves the built frontend) are both same-origin, so this is empty.
CORS_ORIGINS = _list("CORS_ORIGINS", "")

# Off by default so a fresh production database never gets the well-known
# demo accounts. Turn on explicitly for local dev / classroom demos.
SEED_DEMO_DATA = _bool("SEED_DEMO_DATA", False)

SIMULATOR_ENABLED = _bool("SIMULATOR_ENABLED", True)
SIMULATOR_INTERVAL_SECONDS = float(os.environ.get("SIMULATOR_INTERVAL_SECONDS", "4"))

SESSION_TTL_HOURS = float(os.environ.get("SESSION_TTL_HOURS", "12"))

LOGIN_MAX_FAILURES = int(os.environ.get("LOGIN_MAX_FAILURES", "5"))
LOGIN_LOCKOUT_MINUTES = float(os.environ.get("LOGIN_LOCKOUT_MINUTES", "15"))

FRONTEND_DIST = Path(
    os.environ.get("FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist")
)
