from pathlib import Path

REPO_DIR = ".hst"


def find_repo_root(start_dir: Path) -> Path:
    """Walk up from start_dir to find the repository root (.hst folder)."""
    path = start_dir.resolve()
    while path != path.parent:
        if (path / REPO_DIR).exists():
            return path
        path = path.parent
    raise RuntimeError("Not inside a Hst repository")