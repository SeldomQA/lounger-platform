import subprocess
from pathlib import Path
from ..config import PROJECTS_DIR


def clone_project(project_id: int, git_url: str) -> str:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    clone_dir = str(PROJECTS_DIR / str(project_id))

    if Path(clone_dir).exists():
        _pull(clone_dir)
    else:
        _clone(git_url, clone_dir)

    return clone_dir


def _clone(git_url: str, clone_dir: str):
    subprocess.run(
        ["git", "clone", git_url, clone_dir],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _pull(clone_dir: str):
    subprocess.run(
        ["git", "-C", clone_dir, "fetch", "origin"],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    subprocess.run(
        ["git", "-C", clone_dir, "reset", "--hard", "FETCH_HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )


def pull_project(clone_dir: str):
    if Path(clone_dir).exists():
        _pull(clone_dir)
