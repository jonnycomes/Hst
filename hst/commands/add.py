from pathlib import Path
from typing import List
import zlib
from hst.objects import Blob

import json


def run(paths: List[str], repo_dir: str=".hst"):
    """
    Stage the given paths for commit.
    """
    repo_root = find_repo_root(Path.cwd())
    objects_dir = repo_root / repo_dir / "objects"
    index_file = repo_root / repo_dir / "index"

    files_to_add = collect_files(paths, repo_root)
    staged_entries = load_index(index_file)

    for file_path in files_to_add:
        blob = Blob(file_path.read_bytes())
        oid = store_blob(blob, objects_dir)
        rel_path = file_path.relative_to(repo_root)
        staged_entries[str(rel_path)] = oid

    save_index(index_file, staged_entries)
    print(f"Staged {len(files_to_add)} file(s).")


def find_repo_root(start_dir: Path) -> Path:
    """Walk up from start_dir to find the repository root (.hst folder)."""
    path = start_dir.resolve()
    while path != path.parent:
        if (path / repo_dir).exists():
            return path
        path = path.parent
    raise RuntimeError("Not inside a Hst repository")


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
        if repo_dir in abs_path.parts:
            continue
        if abs_path.is_file():
            files.append(abs_path)
        elif abs_path.is_dir():
            # recursively add files
            files.extend(
                [
                    f
                    for f in abs_path.rglob("*")
                    if f.is_file() and repo_dir not in f.parts
                ]
            )
    return files


def store_blob(blob: Blob, objects_dir: Path) -> str:
    """
    Compress and store a blob object in the objects directory.
    Returns the SHA-1 object ID.
    """
    oid = blob.oid()
    path = objects_dir / oid[:2] / oid[2:]
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(blob.compressed())
    return oid


def load_index(index_file: Path) -> dict:
    """Load the index from disk (simple JSON for now)."""
    if index_file.exists():
        return json.loads(index_file.read_text())
    return {}


def save_index(index_file: Path, index: dict):
    """Save the staging index to disk (JSON for now)."""
    index_file.parent.mkdir(parents=True, exist_ok=True)
    index_file.write_text(json.dumps(index, indent=2))
