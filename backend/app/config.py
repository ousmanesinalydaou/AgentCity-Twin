import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def enabled(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"true", "1", "yes"}


def database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///" + (ROOT / "agentcity.sqlite3").as_posix())


def demo_enabled() -> bool:
    return enabled("DEMO_ENABLED", "true")


def public_origin() -> str:
    return os.getenv("APP_ORIGIN", "http://localhost:3100").rstrip("/")
