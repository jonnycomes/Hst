import sys
from pathlib import Path
from typing import Tuple

HST_DIRNAME = ".hst"


def find_repo_root(start_dir: Path) -> Path:
    """Walk up from start_dir to find the repository root (.hst folder)."""
    path = start_dir.resolve()
    while path != path.parent:
        if (path / HST_DIRNAME).exists():
            return path
        path = path.parent
    print("Not inside a Hst repository")
    sys.exit(1)


def get_repo_paths() -> Tuple[Path, Path]:
    """Get repository root and .hst directory paths.

    Returns:
        Tuple of (repo_root, hst_dir) where:
        - repo_root: The root directory of the repository
        - hst_dir: The .hst directory path
    """
    repo_root = find_repo_root(Path.cwd())
    hst_dir = repo_root / HST_DIRNAME
    return repo_root, hst_dir
