from pathlib import Path
from typing import Optional
from hst.repo.objects import read_object
from hst.components import Commit


def resolve_commit_ref(hst_dir: Path, commit_ref: str) -> Optional[str]:
    """
    Resolve a commit reference to a commit hash.

    Supports:
    - Full commit hashes (40 characters)
    - Short commit hashes (7+ characters)
    - Branch names
    - Remote branch names (remote/branch format)

    Args:
        hst_dir: Path to the .hst directory
        commit_ref: The reference to resolve

    Returns:
        Full commit hash if found, None otherwise
    """
    # Try as full commit hash first
    if len(commit_ref) == 40:
        # Verify it's a valid commit
        commit_obj = read_object(hst_dir, commit_ref, Commit, store=False)
        if commit_obj:
            return commit_ref

    # Try as short commit hash (expand to full hash)
    if len(commit_ref) >= 7:
        objects_dir = hst_dir / "objects"
        if objects_dir.exists():
            for subdir in objects_dir.iterdir():
                if subdir.is_dir() and subdir.name == commit_ref[:2]:
                    for obj_file in subdir.iterdir():
                        full_hash = subdir.name + obj_file.name
                        if full_hash.startswith(commit_ref):
                            # Verify it's a commit
                            commit_obj = read_object(
                                hst_dir, full_hash, Commit, store=False
                            )
                            if commit_obj:
                                return full_hash

    # Try as remote branch name (remote/branch format)
    if "/" in commit_ref:
        remote_branch_path = hst_dir / "refs" / "remotes" / commit_ref
        if remote_branch_path.exists():
            try:
                return remote_branch_path.read_text().strip()
            except OSError:
                pass

    # Try as branch name
    branch_path = hst_dir / "refs" / "heads" / commit_ref
    if branch_path.exists():
        try:
            return branch_path.read_text().strip()
        except OSError:
            pass

    return None


def is_ancestor(hst_dir: Path, ancestor_oid: str, descendant_oid: str) -> bool:
    """
    Check if ancestor_oid is an ancestor of descendant_oid.

    Walk back through the commit history from descendant to see if we reach ancestor.

    Args:
        hst_dir: Path to the .hst directory
        ancestor_oid: The potential ancestor commit hash
        descendant_oid: The descendant commit hash

    Returns:
        True if ancestor_oid is an ancestor of descendant_oid
    """
    if ancestor_oid == descendant_oid:
        return True

    visited = set()
    queue = [descendant_oid]

    while queue:
        current_oid = queue.pop(0)

        if current_oid in visited:
            continue
        visited.add(current_oid)

        if current_oid == ancestor_oid:
            return True

        # Read the commit and add its parents to the queue
        commit_obj = read_object(hst_dir, current_oid, Commit, store=False)
        if commit_obj and commit_obj.parents:
            queue.extend(commit_obj.parents)

    return False
