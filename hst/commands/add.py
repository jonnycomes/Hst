from pathlib import Path
from typing import List
from hst.hst_objects import Blob
from hst.repo import get_repo_paths, HST_DIRNAME
from hst.repo.index import read_index, write_index
import sys


def run(paths: List[str]):
    """
    Stage the given paths for commit.
    """
    if not paths:
        print("Usage: hst add <path> [<path> ...]")
        sys.exit(1)

    repo_root, hst_dir = get_repo_paths()

    files_to_add = collect_files(paths, repo_root)
    staged_entries = read_index(hst_dir)

    for file_path in files_to_add:
        blob = Blob(file_path.read_bytes())
        oid = blob.oid()
        rel_path = file_path.relative_to(repo_root)
        staged_entries[str(rel_path)] = oid

    write_index(hst_dir, staged_entries)
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
        if HST_DIRNAME in abs_path.parts:
            continue
        if abs_path.is_file():
            files.append(abs_path)
        elif abs_path.is_dir():
            # recursively add files
            files.extend(
                [
                    f
                    for f in abs_path.rglob("*")
                    if f.is_file() and HST_DIRNAME not in f.parts
                ]
            )
    return files
