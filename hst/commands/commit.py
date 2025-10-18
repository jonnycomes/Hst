import os
import sys
import subprocess
import shlex
import tempfile
from pathlib import Path
from typing import List
from hst.repo import get_repo_paths
from hst.repo.head import get_current_commit_oid, update_head
from hst.repo.index import read_index
from hst.repo.objects import read_object, build_tree
from hst.hst_objects import Commit


def run(argv: List[str]):
    """
    Create a new commit in the repository.
    """
    repo_root, hst_dir = get_repo_paths()
    index = read_index(hst_dir)

    # Check if there's anything to commit
    if not _has_changes_to_commit(hst_dir, index):
        print("nothing to commit, working tree clean")
        sys.exit(1)

    message = _get_commit_message(argv)

    # Build a tree object from index
    tree = build_tree(repo_root, index)
    tree_oid = tree.oid()

    # Get parent commit if HEAD exists
    parent = get_current_commit_oid(hst_dir)

    # Create and write commit object
    commit = Commit(
        tree=tree_oid,
        parents=[parent],
        author=os.getenv("USER", "unknown"),
        committer=os.getenv("USER", "unknown"),
        message=message,
    )
    commit_oid = commit.oid()

    # Update HEAD
    update_head(hst_dir, commit_oid)

    print(f"[hst] Commit {commit_oid} created.")


def _get_commit_message(argv: List[str]) -> str:
    if "-m" in argv:
        m_index = argv.index("-m")
        if m_index + 1 >= len(argv):
            print("error: option '-m' requires an argument")
            sys.exit(1)
        return argv[m_index + 1]

    # No -m flag -> open editor
    editor = os.environ.get("EDITOR", "vi")
    with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as tf:
        temp_path = Path(tf.name)

    subprocess.run(shlex.split(f"{editor} {temp_path}"))

    with open(temp_path, "r") as f:
        message = f.read().strip()

    # Clean up temp file
    temp_path.unlink(missing_ok=True)

    if not message:
        print("Aborting commit due to empty commit message.")
        sys.exit(1)

    return message


def _has_changes_to_commit(hst_dir: Path, index: dict) -> bool:
    """
    Check if there are staged changes to commit.

    Returns True if there are changes, False if nothing to commit.
    """
    # If index is empty, there's nothing to commit
    if not index:
        return False

    # Get current commit's tree if it exists
    current_commit_oid = get_current_commit_oid(hst_dir)
    if current_commit_oid is None:
        # No previous commits, so any staged files are changes
        return True  # Read current commit and get its tree

    commit_obj = read_object(hst_dir, current_commit_oid, Commit)
    if commit_obj is None:
        # Commit object not found, treat as changes
        return True

    current_tree_oid = commit_obj.tree

    # Build tree from index and compare with current tree
    repo_root, _ = get_repo_paths()
    staged_tree = build_tree(repo_root, index)
    staged_tree_oid = staged_tree.oid()

    # If tree OIDs are different, there are changes
    return current_tree_oid != staged_tree_oid
