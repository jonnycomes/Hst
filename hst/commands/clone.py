import sys
from pathlib import Path
from typing import List
from hst.repo.repo import clone_repository
from hst.repo.head import get_current_commit_oid
from hst.repo.worktree import checkout_from_commit


def run(argv: List[str]):
    """
    Run the clone command.
    
    Usage: hst clone <source> [<destination>]
    """
    if not argv:
        print("Usage: hst clone <source> [<destination>]")
        sys.exit(1)
    
    source_path = Path(argv[0])
    
    # Determine destination directory
    if len(argv) > 1:
        dest_path = Path(argv[1])
    else:
        # Use the source directory name
        dest_path = Path.cwd() / source_path.name
    
    # Clone the repository data
    if not clone_repository(source_path, dest_path):
        sys.exit(1)
    
    # Check out the working tree from HEAD
    dest_hst_dir = dest_path / ".hst"
    try:
        # Get HEAD commit
        current_commit_oid = get_current_commit_oid(dest_hst_dir)
        if current_commit_oid:
            # Checkout the working tree from HEAD
            checkout_from_commit(dest_hst_dir, dest_path, current_commit_oid)
        
        print(f"Successfully cloned repository to '{dest_path}'")
    except Exception as e:
        print(f"warning: repository cloned but working tree checkout failed: {e}")