import os
import sys
import subprocess
import shlex
import tempfile
from pathlib import Path
from typing import List, Optional
from hst.repo import get_repo_paths
from hst.repo.head import get_current_commit_oid, update_head
from hst.repo.index import read_index
from hst.hst_objects import Commit, Tree


def run(argv: List[str]):
    """
    Create a new commit in the repository.
    """
    message = _get_commit_message(argv)
    repo_root, hst_dir = get_repo_paths()
    index = read_index(hst_dir)

    # Build a tree object from index
    tree = _build_tree(repo_root, index)
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


def _build_tree(repo_root: Path, index: dict, base_path: Optional[Path] = None) -> Tree:
    """
    Recursively build a tree object from the index.

    index: mapping from relative paths (str) to blob OIDs
    base_path: current directory relative to repo_root
    """
    if base_path is None:
        base_path = Path("")

    entries = []

    # Find all direct children (files and subdirectories) under base_path
    direct_children = {}  # name -> oid (for files) or None (for directories)

    for path_str, blob_oid in index.items():
        path = Path(path_str)

        # Skip if not under current base_path
        if base_path != Path(""):
            try:
                rel_path = path.relative_to(base_path)
            except ValueError:
                continue
        else:
            rel_path = path

        # Get the immediate child name
        if len(rel_path.parts) == 1:
            # This is a direct file child
            direct_children[rel_path.parts[0]] = blob_oid
        elif len(rel_path.parts) > 1:
            # This indicates a subdirectory
            subdir_name = rel_path.parts[0]
            if subdir_name not in direct_children:
                direct_children[subdir_name] = None  # Mark as directory

    # Process direct children
    for name, oid in direct_children.items():
        if oid is not None:
            # It's a file
            entries.append(("100644", name, oid))
        else:
            # It's a directory - recursively build its tree
            subdir_path = base_path / name if base_path != Path("") else Path(name)
            sub_tree = _build_tree(repo_root, index, subdir_path)
            sub_oid = sub_tree.oid()  # Tree stores itself on creation
            entries.append(("040000", name, sub_oid))

    # Sort entries by name (like Git does)
    entries.sort(key=lambda x: x[1])
    return Tree(entries)
