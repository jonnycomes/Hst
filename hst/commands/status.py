from pathlib import Path
from typing import Dict, List, Tuple
from hst.repo import get_repo_paths, HST_DIRNAME
from hst.repo.head import get_current_commit_oid, get_current_branch
from hst.repo.index import read_index
from hst.repo.objects import read_object
from hst.hst_objects import Blob, Tree, Commit


def run(argv: List[str]):
    """
    Run the status command.
    """
    repo_root, hst_dir = get_repo_paths()

    branch, head_tree = _get_branch_and_head_tree(hst_dir)
    index = read_index(hst_dir)
    worktree = _scan_working_tree(repo_root)

    staged, unstaged, untracked = _classify_changes(head_tree, index, worktree)

    print(f"On branch {branch}")  # TODO: resolve current branch name

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

    return branch, _read_tree_recursive(hst_dir, commit_obj.tree)


def _scan_working_tree(repo_root: Path) -> Dict[str, str]:
    """
    Walk repo_root (excluding .hst) and hash each file into {path: oid}.
    """
    mapping = {}
    for path in repo_root.rglob("*"):
        if path.is_file() and HST_DIRNAME not in path.parts:
            rel = str(path.relative_to(repo_root))
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


def _read_tree_recursive(hst_dir: Path, oid: str, prefix="") -> Dict[str, str]:
    """Recursively read a tree object into {path: blob_oid}."""
    tree_obj = read_object(hst_dir, oid, Tree, store=False)
    mapping = {}
    if not tree_obj:
        return mapping

    for mode, name, child_oid in tree_obj.entries:
        path = f"{prefix}{name}"
        if mode == "040000":  # sub-tree
            mapping.update(_read_tree_recursive(hst_dir, child_oid, prefix=f"{path}/"))
        else:
            mapping[path] = child_oid
    return mapping
