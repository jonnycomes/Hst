import json
from pathlib import Path
from typing import Dict


def read_index(hst_dir: Path) -> Dict[str, str]:
    """Read the index file into a path->oid mapping."""
    index_path = hst_dir / "index"
    if not index_path.exists():
        return {}

    with open(index_path, "r") as f:
        return json.load(f)


def write_index(hst_dir: Path, index: Dict[str, str]) -> None:
    """Write the index mapping to disk."""
    index_path = hst_dir / "index"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2))


def check_for_staged_changes(hst_dir: Path) -> bool:
    """
    Check if there are staged changes that differ from HEAD.
    Returns True if there are staged changes, False otherwise.
    """
    from hst.repo.head import get_current_commit_oid
    from hst.repo.objects import read_object
    from hst.repo.worktree import read_tree_recursive
    from hst.components import Commit

    # Read current index
    index = read_index(hst_dir)

    # Get current commit
    current_commit_oid = get_current_commit_oid(hst_dir)
    if not current_commit_oid:
        # No commits yet, any files in index are staged changes
        return len(index) > 0

    # Read HEAD commit tree
    commit_obj = read_object(hst_dir, current_commit_oid, Commit, store=False)
    if not commit_obj:
        return len(index) > 0

    head_tree = read_tree_recursive(hst_dir, commit_obj.tree)

    # Compare index with HEAD tree
    return index != head_tree
