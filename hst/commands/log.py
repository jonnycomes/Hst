import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set
from hst.repo import get_repo_paths
from hst.repo.head import get_current_commit_oid, get_current_branch
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

    # Get branch information
    commit_to_branches = _get_commit_to_branches_mapping(hst_dir)
    current_branch = get_current_branch(hst_dir)

    # Display commits
    if oneline:
        _display_oneline(commits, commit_to_branches, current_branch)
    else:
        _display_full(commits, commit_to_branches, current_branch)


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


def _get_commit_to_branches_mapping(hst_dir: Path) -> Dict[str, Set[str]]:
    """Create a mapping from commit OID to set of branch names that point to it."""
    commit_to_branches = {}
    refs_heads = hst_dir / "refs" / "heads"

    if not refs_heads.exists():
        return commit_to_branches

    # Scan all branch files
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

    return commit_to_branches


def _format_branch_info(commit_oid: str, commit_to_branches: Dict[str, Set[str]], current_branch: str) -> str:
    """Format branch information for a commit."""
    if commit_oid not in commit_to_branches:
        return ""

    branches = list(commit_to_branches[commit_oid])
    if not branches:
        return ""

    # Check if colors are supported
    use_colors = sys.stdout.isatty()
    
    # Color codes
    if use_colors:
        CYAN = "\033[36m"
        YELLOW = "\033[33m" 
        GREEN = "\033[32m"
        RESET = "\033[0m"
    else:
        CYAN = YELLOW = GREEN = RESET = ""
    
    branch_parts = []
    
    # Handle current branch with HEAD -> branch_name format
    if current_branch in branches:
        branches.remove(current_branch)
        head_info = f"{CYAN}HEAD -> {GREEN}{current_branch}{RESET}"
        branch_parts.append(head_info)
    
    # Add other branches
    for branch in sorted(branches):
        branch_parts.append(f"{YELLOW}{branch}{RESET}")
    
    return f" ({', '.join(branch_parts)})"


def _display_full(commits: List[tuple], commit_to_branches: Dict[str, Set[str]], current_branch: str):
    """Display commits in full format (like git log)."""
    for i, (commit_oid, commit_obj) in enumerate(commits):
        if i > 0:
            print()  # Blank line between commits

        branch_info = _format_branch_info(commit_oid, commit_to_branches, current_branch)
        print(f"commit {commit_oid}{branch_info}")
        print(f"Author: {commit_obj.author}")
        print(f"Date:   {_format_timestamp(commit_obj.author_timestamp)}")
        print()

        # Indent commit message
        for line in commit_obj.message.split("\n"):
            print(f"    {line}")


def _display_oneline(commits: List[tuple], commit_to_branches: Dict[str, Set[str]], current_branch: str):
    """Display commits in one-line format (like git log --oneline)."""
    for commit_oid, commit_obj in commits:
        # Get first line of commit message
        first_line = commit_obj.message.split("\n")[0]

        # Display branch information
        branch_info = _format_branch_info(commit_oid, commit_to_branches, current_branch)
        if branch_info:
            print(f"{commit_oid[:7]} {first_line} {branch_info}")
        else:
            print(f"{commit_oid[:7]} {first_line}")


def _format_timestamp(timestamp: int) -> str:
    """Format a Unix timestamp for display."""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%a %b %d %H:%M:%S %Y")
