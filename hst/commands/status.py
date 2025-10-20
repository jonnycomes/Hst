from pathlib import Path
from typing import Dict, List, Tuple
from hst.repo import get_repo_paths
from hst.repo.head import get_current_commit_oid, get_current_branch
from hst.repo.index import read_index
from hst.repo.objects import read_object
from hst.repo.worktree import read_tree_recursive, scan_working_tree
from hst.repo.utils import (
    parse_path_arguments,
    filter_dict_by_paths,
    path_matches_filter,
)
from hst.components import Commit
from hst.colors import RED, GREEN, RESET


def run(argv: List[str]):
    """
    Run the status command.
    """
    repo_root, hst_dir = get_repo_paths()

    # Parse path arguments
    filter_paths = parse_path_arguments(argv, repo_root) if argv else None

    branch, head_tree = _get_branch_and_head_tree(hst_dir)
    index = read_index(hst_dir)
    worktree = scan_working_tree(repo_root, filter_paths)

    # Filter other collections by paths if specified
    if filter_paths:
        head_tree = filter_dict_by_paths(head_tree, filter_paths, path_matches_filter)
        index = filter_dict_by_paths(index, filter_paths, path_matches_filter)

    staged, unstaged, untracked = _classify_changes(head_tree, index, worktree)

    print(f"On branch {branch}")

    if staged:
        print("\nChanges to be committed:")
        for path, change in staged:
            print(f"{GREEN}    {change}:   {path}{RESET}")

    if unstaged:
        print("\nChanges not staged for commit:")
        for path, change in unstaged:
            print(f"{RED}    {change}:   {path}{RESET}")

    if untracked:
        print("\nUntracked files:")
        for path in untracked:
            print(f"{RED}    {path}{RESET}")


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
