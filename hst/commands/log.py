from datetime import datetime
from pathlib import Path
from typing import List
from hst.repo import get_repo_paths
from hst.repo.head import get_current_commit_oid
from hst.repo.objects import read_object
from hst.hst_objects import Commit


def run(argv: List[str]):
    """
    Run the log command.
    """
    # Parse arguments
    oneline = "--oneline" in argv

    repo_root, hst_dir = get_repo_paths()

    # Get starting commit (HEAD)
    current_commit_oid = get_current_commit_oid(hst_dir)
    if not current_commit_oid:
        print("No commits found")
        return

    # Walk the commit history
    commits = _get_commit_history(hst_dir, current_commit_oid)

    if not commits:
        print("No commits found")
        return

    # Display commits
    if oneline:
        _display_oneline(commits)
    else:
        _display_full(commits)


def _get_commit_history(hst_dir: Path, start_commit_oid: str) -> List[tuple]:
    """
    Walk the commit history starting from the given commit.

    Returns:
        List of (commit_oid, commit_obj) tuples in reverse chronological order
    """
    commits = []
    current_oid = start_commit_oid
    visited = set()

    while current_oid and current_oid not in visited:
        visited.add(current_oid)

        # Read the commit object
        commit_obj = read_object(hst_dir, current_oid, Commit, store=False)
        if not commit_obj:
            break

        commits.append((current_oid, commit_obj))

        # Move to parent commit (simplified - just take first parent)
        if commit_obj.parents and commit_obj.parents[0]:
            current_oid = commit_obj.parents[0]
        else:
            break

    return commits


def _display_full(commits: List[tuple]):
    """Display commits in full format (like git log)."""
    for i, (commit_oid, commit_obj) in enumerate(commits):
        if i > 0:
            print()  # Blank line between commits

        print(f"commit {commit_oid}")
        print(f"Author: {commit_obj.author}")
        print(f"Date:   {_format_timestamp(commit_obj.author_timestamp)}")
        print()
        # Indent commit message
        for line in commit_obj.message.split("\n"):
            print(f"    {line}")


def _display_oneline(commits: List[tuple]):
    """Display commits in one-line format (like git log --oneline)."""
    for commit_oid, commit_obj in commits:
        # Get first line of commit message
        first_line = commit_obj.message.split("\n")[0]
        print(f"{commit_oid[:7]} {first_line}")


def _format_timestamp(timestamp: int) -> str:
    """Format a Unix timestamp for display."""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%a %b %d %H:%M:%S %Y")
