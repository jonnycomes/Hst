import sys
from pathlib import Path
from typing import List
from hst.repo import get_repo_paths
from hst.repo.config import get_remote_url
from hst.repo.head import get_current_branch, get_current_commit_oid
from hst.repo.refs import is_ancestor
from hst.repo.worktree import checkout_from_commit
from hst.commands import fetch


def run(argv: List[str]):
    """
    Run the pull command.

    Usage:
    hst pull [<remote>] [<branch>]
    """
    repo_root, hst_dir = get_repo_paths()

    # Get current branch
    current_branch = get_current_branch(hst_dir)
    if not current_branch:
        print("fatal: You are not currently on a branch.")
        sys.exit(1)

    # Parse arguments
    if not argv:
        remote_name = "origin"
        remote_branch = current_branch
    elif len(argv) == 1:
        remote_name = argv[0]
        remote_branch = current_branch
    elif len(argv) == 2:
        remote_name = argv[0]
        remote_branch = argv[1]
    else:
        print("Usage: hst pull [<remote>] [<branch>]")
        sys.exit(1)

    # Check if remote exists
    remote_url = get_remote_url(hst_dir, remote_name)
    if not remote_url:
        print(f"fatal: '{remote_name}' does not appear to be a hst repository")
        sys.exit(1)

    # First, fetch from remote
    print(f"Fetching from {remote_name}...")
    fetch_args = [remote_name, f"{remote_branch}:remotes/{remote_name}/{remote_branch}"]

    try:
        fetch.run(fetch_args)
    except SystemExit:
        print(f"error: failed to fetch from {remote_name}")
        sys.exit(1)

    # Now try to merge the remote tracking branch
    current_commit = get_current_commit_oid(hst_dir)
    remote_tracking_ref = hst_dir / "refs" / "remotes" / remote_name / remote_branch

    if not remote_tracking_ref.exists():
        print(f"error: remote tracking branch {remote_name}/{remote_branch} not found")
        sys.exit(1)

    remote_commit = remote_tracking_ref.read_text().strip()

    if current_commit == remote_commit:
        print("Already up to date.")
        return

    # Check if we can fast-forward
    if not current_commit:
        # No current commit (empty repository)
        _fast_forward_to(hst_dir, repo_root, current_branch, remote_commit)
        print(f"Fast-forward to {remote_commit[:7]}")
    elif is_ancestor(hst_dir, current_commit, remote_commit):
        # Can fast-forward
        _fast_forward_to(hst_dir, repo_root, current_branch, remote_commit)
        print(f"Fast-forward {current_commit[:7]}..{remote_commit[:7]}")
    else:
        # Need to merge - for now, just inform the user
        print(
            f"Automatic merge failed. The remote branch {remote_name}/{remote_branch} has diverged."
        )
        print(
            f"You may need to merge manually or use 'hst merge {remote_name}/{remote_branch}'"
        )
        print(f"Remote commit: {remote_commit}")
        print(f"Local commit:  {current_commit}")


def _fast_forward_to(
    hst_dir: Path, repo_root: Path, branch_name: str, target_commit: str
):
    """Fast-forward the current branch to the target commit."""
    # Update branch reference
    branch_ref = hst_dir / "refs" / "heads" / branch_name
    try:
        branch_ref.write_text(target_commit + "\n")
    except OSError as e:
        print(f"error: failed to update branch {branch_name}: {e}")
        sys.exit(1)

    # Update HEAD
    head_file = hst_dir / "HEAD"
    try:
        head_file.write_text(f"ref: refs/heads/{branch_name}\n")
    except OSError as e:
        print(f"error: failed to update HEAD: {e}")
        sys.exit(1)

    # Update working tree
    try:
        checkout_from_commit(hst_dir, repo_root, target_commit)
    except Exception as e:
        print(f"warning: failed to update working tree: {e}")
        # Don't exit - the refs are updated, working tree can be fixed manually
