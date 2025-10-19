import sys
import shutil
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


def clone_repository(source_path: Path, dest_path: Path) -> bool:
    """
    Clone a repository from source_path to dest_path.

    Returns:
        True if successful, False otherwise
    """
    source_path = source_path.resolve()
    dest_path = dest_path.resolve()

    # Check if source is a valid hst repository
    source_hst_dir = source_path / HST_DIRNAME
    if not source_hst_dir.exists():
        print(f"fatal: '{source_path}' does not appear to be a hst repository")
        return False

    # Check if destination already exists
    if dest_path.exists():
        print(f"fatal: destination path '{dest_path}' already exists")
        return False

    # Create destination directory
    try:
        dest_path.mkdir(parents=True)
        print(f"Cloning into '{dest_path}'...")
    except OSError as e:
        print(f"fatal: could not create directory '{dest_path}': {e}")
        return False

    # Copy the .hst directory
    dest_hst_dir = dest_path / HST_DIRNAME
    try:
        shutil.copytree(source_hst_dir, dest_hst_dir)
        return True
    except OSError as e:
        print(f"fatal: could not copy repository data: {e}")
        # Clean up the destination directory
        shutil.rmtree(dest_path, ignore_errors=True)
        return False
