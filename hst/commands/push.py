import sys
from pathlib import Path
from typing import List, Optional
from hst.repo import get_repo_paths, validate_repository, copy_objects_to_repository
from hst.repo.config import get_remote_url
from hst.repo.head import get_current_branch, get_current_commit_oid
from hst.repo.refs import resolve_commit_ref


def run(argv: List[str]):
    """
    Run the push command.
    
    Usage:
    hst push [<remote>] [<branch>]
    hst push <remote> <local_branch>:<remote_branch>
    """
    repo_root, hst_dir = get_repo_paths()
    
    if not argv:
        # Default: push current branch to origin
        remote_name = "origin"
        local_branch = get_current_branch(hst_dir)
        if not local_branch:
            print("fatal: You are not currently on a branch.")
            sys.exit(1)
        local_ref = local_branch
        remote_ref = local_branch
    elif len(argv) == 1:
        # One argument - could be remote name or refspec
        if ":" in argv[0]:
            # It's a refspec like "main:main"
            remote_name = "origin"
            local_ref, remote_ref = argv[0].split(":", 1)
        else:
            # It's a remote name
            remote_name = argv[0]
            local_branch = get_current_branch(hst_dir)
            if not local_branch:
                print("fatal: You are not currently on a branch.")
                sys.exit(1)
            local_ref = local_branch
            remote_ref = local_branch
    elif len(argv) == 2:
        # Two arguments: remote and branch/refspec
        remote_name = argv[0]
        if ":" in argv[1]:
            # It's a refspec
            local_ref, remote_ref = argv[1].split(":", 1)
        else:
            # It's just a branch name
            local_ref = argv[1]
            remote_ref = argv[1]
    else:
        print("Usage: hst push [<remote>] [<branch>] | hst push <remote> <refspec>")
        sys.exit(1)
    
    # Get remote URL
    remote_url = get_remote_url(hst_dir, remote_name)
    if not remote_url:
        print(f"fatal: '{remote_name}' does not appear to be a hst repository")
        sys.exit(1)
    
    # Resolve local ref to commit
    local_commit = resolve_commit_ref(hst_dir, local_ref)
    if not local_commit:
        print(f"error: src refspec {local_ref} does not match any.")
        sys.exit(1)
    
    # Push to remote
    success = _push_to_remote(hst_dir, repo_root, remote_name, remote_url, 
                            local_ref, remote_ref, local_commit)
    
    if success:
        print(f"To {remote_url}")
        print(f"   {local_commit[:7]}..{local_commit[:7]}  {local_ref} -> {remote_ref}")
    else:
        sys.exit(1)


def _push_to_remote(hst_dir: Path, repo_root: Path, remote_name: str, 
                   remote_url: str, local_ref: str, remote_ref: str, 
                   local_commit: str) -> bool:
    """
    Push commits and update remote branch.
    
    Args:
        hst_dir: Local .hst directory
        repo_root: Local repository root
        remote_name: Name of the remote (e.g., 'origin')
        remote_url: URL/path of the remote repository
        local_ref: Local branch/ref name
        remote_ref: Remote branch/ref name
        local_commit: Commit hash to push
        
    Returns:
        True if successful, False otherwise
    """
    remote_path = Path(remote_url)
    
    # Validate remote repository
    remote_hst_dir = validate_repository(remote_path)
    if not remote_hst_dir:
        print(f"fatal: Could not read from remote repository '{remote_url}'")
        return False
    
    # Copy objects that don't exist in remote
    if not copy_objects_to_repository(hst_dir, remote_hst_dir, local_commit):
        return False
    
    # Update remote branch reference
    remote_branch_path = remote_hst_dir / "refs" / "heads" / remote_ref
    remote_branch_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        remote_branch_path.write_text(local_commit + "\n")
    except OSError as e:
        print(f"error: failed to update remote ref: {e}")
        return False
    
    # Update local remote tracking branch
    local_remote_branch_path = hst_dir / "refs" / "remotes" / remote_name / remote_ref
    local_remote_branch_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        local_remote_branch_path.write_text(local_commit + "\n")
    except OSError as e:
        print(f"warning: failed to update remote tracking branch: {e}")
        # Don't fail the push for this
    
    return True



