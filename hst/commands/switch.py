import sys
from pathlib import Path
from typing import List
from hst.repo import get_repo_paths
from hst.repo.head import get_current_commit_oid, get_current_branch
from hst.repo.worktree import checkout_commit


def run(argv: List[str]):
    """
    Run the switch command.
    """
    repo_root, hst_dir = get_repo_paths()

    if not argv:
        print("Usage: hst switch [-c] <branch>")
        sys.exit(1)

    if argv[0] == "-c":
        if len(argv) < 2:
            print("Usage: hst switch -c <branch>")
            sys.exit(1)
        _compare_current_to_switch(hst_dir, argv[1])
        _create_and_switch(hst_dir, argv[1])
    else:
        _compare_current_to_switch(hst_dir, argv[0])
        _switch_branch(hst_dir, argv[0])


def _switch_branch(hst_dir: Path, name: str):
    repo_root = hst_dir.parent  # Get repo root from hst_dir
    branch_path = hst_dir / "refs" / "heads" / name
    if not branch_path.exists():
        print(f"Branch '{name}' does not exist")
        sys.exit(1)

    # Get the commit hash for the target branch
    target_commit_oid = branch_path.read_text().strip()

    # Update working directory and index to match target commit
    checkout_commit(hst_dir, repo_root, target_commit_oid)

    # Update HEAD
    (hst_dir / "HEAD").write_text(f"ref: refs/heads/{name}")
    print(f"Switched to branch '{name}'")


def _create_and_switch(hst_dir: Path, name: str):
    repo_root = hst_dir.parent  # Get repo root from hst_dir
    branch_path = hst_dir / "refs" / "heads" / name
    if branch_path.exists():
        print(f"Branch '{name}' already exists")
        sys.exit(1)

    # Get current commit hash
    commit_hash = get_current_commit_oid(hst_dir)
    if not commit_hash:
        print("No commits yet")
        sys.exit(1)

    # Create new branch
    branch_path.write_text(commit_hash)

    # Update working directory and index to match the commit (should be same as current)
    checkout_commit(hst_dir, repo_root, commit_hash)

    # Update HEAD
    (hst_dir / "HEAD").write_text(f"ref: refs/heads/{name}")
    print(f"Created and switched to branch '{name}' at {commit_hash[:7]}")


def _compare_current_to_switch(hst_dir: Path, name: str):
    current = get_current_branch(hst_dir)

    if name == current:
        print(f"Already on '{name}'")
        sys.exit(1)
