import sys
from pathlib import Path
from typing import List
from hst.repo import get_repo_paths
from hst.repo.head import get_current_commit_oid, get_current_branch
from hst.repo.worktree import check_for_staged_changes
from hst.repo.refs import resolve_commit_ref, is_ancestor
from hst.colors import GREEN, RESET


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
        commit_ref = argv[1] if len(argv) > 1 else None
        _create_branch(hst_dir, name, commit_ref)


def _list_branches(hst_dir: Path):
    heads_dir = hst_dir / "refs" / "heads"
    branches = sorted([p.name for p in heads_dir.iterdir() if p.is_file()])

    # figure out current branch
    current = get_current_branch(hst_dir)

    for b in branches:
        prefix = "*" if b == current else " "
        clr = GREEN if b == current else ""
        print(f"{prefix} {clr}{b}{RESET}")


def _create_branch(hst_dir: Path, name: str, commit_ref: str = None):
    # Resolve commit reference
    if commit_ref:
        commit_hash = resolve_commit_ref(hst_dir, commit_ref)
        if not commit_hash:
            print(f"fatal: not a valid object name: '{commit_ref}'")
            sys.exit(1)
    else:
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
    Check if a branch is fully merged into the current branch.
    Returns True if the branch commit is reachable from HEAD (i.e., is an ancestor).
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
    if current_commit == branch_commit:
        return True

    # Walk back through current branch history to see if branch_commit is an ancestor
    return is_ancestor(hst_dir, branch_commit, current_commit)
