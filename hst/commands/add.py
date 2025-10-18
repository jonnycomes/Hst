from pathlib import Path
from typing import List, Tuple
from hst.hst_objects import Blob
from hst.repo import get_repo_paths, HST_DIRNAME
from hst.repo.index import read_index, write_index
from hst.repo.worktree import scan_working_tree
import sys


def run(paths: List[str]):
    """
    Stage the given paths for commit.
    """
    # Check for --all flag
    if "--all" in paths or "-A" in paths:
        # Remove the flag from paths
        paths = [p for p in paths if p not in ["--all", "-A"]]
        if paths:
            print("Warning: --all flag ignores other paths")
        _add_all()
        return

    if not paths:
        print("Usage: hst add <path> [<path> ...] or hst add --all")
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


def _add_all():
    """
    Stage all changes in the repository (like git add --all).
    This includes new files, modifications, and deletions.
    """
    repo_root, hst_dir = get_repo_paths()

    # Get current index
    staged_entries = read_index(hst_dir)

    # Scan working directory for all files using shared function
    worktree_files = scan_working_tree(repo_root)

    # Find all paths that exist in either working directory or index
    all_paths = set(worktree_files.keys()) | set(staged_entries.keys())

    files_added = 0
    files_deleted = 0
    files_modified = 0

    for path in all_paths:
        worktree_oid = worktree_files.get(path)
        index_oid = staged_entries.get(path)

        if worktree_oid and not index_oid:
            # New file
            staged_entries[path] = worktree_oid
            files_added += 1
        elif worktree_oid and index_oid and worktree_oid != index_oid:
            # Modified file
            staged_entries[path] = worktree_oid
            files_modified += 1
        elif not worktree_oid and index_oid:
            # Deleted file
            del staged_entries[path]
            files_deleted += 1
        # If worktree_oid == index_oid, no change needed

    # Write updated index
    write_index(hst_dir, staged_entries)

    # Report results
    total_changes = files_added + files_modified + files_deleted
    if total_changes == 0:
        print("No changes to stage.")
    else:
        changes = []
        if files_added > 0:
            changes.append(f"{files_added} new file(s)")
        if files_modified > 0:
            changes.append(f"{files_modified} modified file(s)")
        if files_deleted > 0:
            changes.append(f"{files_deleted} deletion(s)")

        print(f"Staged {', '.join(changes)}.")
