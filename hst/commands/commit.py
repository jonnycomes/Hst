import os
import sys
import subprocess
import shlex
import tempfile
import json
import time
from pathlib import Path
from typing import List, Optional
from hst.repo import find_repo_root, REPO_DIR
from hst.objects import Commit, Tree


def run(argv: List[str]):
    """
    Create a new commit in the repository.
    """
    message = _get_commit_message(argv)
    repo_root = find_repo_root(Path.cwd())
    index = _read_index(repo_root)
    
    # Build a tree object from index
    tree = _build_tree(repo_root, index)
    tree_oid = tree.oid()
    
    # Get parent commit if HEAD exists
    parent = _get_head_commit(repo_root)
    
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
    _update_head(repo_root, commit_oid)

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

def _read_index(repo_root: Path) -> dict:
    index_path = repo_root / REPO_DIR / "index"
    if not index_path.exists():
        return {}
    with open(index_path) as f:
        return json.load(f)


def _build_tree(repo_root: Path, index: dict, base_path: Optional[Path] = None) -> Tree:
    """
    Recursively build a tree object from the index.

    index: mapping from relative paths (str) to blob OIDs
    base_path: current directory relative to repo_root
    """
    if base_path is None:
        base_path = Path("")

    entries = []

    # Collect files and directories directly under base_path
    children = {}
    for path_str, blob_oid in index.items():
        path = Path(path_str)
        if base_path == Path("") or base_path in path.parents or base_path == path.parent:
            # Relative path from base_path
            try:
                rel_path = path.relative_to(base_path)
            except ValueError:
                continue
            parts = rel_path.parts
            if len(parts) == 1:  # Direct child of base_path
                children[parts[0]] = blob_oid

    # Separate files and directories
    files = {name: oid for name, oid in children.items() if Path(name).is_file()}
    dirs = {name: oid for name, oid in children.items() if Path(name).is_dir() or "/" in name}

    # Add files
    for name, oid in files.items():
        entries.append(("100644", name, oid))

    # Add subdirectories recursively
    for dir_name in set(path.parts[0] for path in (Path(k) for k in dirs.keys())):
        # Collect all entries under this subdirectory
        sub_index = {k: v for k, v in index.items() if Path(k).parts[0] == dir_name}
        sub_tree = _build_tree(repo_root, sub_index, base_path=Path(base_path) / dir_name)
        sub_oid = sub_tree.write(repo_root)  # write tree to objects
        entries.append(("040000", dir_name, sub_oid))

    # Sort entries by name (like Git does)
    entries.sort(key=lambda x: x[1])
    return Tree(entries)

def _get_head_commit(repo_root: Path) -> Optional[str]:
    """
    Return the current commit OID that HEAD points to, or None if no commits yet.
    """
    head_path = repo_root / REPO_DIR / "HEAD"
    if not head_path.exists():
        return None

    head_contents = head_path.read_text().strip()
    if head_contents.startswith("ref: "):
        # HEAD points to a branch
        ref_relpath = head_contents[5:]
        ref_path = repo_root / REPO_DIR / ref_relpath
        if ref_path.exists():
            return ref_path.read_text().strip() or None
        return None  # branch file missing (no commits yet)
    else:
        # Detached HEAD points directly to a commit
        return head_contents or None


def _update_head(repo_root: Path, commit_oid: str):
    """
    Update HEAD after creating a new commit.
    - If HEAD points to a branch (symbolic ref), update that branch ref.
    - If HEAD is detached (points directly to a commit), update HEAD itself.
    """
    head_path = repo_root / REPO_DIR / "HEAD"
    head_contents = head_path.read_text().strip()

    if head_contents.startswith("ref: "):
        # Symbolic ref: update the branch
        ref_path = repo_root / REPO_DIR / head_contents[5:]
        ref_path.write_text(commit_oid + "\n")
    else:
        # Detached HEAD: update HEAD directly
        head_path.write_text(commit_oid + "\n")

