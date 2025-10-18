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

    # Check for --amend flag
    is_amend = "--amend" in argv
    if is_amend:
        argv = [arg for arg in argv if arg != "--amend"]  # Remove --amend from argv

    if is_amend:
        _amend_commit(argv, repo_root, hst_dir, index)
    else:
        _create_new_commit(argv, repo_root, hst_dir, index)


def _create_new_commit(argv: List[str], repo_root: Path, hst_dir: Path, index: dict):
    """Create a new commit (original behavior)."""
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


def _amend_commit(argv: List[str], repo_root: Path, hst_dir: Path, index: dict):
    """Amend the most recent commit."""
    # Check if there's a commit to amend
    current_commit_oid = get_current_commit_oid(hst_dir)
    if not current_commit_oid:
        print("error: nothing to amend")
        sys.exit(1)

    # Read the current commit
    current_commit = read_object(hst_dir, current_commit_oid, Commit)
    if not current_commit:
        print("error: cannot read current commit")
        sys.exit(1)

    # Get message for amended commit
    message = _get_amend_message(argv, current_commit.message)

    # Build tree from current index
    tree = build_tree(repo_root, index)
    tree_oid = tree.oid()

    # Use the parent(s) of the current commit, not the current commit itself
    parents = current_commit.parents

    # Create new commit with same parents as the commit being amended
    commit = Commit(
        tree=tree_oid,
        parents=parents,
        author=current_commit.author,  # Keep original author
        committer=os.getenv("USER", "unknown"),  # Update committer
        message=message,
        author_timestamp=current_commit.author_timestamp,  # Keep original timestamp
        author_tz=current_commit.author_tz,
    )
    commit_oid = commit.oid()

    # Update HEAD to point to the new commit
    update_head(hst_dir, commit_oid)

    print(f"[hst] Commit {current_commit_oid[:7]} amended as {commit_oid[:7]}")


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


def _get_amend_message(argv: List[str], current_message: str) -> str:
    """Get commit message for amend operation."""
    if "-m" in argv:
        # User provided a new message
        m_index = argv.index("-m")
        if m_index + 1 >= len(argv):
            print("error: option '-m' requires an argument")
            sys.exit(1)
        return argv[m_index + 1]

    # No -m flag -> open editor with current message as template
    editor = os.environ.get("EDITOR", "vi")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tmp", delete=False) as tf:
        tf.write(current_message)
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
