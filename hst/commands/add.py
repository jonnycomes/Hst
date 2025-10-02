from pathlib import Path
from typing import List
import zlib
from hst.objects import Blob
from hst.repo import find_repo_root, REPO_DIR

import json


def run(paths: List[str]):
    """
    Stage the given paths for commit.
    """
    repo_root = find_repo_root(Path.cwd())
    objects_dir = repo_root / REPO_DIR / "objects"
    index_file = repo_root / REPO_DIR / "index"

    files_to_add = collect_files(paths, repo_root)
    staged_entries = load_index(index_file)

    for file_path in files_to_add:
        blob = Blob(file_path.read_bytes())
        oid = blob.oid()
        rel_path = file_path.relative_to(repo_root)
        staged_entries[str(rel_path)] = oid

    save_index(index_file, staged_entries)
    print(f"Staged {len(files_to_add)} file(s).")


def collect_files(paths: List[str], repo_root: Path) -> List[Path]:
    """
    Expand directories and normalize file paths.
    Ignores .hst itself.
    """
    files = []
    for p in paths:
        abs_path = (Path.cwd() / p).resolve()
        if not abs_path.exists():
            print(f"Warning: {abs_path} does not exist, skipping")
            continue
        if REPO_DIR in abs_path.parts:
            continue
        if abs_path.is_file():
            files.append(abs_path)
        elif abs_path.is_dir():
            # recursively add files
            files.extend(
                [
                    f
                    for f in abs_path.rglob("*")
                    if f.is_file() and REPO_DIR not in f.parts
                ]
            )
    return files


def load_index(index_file: Path) -> dict:
    """Load the index from disk (simple JSON for now)."""
    if index_file.exists():
        return json.loads(index_file.read_text())
    return {}


def save_index(index_file: Path, index: dict):
    """Save the staging index to disk (JSON for now)."""
    index_file.parent.mkdir(parents=True, exist_ok=True)
    index_file.write_text(json.dumps(index, indent=2))
