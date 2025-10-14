from pathlib import Path
from typing import Dict, List, Tuple
from hst.repo import get_repo_paths, HST_DIRNAME
from hst.repo.head import get_current_commit_oid, get_current_branch
from hst.repo.index import read_index
from hst.repo.objects import read_object
from hst.repo.worktree import read_tree_recursive
from hst.hst_objects import Blob, Commit


def run(argv: List[str]):
    """
    Run the status command.
    """
    repo_root, hst_dir = get_repo_paths()

    # Parse path arguments
    filter_paths = _parse_path_arguments(argv, repo_root) if argv else None

    branch, head_tree = _get_branch_and_head_tree(hst_dir)
    index = read_index(hst_dir)
    worktree = _scan_working_tree(repo_root, filter_paths)

    # Filter other collections by paths if specified
    if filter_paths:
        head_tree = _filter_tree_by_paths(head_tree, filter_paths)
        index = _filter_index_by_paths(index, filter_paths)

    staged, unstaged, untracked = _classify_changes(head_tree, index, worktree)

    print(f"On branch {branch}")

    if staged:
        print("\nChanges to be committed:")
        for path, change in staged:
            print(f"    {change}:   {path}")

    if unstaged:
        print("\nChanges not staged for commit:")
        for path, change in unstaged:
            print(f"    {change}:   {path}")

    if untracked:
        print("\nUntracked files:")
        for path in untracked:
            print(f"    {path}")


def _get_branch_and_head_tree(hst_dir: Path) -> Dict[str, str]:
    """
    Read HEAD, resolve to commit, and load the commit's tree mapping.
    Returns branch, {path: oid}.
    """
    branch = get_current_branch(hst_dir)
    commit_oid = get_current_commit_oid(hst_dir)

    if not commit_oid:
        return branch, {}

    commit_obj = read_object(hst_dir, commit_oid, Commit, store=False)
    if not commit_obj:
        return branch, {}

    return branch, read_tree_recursive(hst_dir, commit_obj.tree)


def _scan_working_tree(
    repo_root: Path, filter_paths: List[str] = None
) -> Dict[str, str]:
    """
    Walk repo_root (excluding .hst) and hash each file into {path: oid}.
    If filter_paths is provided, only scan files matching those paths.
    """
    mapping = {}
    for path in repo_root.rglob("*"):
        if path.is_file() and HST_DIRNAME not in path.parts:
            rel = str(path.relative_to(repo_root))

            # Apply path filter if specified
            if filter_paths and not _path_matches_filter(rel, filter_paths):
                continue

            with open(path, "rb") as f:
                data = f.read()
            blob = Blob(data, store=False)  # Don't store, just compute hash
            mapping[rel] = blob.oid()
    return mapping


def _classify_changes(
    head: Dict[str, str],
    index: Dict[str, str],
    work: Dict[str, str],
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]], List[str]]:
    """
    Compare HEAD ↔ index ↔ working tree.
    Returns (staged, unstaged, untracked).
    Each staged/unstaged entry is (path, change_type).
    """
    staged = []
    unstaged = []
    untracked = []

    paths = set(head) | set(index) | set(work)

    for path in sorted(paths):
        head_oid = head.get(path)
        index_oid = index.get(path)
        work_oid = work.get(path)

        # --- staged ---
        if index_oid != head_oid:
            if head_oid is None:
                staged.append((path, "new file"))
            elif index_oid is None:
                staged.append((path, "deleted"))
            else:
                staged.append((path, "modified"))

        # --- unstaged ---
        if work_oid != index_oid:
            if index_oid is None and work_oid is not None:
                untracked.append(path)
            elif work_oid is None and index_oid is not None:
                unstaged.append((path, "deleted"))
            elif work_oid is not None and index_oid is not None:
                unstaged.append((path, "modified"))

    return staged, unstaged, untracked


def _parse_path_arguments(argv: List[str], repo_root: Path) -> List[str]:
    """
    Parse and validate path arguments.
    Returns a list of normalized relative paths from repo root.
    """
    filter_paths = []
    for arg in argv:
        path = Path(arg)

        # Convert to absolute path
        if not path.is_absolute():
            path = Path.cwd() / path

        # Normalize the path
        try:
            path = path.resolve()
        except (OSError, RuntimeError):
            print(f"Warning: Cannot resolve path '{arg}', skipping")
            continue

        # Check if path is within repo
        try:
            rel_path = path.relative_to(repo_root)
            filter_paths.append(str(rel_path))
        except ValueError:
            print(f"Warning: Path '{arg}' is not within the repository, skipping")
            continue

    return filter_paths


def _filter_tree_by_paths(
    tree: Dict[str, str], filter_paths: List[str]
) -> Dict[str, str]:
    """Filter tree entries to only include paths matching the filter."""
    if not filter_paths:
        return tree

    filtered = {}
    for path, oid in tree.items():
        if _path_matches_filter(path, filter_paths):
            filtered[path] = oid
    return filtered


def _filter_index_by_paths(
    index: Dict[str, str], filter_paths: List[str]
) -> Dict[str, str]:
    """Filter index entries to only include paths matching the filter."""
    if not filter_paths:
        return index

    filtered = {}
    for path, oid in index.items():
        if _path_matches_filter(path, filter_paths):
            filtered[path] = oid
    return filtered


def _path_matches_filter(file_path: str, filter_paths: List[str]) -> bool:
    """
    Check if a file path should be included based on filter paths.
    Returns True if the file_path matches any of the filter_paths.
    """
    file_path_parts = Path(file_path).parts

    for filter_path in filter_paths:
        filter_path_parts = Path(filter_path).parts

        # Exact match
        if file_path == filter_path:
            return True

        # Check if file is under a directory filter
        if len(file_path_parts) >= len(filter_path_parts):
            if file_path_parts[: len(filter_path_parts)] == filter_path_parts:
                return True

    return False
