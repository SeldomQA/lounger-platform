import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{BASE_DIR / 'lounger_platform.db'}"
)

PROJECTS_DIR = BASE_DIR / "projects"

REPORTS_DIR = BASE_DIR / "reports"
