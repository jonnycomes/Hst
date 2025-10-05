import sys
import json
import hashlib
import zlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from hst.repo import find_repo_root, REPO_DIR
from hst.objects import Blob, Tree, Commit, Object


def run(argv: List[str]):
    """
    Run the status command.
    """
    repo_root = find_repo_root(Path.cwd())
    repo_dir = repo_root / REPO_DIR

    branch, head_tree = _get_branch_and_head_tree(repo_dir)
    index = _read_index(repo_dir)
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


def _get_branch_and_head_tree(repo_dir: Path) -> Dict[str, str]:
    """
    Read HEAD, resolve to commit, and load the commit's tree mapping.
    Returns branch, {path: oid}.
    """
    head_path = repo_dir / "HEAD"
    if not head_path.exists():
        return None, {}

    head_val = head_path.read_text().strip()
    if head_val.startswith("ref: "):
        ref_path = repo_dir / head_val[5:]
        if not ref_path.exists():
            return None, {}
        commit_oid = ref_path.read_text().strip()
        branch = head_val.split("/")[-1]
    else:
        commit_oid = head_val
        branch = head_val

    commit_obj = _read_object(repo_dir, commit_oid, Commit)
    if not commit_obj:
        return branch, {}

    return branch, _read_tree_recursive(repo_dir, commit_obj.tree)


def _read_index(repo_dir: Path) -> Dict[str, str]:
    """
    Read index file into {path: oid}.
    """
    index_path = repo_dir / "index"
    if not index_path.exists():
        return {}

    with open(index_path, 'r') as file:
        return json.load(file)


def _scan_working_tree(repo_root: Path) -> Dict[str, str]:
    """
    Walk repo_root (excluding .hst) and hash each file into {path: oid}.
    """
    mapping = {}
    for path in repo_root.rglob("*"):
        if path.is_file() and REPO_DIR not in path.parts:
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


# ------------------------------
# Low-level object readers
# ------------------------------

def _read_object(repo_dir: Path, oid: str, cls) -> Optional[Object]:
    """Read and decompress an object by oid into the given class."""
    obj_path = repo_dir / "objects" / oid[:2] / oid[2:]
    if not obj_path.exists():
        return None
    
    data = zlib.decompress(obj_path.read_bytes())
    # Strip header
    header, _, content = data.partition(b"\x00")
    return cls.deserialize(content, store=False)  # Don't re-store when reading


def _read_tree_recursive(repo_dir: Path, oid: str, prefix="") -> Dict[str, str]:
    """Recursively read a tree object into {path: blob_oid}."""
    tree_obj = _read_object(repo_dir, oid, Tree)
    mapping = {}
    if not tree_obj:
        return mapping

    for mode, name, child_oid in tree_obj.entries:
        path = f"{prefix}{name}"
        if mode == "040000":  # sub-tree
            mapping.update(_read_tree_recursive(repo_dir, child_oid, prefix=f"{path}/"))
        else:
            mapping[path] = child_oid
    return mapping
