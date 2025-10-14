from pathlib import Path
from typing import List, Tuple
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

    files_to_add, files_to_delete = collect_files_and_deletions(
        paths, repo_root, hst_dir
    )
    staged_entries = read_index(hst_dir)

    # Stage file additions/modifications
    for file_path in files_to_add:
        blob = Blob(file_path.read_bytes())
        oid = blob.oid()
        rel_path = file_path.relative_to(repo_root)
        staged_entries[str(rel_path)] = oid

    # Stage file deletions
    for deleted_path in files_to_delete:
        if deleted_path in staged_entries:
            del staged_entries[deleted_path]

    write_index(hst_dir, staged_entries)

    total_changes = len(files_to_add) + len(files_to_delete)
    if files_to_add:
        print(f"Staged {len(files_to_add)} file(s).")
    if files_to_delete:
        print(f"Staged {len(files_to_delete)} deletion(s).")
    if total_changes == 0:
        print("No changes to stage.")


def collect_files_and_deletions(
    paths: List[str], repo_root: Path, hst_dir: Path
) -> Tuple[List[Path], List[str]]:
    """
    Expand directories and normalize file paths.
    Returns (files_to_add, files_to_delete).

    - files_to_add: existing files that should be staged
    - files_to_delete: paths that don't exist but are in the index (deletions to stage)
    """
    files_to_add = []
    files_to_delete = []

    # Read current index to check for deleted files
    staged_entries = read_index(hst_dir)

    for p in paths:
        abs_path = (Path.cwd() / p).resolve()

        # Skip .hst directory
        if HST_DIRNAME in abs_path.parts:
            continue

        if abs_path.exists():
            # Handle existing files/directories
            if abs_path.is_file():
                files_to_add.append(abs_path)
            elif abs_path.is_dir():
                # recursively add files
                files_to_add.extend(
                    [
                        f
                        for f in abs_path.rglob("*")
                        if f.is_file() and HST_DIRNAME not in f.parts
                    ]
                )
        else:
            # Path doesn't exist - check if it's a deletion
            try:
                rel_path = abs_path.relative_to(repo_root)
                rel_path_str = str(rel_path)

                if rel_path_str in staged_entries:
                    # File was deleted from working directory but exists in index
                    files_to_delete.append(rel_path_str)
                else:
                    print(
                        f"Warning: '{p}' does not exist and is not in the index, skipping"
                    )
            except ValueError:
                # Path is outside repo
                print(f"Warning: '{p}' is not within the repository, skipping")

    return files_to_add, files_to_delete
