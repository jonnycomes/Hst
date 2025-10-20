import sys
from pathlib import Path
from typing import List
from hst.repo import get_repo_paths, validate_repository, copy_objects_to_repository
from hst.repo.config import get_remote_url


def run(argv: List[str]):
    """
    Run the fetch command.

    Usage:
    hst fetch [<remote>] [<refspec>...]
    hst fetch [<remote>]
    """
    repo_root, hst_dir = get_repo_paths()

    # Parse arguments
    if not argv:
        # Default: fetch from origin
        remote_name = "origin"
        refspecs = []
    else:
        remote_name = argv[0]
        refspecs = argv[1:] if len(argv) > 1 else []

    # Get remote URL
    remote_url = get_remote_url(hst_dir, remote_name)
    if not remote_url:
        print(f"fatal: '{remote_name}' does not appear to be a hst repository")
        sys.exit(1)

    # Validate remote repository
    remote_path = Path(remote_url)
    remote_hst_dir = validate_repository(remote_path)
    if not remote_hst_dir:
        print(f"fatal: Could not read from remote repository '{remote_url}'")
        sys.exit(1)

    # Get all remote branches if no refspecs specified
    if not refspecs:
        refspecs = _get_default_refspecs(remote_hst_dir, remote_name)

    if not refspecs:
        print(f"No refs found in remote repository '{remote_name}'")
        return

    # Fetch each refspec
    updated_refs = []
    for refspec in refspecs:
        if _fetch_refspec(hst_dir, remote_hst_dir, remote_name, refspec):
            updated_refs.append(refspec)

    # Display results
    if updated_refs:
        print(f"From {remote_url}")
        for refspec in updated_refs:
            local_ref, remote_ref = _parse_refspec(refspec, remote_name)
            # Get commit hash for display
            remote_branch_file = remote_hst_dir / "refs" / "heads" / remote_ref
            if remote_branch_file.exists():
                try:
                    remote_commit = remote_branch_file.read_text().strip()
                    print(
                        f"   {remote_commit[:7]}..{remote_commit[:7]}  {remote_ref} -> {local_ref}"
                    )
                except OSError:
                    print(f"   ???..???  {remote_ref} -> {local_ref}")
    else:
        print("Already up to date.")


def _get_default_refspecs(remote_hst_dir: Path, remote_name: str) -> List[str]:
    """Get default refspecs by scanning remote branches."""
    refspecs = []
    remote_heads = remote_hst_dir / "refs" / "heads"

    if not remote_heads.exists():
        return refspecs

    for branch_file in remote_heads.iterdir():
        if branch_file.is_file():
            branch_name = branch_file.name
            # Create refspec: remote_branch:remotes/remote_name/remote_branch
            refspec = f"{branch_name}:remotes/{remote_name}/{branch_name}"
            refspecs.append(refspec)

    return refspecs


def _parse_refspec(refspec: str, remote_name: str) -> tuple[str, str]:
    """Parse a refspec into (local_ref, remote_ref) parts."""
    if ":" in refspec:
        remote_ref, local_ref = refspec.split(":", 1)
    else:
        # Simple branch name - map to remote tracking branch
        remote_ref = refspec
        local_ref = f"remotes/{remote_name}/{refspec}"

    return local_ref, remote_ref


def _fetch_refspec(
    hst_dir: Path, remote_hst_dir: Path, remote_name: str, refspec: str
) -> bool:
    """Fetch a single refspec from remote to local."""
    local_ref, remote_ref = _parse_refspec(refspec, remote_name)

    # Resolve remote commit - look directly in heads/
    remote_branch_file = remote_hst_dir / "refs" / "heads" / remote_ref
    if not remote_branch_file.exists():
        print(f"error: couldn't find remote ref {remote_ref}")
        return False

    try:
        remote_commit = remote_branch_file.read_text().strip()
    except OSError:
        print(f"error: couldn't read remote ref {remote_ref}")
        return False

    # Check if we already have this commit
    local_tracking_ref = hst_dir / "refs" / local_ref
    if local_tracking_ref.exists():
        local_commit = local_tracking_ref.read_text().strip()
        if local_commit == remote_commit:
            # Already up to date
            return False

    # Copy objects from remote
    if not copy_objects_to_repository(remote_hst_dir, hst_dir, remote_commit):
        print(f"error: failed to copy objects for {refspec}")
        return False

    # Update local tracking branch
    local_tracking_ref.parent.mkdir(parents=True, exist_ok=True)
    try:
        local_tracking_ref.write_text(remote_commit + "\n")
        return True
    except OSError as e:
        print(f"error: failed to update tracking ref {local_ref}: {e}")
        return False
