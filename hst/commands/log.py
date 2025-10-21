import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set
from hst.repo import get_repo_paths
from hst.repo.head import get_current_commit_oid, get_current_branch
from hst.repo.objects import read_object
from hst.repo.refs import resolve_commit_ref
from hst.components import Commit
from hst.colors import CYAN, GREEN, YELLOW, RED, RESET


def run(argv: List[str]):
    """
    Run the log command.

    Usage:
    hst log [--oneline] [-<n>] [<commit>...] - Show commit history
    """
    # Parse arguments - separate flags, limit, and commit references
    oneline = "--oneline" in argv
    max_commits = None
    commit_refs = []

    for arg in argv:
        if arg == "--oneline":
            continue
        elif arg.startswith("-") and arg[1:].isdigit():
            # Numeric limit like -5, -10, etc.
            max_commits = int(arg[1:])
        elif not arg.startswith("-"):
            # Commit reference
            commit_refs.append(arg)
        else:
            print(f"Unknown option: {arg}")
            sys.exit(1)

    repo_root, hst_dir = get_repo_paths()

    # Determine starting commits
    starting_commits = []

    if not commit_refs:
        # No commits specified - start from HEAD
        current_commit_oid = get_current_commit_oid(hst_dir)
        if not current_commit_oid:
            print("No commits found")
            return
        starting_commits.append(current_commit_oid)
    else:
        # Resolve each commit reference
        for commit_ref in commit_refs:
            commit_oid = resolve_commit_ref(hst_dir, commit_ref)
            if not commit_oid:
                print(f"fatal: bad revision '{commit_ref}'")
                sys.exit(1)
            starting_commits.append(commit_oid)

    # Walk the commit history from all starting points
    if len(starting_commits) == 1:
        # Single starting commit - use the original simple history walk
        commits = _get_commit_history(hst_dir, starting_commits[0], max_commits)
    else:
        # Multiple starting commits - merge their histories
        commits = _get_commit_history_from_multiple(
            hst_dir, starting_commits, max_commits
        )

    if not commits:
        print("No commits found")
        return

    # Get branch information
    commit_to_branches = _get_commit_to_branches_mapping(hst_dir)
    current_branch = get_current_branch(hst_dir)

    # Display commits
    if oneline:
        _display_oneline(commits, commit_to_branches, current_branch)
    else:
        _display_full(commits, commit_to_branches, current_branch)


def _get_commit_history(
    hst_dir: Path, start_commit_oid: str, max_commits: int = None
) -> List[tuple]:
    """
    Walk the commit history starting from the given commit.

    Args:
        hst_dir: Path to .hst directory
        start_commit_oid: Starting commit hash
        max_commits: Maximum number of commits to return (None for unlimited)

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

        # Check if we've reached the limit
        if max_commits is not None and len(commits) >= max_commits:
            break

        # Move to parent commit (simplified - just take first parent)
        if commit_obj.parents and commit_obj.parents[0]:
            current_oid = commit_obj.parents[0]
        else:
            break

    return commits


def _get_commit_to_branches_mapping(hst_dir: Path) -> Dict[str, Set[str]]:
    """Create a mapping from commit OID to set of branch names that point to it."""
    commit_to_branches = {}

    # Scan local branches
    refs_heads = hst_dir / "refs" / "heads"
    if refs_heads.exists():
        for branch_file in refs_heads.iterdir():
            if branch_file.is_file():
                branch_name = branch_file.name
                try:
                    commit_oid = branch_file.read_text().strip()
                    if commit_oid not in commit_to_branches:
                        commit_to_branches[commit_oid] = set()
                    commit_to_branches[commit_oid].add(branch_name)
                except Exception:
                    # Skip invalid branch files
                    continue

    # Scan remote tracking branches
    refs_remotes = hst_dir / "refs" / "remotes"
    if refs_remotes.exists():
        for remote_dir in refs_remotes.iterdir():
            if remote_dir.is_dir():
                remote_name = remote_dir.name
                for branch_file in remote_dir.iterdir():
                    if branch_file.is_file():
                        branch_name = f"{remote_name}/{branch_file.name}"
                        try:
                            commit_oid = branch_file.read_text().strip()
                            if commit_oid not in commit_to_branches:
                                commit_to_branches[commit_oid] = set()
                            commit_to_branches[commit_oid].add(branch_name)
                        except Exception:
                            # Skip invalid branch files
                            continue

    return commit_to_branches


def _format_branch_info(
    commit_oid: str, commit_to_branches: Dict[str, Set[str]], current_branch: str
) -> str:
    """Format branch information for a commit."""
    if commit_oid not in commit_to_branches:
        return ""

    branches = list(commit_to_branches[commit_oid])
    if not branches:
        return ""

    branch_parts = []

    # Handle current branch with HEAD -> branch_name format
    if current_branch in branches:
        branches.remove(current_branch)
        head_info = f"{CYAN}HEAD -> {GREEN}{current_branch}{RESET}"
        branch_parts.append(head_info)

    # Separate local and remote branches
    local_branches = []
    remote_branches = []

    for branch in branches:
        if "/" in branch:  # Remote branch (format: remote/branch)
            remote_branches.append(branch)
        else:  # Local branch
            local_branches.append(branch)

    # Add local branches (green)
    for branch in sorted(local_branches):
        branch_parts.append(f"{GREEN}{branch}{RESET}")

    # Add remote branches (red)
    for branch in sorted(remote_branches):
        branch_parts.append(f"{RED}{branch}{RESET}")

    return f"{YELLOW}({RESET}{f'{YELLOW}, {RESET}'.join(branch_parts)}{YELLOW}){RESET}"


def _display_full(
    commits: List[tuple], commit_to_branches: Dict[str, Set[str]], current_branch: str
):
    """Display commits in full format (like git log)."""
    for i, (commit_oid, commit_obj) in enumerate(commits):
        if i > 0:
            print()  # Blank line between commits

        branch_info = _format_branch_info(
            commit_oid, commit_to_branches, current_branch
        )
        print(f"{YELLOW}commit {commit_oid} {branch_info}{RESET}")
        print(f"Author: {commit_obj.author}")
        print(f"Date:   {_format_timestamp(commit_obj.author_timestamp)}")
        print()

        # Indent commit message
        for line in commit_obj.message.split("\n"):
            print(f"    {line}")


def _display_oneline(
    commits: List[tuple], commit_to_branches: Dict[str, Set[str]], current_branch: str
):
    """Display commits in one-line format (like git log --oneline)."""
    for commit_oid, commit_obj in commits:
        # Get first line of commit message
        first_line = commit_obj.message.split("\n")[0]

        # Display branch information
        branch_info = _format_branch_info(
            commit_oid, commit_to_branches, current_branch
        )
        colored_commit = f"{YELLOW}{commit_oid[:7]}{RESET}"
        if branch_info:
            print(f"{colored_commit} {branch_info} {first_line}")
        else:
            print(f"{colored_commit} {first_line}")


def _format_timestamp(timestamp: int) -> str:
    """Format a Unix timestamp for display."""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%a %b %d %H:%M:%S %Y")


def _get_commit_history_from_multiple(
    hst_dir: Path, start_commit_oids: List[str], max_commits: int = None
) -> List[tuple]:
    """
    Walk the commit history starting from multiple commits, merging the results.

    For multiple commits, this shows all commits reachable from any of the starting commits.

    Args:
        hst_dir: Path to .hst directory
        start_commit_oids: List of starting commit hashes
        max_commits: Maximum number of commits to return (None for unlimited)

    Returns:
        List of (commit_oid, commit_obj) tuples in reverse chronological order
    """
    all_commits = {}  # commit_oid -> (commit_oid, commit_obj)

    # Gather commits from all starting points
    for start_oid in start_commit_oids:
        commits = _get_commit_history(hst_dir, start_oid, max_commits)
        for commit_oid, commit_obj in commits:
            if commit_oid not in all_commits:
                all_commits[commit_oid] = (commit_oid, commit_obj)

    # Sort by timestamp (most recent first)
    sorted_commits = sorted(
        all_commits.values(), key=lambda x: x[1].author_timestamp, reverse=True
    )

    # Apply limit after sorting if specified
    if max_commits is not None:
        sorted_commits = sorted_commits[:max_commits]

    return sorted_commits
