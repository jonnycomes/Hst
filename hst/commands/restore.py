import sys
from pathlib import Path
from typing import List
from hst.repo import get_repo_paths
from hst.repo.head import get_current_commit_oid
from hst.repo.index import read_index, write_index
from hst.repo.objects import read_object
from hst.repo.worktree import read_tree_recursive
from hst.components import Commit, Blob


def run(argv: List[str]):
    """
    Run the restore command.

    hst restore <file>         - Restore file from index to working tree
    hst restore --staged <file> - Restore file from HEAD to index (unstage)
    """
    if not argv:
        print("Usage: hst restore [--staged] <file> [<file> ...]")
        sys.exit(1)

    # Check for --staged flag
    is_staged = "--staged" in argv
    if is_staged:
        argv = [arg for arg in argv if arg != "--staged"]

    if not argv:
        print("Usage: hst restore [--staged] <file> [<file> ...]")
        sys.exit(1)

    repo_root, hst_dir = get_repo_paths()

    if is_staged:
        _restore_staged(argv, repo_root, hst_dir)
    else:
        _restore_worktree(argv, repo_root, hst_dir)


def _restore_worktree(file_paths: List[str], repo_root: Path, hst_dir: Path):
    """Restore files from index to working tree (discard working tree changes)."""
    # Get HEAD tree to check if files exist there
    current_commit_oid = get_current_commit_oid(hst_dir)
    head_tree = {}
    if current_commit_oid:
        commit_obj = read_object(hst_dir, current_commit_oid, Commit, store=False)
        if commit_obj:
            head_tree = read_tree_recursive(hst_dir, commit_obj.tree)

    index = read_index(hst_dir)
    restored_files = []

    for file_path_str in file_paths:
        # Convert to relative path from repo root
        file_path = Path(file_path_str)
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path

        try:
            rel_path = file_path.relative_to(repo_root)
            rel_path_str = str(rel_path)
        except ValueError:
            print(f"error: pathspec '{file_path_str}' is outside repository")
            continue

        # Find matching files in index (exact match or directory)
        matching_files = _find_matching_files(index, rel_path_str)
        if not matching_files:
            print(
                f"error: pathspec '{file_path_str}' did not match any file(s) known to hst"
            )
            continue

        # Restore each matching file
        for file_rel_path in matching_files:
            full_path = repo_root / file_rel_path

            # Check if file exists in HEAD
            if file_rel_path in head_tree:
                # File exists in HEAD - restore from index (which should match HEAD or be staged)
                blob_oid = index[file_rel_path]
                blob_obj = read_object(hst_dir, blob_oid, Blob, store=False)
                if not blob_obj:
                    print(f"error: cannot read blob {blob_oid} for {file_rel_path}")
                    continue

                # Write blob content to working tree
                try:
                    # Create parent directories if needed
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_bytes(blob_obj.data)
                    restored_files.append(file_rel_path)
                except OSError as e:
                    print(f"error: cannot restore {file_rel_path}: {e}")
            else:
                # File doesn't exist in HEAD but is in index (new file)
                # Remove it from working tree to match HEAD state
                try:
                    if full_path.exists():
                        full_path.unlink()
                        restored_files.append(file_rel_path)
                except OSError as e:
                    print(f"error: cannot remove {file_rel_path}: {e}")

    if restored_files:
        print(f"Restored {len(restored_files)} file(s) from index to working tree:")
        for file_path in restored_files:
            print(f"  {file_path}")


def _restore_staged(file_paths: List[str], repo_root: Path, hst_dir: Path):
    """Restore files from HEAD to index (unstage changes)."""
    # Get HEAD tree
    current_commit_oid = get_current_commit_oid(hst_dir)
    if not current_commit_oid:
        print("error: no HEAD commit found")
        sys.exit(1)

    commit_obj = read_object(hst_dir, current_commit_oid, Commit, store=False)
    if not commit_obj:
        print("error: cannot read HEAD commit")
        sys.exit(1)

    head_tree = read_tree_recursive(hst_dir, commit_obj.tree)
    index = read_index(hst_dir)
    restored_files = []

    for file_path_str in file_paths:
        # Convert to relative path from repo root
        file_path = Path(file_path_str)
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path

        try:
            rel_path = file_path.relative_to(repo_root)
            rel_path_str = str(rel_path)
        except ValueError:
            print(f"error: pathspec '{file_path_str}' is outside repository")
            continue

        # Find matching files in index and HEAD
        index_matches = _find_matching_files(index, rel_path_str)
        head_matches = _find_matching_files(head_tree, rel_path_str)
        all_matches = set(index_matches) | set(head_matches)

        if not all_matches:
            print(
                f"error: pathspec '{file_path_str}' did not match any file(s) known to hst"
            )
            continue

        # Process each matching file
        for file_rel_path in all_matches:
            if file_rel_path in head_tree:
                # File exists in HEAD - restore it to index
                index[file_rel_path] = head_tree[file_rel_path]
                restored_files.append(f"restored: {file_rel_path}")
            elif file_rel_path in index:
                # File doesn't exist in HEAD but is staged - remove from index
                del index[file_rel_path]
                restored_files.append(f"unstaged: {file_rel_path}")

    # Write updated index
    write_index(hst_dir, index)

    if restored_files:
        print(f"Unstaged {len(restored_files)} file(s):")
        for file_status in restored_files:
            print(f"  {file_status}")


def _find_matching_files(index: dict, path_spec: str) -> List[str]:
    """
    Find files in index that match the given path specification.

    Args:
        index: Dictionary mapping file paths to blob OIDs
        path_spec: Path specification (file or directory)

    Returns:
        List of matching file paths from the index
    """
    matching_files = []

    # Normalize path spec (remove trailing slash if it's a directory)
    normalized_spec = path_spec.rstrip("/")

    # Special case: empty string or "." means all files in current directory/repo
    if normalized_spec == "" or normalized_spec == ".":
        return list(index.keys())

    for file_path in index.keys():
        # Exact match
        if file_path == normalized_spec:
            matching_files.append(file_path)
        # Directory match (file is under the specified directory)
        elif file_path.startswith(normalized_spec + "/"):
            matching_files.append(file_path)

    return matching_files
