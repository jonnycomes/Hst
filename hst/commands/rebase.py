import sys
from pathlib import Path
from typing import List, Optional
from hst.repo import get_repo_paths
from hst.repo.head import get_current_branch
from hst.repo.refs import resolve_commit_ref, is_ancestor
from hst.repo.objects import read_object
from hst.repo.worktree import checkout_from_commit
from hst.components import Commit


def run(argv: List[str]):
    """
    Run the rebase command.

    Usage:
    hst rebase <upstream>
    hst rebase <upstream> <branch>
    """
    if not argv:
        print("Usage: hst rebase <upstream> [<branch>]")
        sys.exit(1)

    repo_root, hst_dir = get_repo_paths()

    # Parse arguments
    upstream = argv[0]
    target_branch = argv[1] if len(argv) > 1 else None

    # Get current branch if no target specified
    if not target_branch:
        current_branch = get_current_branch(hst_dir)
        if not current_branch:
            print("fatal: You are not currently on a branch.")
            sys.exit(1)
        target_branch = current_branch
    else:
        # Switch to target branch if specified
        target_branch_ref = hst_dir / "refs" / "heads" / target_branch
        if not target_branch_ref.exists():
            print(f"fatal: branch '{target_branch}' does not exist")
            sys.exit(1)

        # Update HEAD to point to target branch
        head_file = hst_dir / "HEAD"
        head_file.write_text(f"ref: refs/heads/{target_branch}\n")

    # Resolve commits
    upstream_commit = resolve_commit_ref(hst_dir, upstream)
    if not upstream_commit:
        print(f"fatal: invalid upstream '{upstream}'")
        sys.exit(1)

    target_commit = resolve_commit_ref(hst_dir, target_branch)
    if not target_commit:
        print(f"fatal: invalid branch '{target_branch}'")
        sys.exit(1)

    # Check if rebase is needed
    if upstream_commit == target_commit:
        print("Current branch is up to date.")
        return

    # Check if upstream is ancestor of target (already up to date)
    if is_ancestor(hst_dir, upstream_commit, target_commit):
        print("Current branch is up to date.")
        return

    # Check if target is ancestor of upstream (fast-forward)
    if is_ancestor(hst_dir, target_commit, upstream_commit):
        print(f"Fast-forwarding {target_branch} to {upstream}...")
        _fast_forward_branch(hst_dir, repo_root, target_branch, upstream_commit)
        print(f"Successfully rebased and updated refs/heads/{target_branch}.")
        return

    # Find merge base
    merge_base = _find_merge_base(hst_dir, upstream_commit, target_commit)
    if not merge_base:
        print("fatal: no merge base found")
        sys.exit(1)

    # Get commits to rebase (from merge_base to target_commit)
    commits_to_rebase = _get_commits_to_rebase(hst_dir, merge_base, target_commit)
    if not commits_to_rebase:
        print("Current branch is up to date.")
        return

    print(f"Rebasing {len(commits_to_rebase)} commit(s) onto {upstream}...")

    # Perform the rebase
    new_head = _perform_rebase(hst_dir, repo_root, upstream_commit, commits_to_rebase)
    if not new_head:
        print("Rebase failed.")
        sys.exit(1)

    # Update branch ref
    target_branch_ref = hst_dir / "refs" / "heads" / target_branch
    target_branch_ref.write_text(new_head + "\n")

    # Update working tree
    checkout_from_commit(hst_dir, repo_root, new_head)

    print(f"Successfully rebased and updated refs/heads/{target_branch}.")


def _fast_forward_branch(
    hst_dir: Path, repo_root: Path, branch_name: str, target_commit: str
):
    """Fast-forward a branch to the target commit."""
    # Update branch reference
    branch_ref = hst_dir / "refs" / "heads" / branch_name
    branch_ref.write_text(target_commit + "\n")

    # Update working tree
    checkout_from_commit(hst_dir, repo_root, target_commit)


def _find_merge_base(hst_dir: Path, commit1: str, commit2: str) -> Optional[str]:
    """Find the merge base (common ancestor) of two commits."""
    # Simple implementation: BFS to find first common ancestor
    visited1 = set()
    visited2 = set()
    queue1 = [commit1]
    queue2 = [commit2]

    while queue1 or queue2:
        # Process queue1
        if queue1:
            current = queue1.pop(0)
            if current in visited2:
                return current
            if current not in visited1:
                visited1.add(current)
                commit_obj = read_object(hst_dir, current, Commit, store=False)
                if commit_obj and commit_obj.parents:
                    for parent in commit_obj.parents:
                        if parent and parent != "None":
                            queue1.append(parent)

        # Process queue2
        if queue2:
            current = queue2.pop(0)
            if current in visited1:
                return current
            if current not in visited2:
                visited2.add(current)
                commit_obj = read_object(hst_dir, current, Commit, store=False)
                if commit_obj and commit_obj.parents:
                    for parent in commit_obj.parents:
                        if parent and parent != "None":
                            queue2.append(parent)

    return None


def _get_commits_to_rebase(
    hst_dir: Path, merge_base: str, target_commit: str
) -> List[str]:
    """Get the list of commits from merge_base (exclusive) to target_commit (inclusive)."""
    commits = []
    current = target_commit

    while current and current != merge_base:
        commits.append(current)
        commit_obj = read_object(hst_dir, current, Commit, store=False)
        if not commit_obj or not commit_obj.parents:
            break

        # Take first parent (main line of development)
        parent = commit_obj.parents[0] if commit_obj.parents[0] != "None" else None
        current = parent

    # Reverse to get chronological order
    return list(reversed(commits))


def _perform_rebase(
    hst_dir: Path, repo_root: Path, new_base: str, commits: List[str]
) -> Optional[str]:
    """Apply commits one by one on top of new_base."""
    current_head = new_base

    for i, commit_hash in enumerate(commits):
        commit_obj = read_object(hst_dir, commit_hash, Commit, store=False)
        if not commit_obj:
            print(f"error: could not read commit {commit_hash}")
            return None

        print(f"Applying {commit_hash[:7]}: {commit_obj.message.split(chr(10))[0]}")

        # Create new commit with same tree and message but new parent
        new_commit = _create_rebased_commit(hst_dir, commit_obj, current_head)
        if not new_commit:
            print(f"error: failed to apply commit {commit_hash}")
            return None

        current_head = new_commit

    return current_head


def _create_rebased_commit(
    hst_dir: Path, original_commit: Commit, new_parent: str
) -> Optional[str]:
    """Create a new commit with the same tree and message but different parent."""
    # Create new commit object
    new_commit = Commit(
        tree=original_commit.tree,
        parents=[new_parent],
        author=original_commit.author,
        author_timestamp=original_commit.author_timestamp,
        committer=original_commit.committer,
        committer_timestamp=original_commit.committer_timestamp,
        message=original_commit.message,
        store=True,
    )

    return new_commit.oid()
