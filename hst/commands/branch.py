import sys
from pathlib import Path
from typing import List
from hst.repo import get_repo_paths
from hst.repo.head import get_current_commit_oid, get_current_branch
from hst.repo.index import check_for_staged_changes


def run(argv: List[str]):
    """
    Run the branch command
    """
    repo_root, hst_dir = get_repo_paths()

    if not argv:
        _list_branches(hst_dir)
    elif argv[0] == "-D":
        if len(argv) < 2:
            print("Usage: hst branch -D <branch>")
            sys.exit(1)
        _delete_branch(hst_dir, argv[1], force=True)
    elif argv[0] == "-d":
        if len(argv) < 2:
            print("Usage: hst branch -d <branch>")
            sys.exit(1)
        _delete_branch(hst_dir, argv[1], force=False)
    else:
        name = argv[0]
        _create_branch(hst_dir, name)


def _list_branches(hst_dir: Path):
    heads_dir = hst_dir / "refs" / "heads"
    branches = [p.name for p in heads_dir.iterdir() if p.is_file()]

    # figure out current branch
    current = get_current_branch(hst_dir)

    for b in branches:
        prefix = "*" if b == current else " "
        print(f"{prefix} {b}")


def _create_branch(hst_dir: Path, name: str):
    commit_hash = get_current_commit_oid(hst_dir)
    if not commit_hash:
        print("No commits yet")
        sys.exit(1)

    branch_path = hst_dir / "refs" / "heads" / name
    if branch_path.exists():
        print(f"Branch {name} already exists")
        sys.exit(1)

    branch_path.write_text(commit_hash)
    print(f"Created branch {name} at {commit_hash[:7]}")


def _delete_branch(hst_dir: Path, name: str, force: bool = False):
    current = get_current_branch(hst_dir)

    if name == current:
        print(f"Cannot delete branch '{name}' while on it")
        sys.exit(1)

    branch_path = hst_dir / "refs" / "heads" / name
    if not branch_path.exists():
        print(f"Branch '{name}' not found")
        sys.exit(1)

    # Get commit hash before deletion for display purposes
    branch_commit_hash = branch_path.read_text().strip()

    # Safety check for -d (but not -D)
    if not force:
        # Check for staged changes in current branch
        if check_for_staged_changes(hst_dir):
            print("error: There are uncommitted changes.")
            print("Please commit your changes before deleting branches.")
            sys.exit(1)

        # Check if branch is fully merged (simplified check)
        if not _is_branch_merged(hst_dir, name):
            print(f"error: The branch '{name}' is not fully merged.")
            print(f"If you are sure you want to delete it, run 'hst branch -D {name}'.")
            sys.exit(1)

    branch_path.unlink()

    if force:
        print(f"Deleted branch {name} (was {branch_commit_hash[:7]})")
    else:
        print(f"Deleted branch {name}")


def _is_branch_merged(hst_dir: Path, branch_name: str) -> bool:
    """
    Simplified check to see if a branch is merged.
    Returns True if the branch points to the same commit as HEAD or
    if the branch commit is an ancestor of HEAD.

    Note: This is a simplified implementation. A full implementation would
    need to walk the commit history to check ancestry properly.
    """
    # Get current commit
    current_commit = get_current_commit_oid(hst_dir)
    if not current_commit:
        return False

    # Get branch commit
    branch_path = hst_dir / "refs" / "heads" / branch_name
    if not branch_path.exists():
        return False

    branch_commit = branch_path.read_text().strip()

    # If they point to the same commit, it's merged
    return current_commit == branch_commit
