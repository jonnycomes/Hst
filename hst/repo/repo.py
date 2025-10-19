import sys
import shutil
from pathlib import Path
from typing import Tuple, Set, List, Callable, Optional

HST_DIRNAME = ".hst"


def find_repo_root(start_dir: Path) -> Path:
    """Walk up from start_dir to find the repository root (.hst folder)."""
    path = start_dir.resolve()
    while path != path.parent:
        if (path / HST_DIRNAME).exists():
            return path
        path = path.parent
    print("Not inside a Hst repository")
    sys.exit(1)


def get_repo_paths() -> Tuple[Path, Path]:
    """Get repository root and .hst directory paths.

    Returns:
        Tuple of (repo_root, hst_dir) where:
        - repo_root: The root directory of the repository
        - hst_dir: The .hst directory path
    """
    repo_root = find_repo_root(Path.cwd())
    hst_dir = repo_root / HST_DIRNAME
    return repo_root, hst_dir


def clone_repository(source_path: Path, dest_path: Path) -> bool:
    """
    Clone a repository from source_path to dest_path.

    Returns:
        True if successful, False otherwise
    """
    source_path = source_path.resolve()
    dest_path = dest_path.resolve()

    # Check if source is a valid hst repository
    source_hst_dir = validate_repository(source_path)
    if not source_hst_dir:
        print(f"fatal: '{source_path}' does not appear to be a hst repository")
        return False

    # Check if destination already exists
    if dest_path.exists():
        print(f"fatal: destination path '{dest_path}' already exists")
        return False

    # Create destination directory
    try:
        dest_path.mkdir(parents=True)
        print(f"Cloning into '{dest_path}'...")
    except OSError as e:
        print(f"fatal: could not create directory '{dest_path}': {e}")
        return False

    # Copy the .hst directory
    dest_hst_dir = dest_path / HST_DIRNAME
    try:
        shutil.copytree(source_hst_dir, dest_hst_dir)
        return True
    except OSError as e:
        print(f"fatal: could not copy repository data: {e}")
        # Clean up the destination directory
        shutil.rmtree(dest_path, ignore_errors=True)
        return False


def validate_repository(repo_path: Path) -> Optional[Path]:
    """
    Validate that a path contains a valid hst repository.

    Args:
        repo_path: Path to check for repository

    Returns:
        Path to .hst directory if valid, None otherwise
    """
    repo_path = repo_path.resolve()
    hst_dir = repo_path / HST_DIRNAME

    if not repo_path.exists():
        return None

    if not hst_dir.exists():
        return None

    return hst_dir


def walk_commit_objects(hst_dir: Path, start_commit: str,
                       visitor: Callable[[str, type], bool]) -> bool:
    """
    Walk through all objects reachable from a commit.

    Args:
        hst_dir: Path to .hst directory
        start_commit: Starting commit hash
        visitor: Function called for each object (hash, type) -> continue walking?

    Returns:
        True if walk completed successfully, False if error occurred
    """
    from hst.repo.objects import read_object
    from hst.components import Commit, Tree, Blob

    visited = set()
    queue = [(start_commit, Commit)]

    while queue:
        obj_hash, obj_type = queue.pop(0)

        if obj_hash in visited:
            continue
        visited.add(obj_hash)

        # Call visitor function
        if not visitor(obj_hash, obj_type):
            continue

        # Read object to find references
        obj = read_object(hst_dir, obj_hash, obj_type, store=False)
        if not obj:
            return False

        # Add referenced objects to queue
        if isinstance(obj, Commit):
            queue.append((obj.tree, Tree))
            for parent in obj.parents:
                if parent and parent != 'None':  # Skip None parents (both None and string 'None')
                    queue.append((parent, Commit))
        elif isinstance(obj, Tree):
            for mode, name, child_hash in obj.entries:
                if mode == "040000":  # Directory
                    queue.append((child_hash, Tree))
                else:  # File
                    queue.append((child_hash, Blob))

    return True


def copy_objects_to_repository(source_hst_dir: Path, dest_hst_dir: Path, 
                              start_commit: str) -> bool:
    """
    Copy all objects reachable from start_commit to the destination repository.
    Only copies objects that don't already exist in the destination.
    
    Args:
        source_hst_dir: Source .hst directory
        dest_hst_dir: Destination .hst directory  
        start_commit: Starting commit hash
        
    Returns:
        True if successful, False otherwise
    """
    # Collect objects that need to be copied
    objects_to_copy = []
    
    def collect_missing_objects(obj_hash: str, obj_type: type) -> bool:
        # Check if object already exists in destination
        dest_obj_path = dest_hst_dir / "objects" / obj_hash[:2] / obj_hash[2:]
        if not dest_obj_path.exists():
            # Mark for copying
            objects_to_copy.append(obj_hash)
        return True  # Continue walking
    
    # Walk all objects reachable from the commit
    if not walk_commit_objects(source_hst_dir, start_commit, collect_missing_objects):
        print(f"error: failed to walk objects from commit {start_commit}")
        return False
    
    # Copy all collected objects
    for obj_hash in objects_to_copy:
        if not copy_single_object(source_hst_dir, dest_hst_dir, obj_hash):
            return False
    
    return True


def copy_single_object(source_hst_dir: Path, dest_hst_dir: Path, 
                      obj_hash: str) -> bool:
    """
    Copy a single object from source to destination repository.
    
    Args:
        source_hst_dir: Source .hst directory
        dest_hst_dir: Destination .hst directory
        obj_hash: Hash of object to copy
        
    Returns:
        True if successful, False otherwise
    """
    # Source object path
    source_obj_path = source_hst_dir / "objects" / obj_hash[:2] / obj_hash[2:]
    if not source_obj_path.exists():
        print(f"error: source object {obj_hash} not found")
        return False
    
    # Destination object path
    dest_obj_dir = dest_hst_dir / "objects" / obj_hash[:2]
    dest_obj_path = dest_obj_dir / obj_hash[2:]
    
    # Create directory if needed
    dest_obj_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy the object file
    try:
        shutil.copy2(source_obj_path, dest_obj_path)
        return True
    except OSError as e:
        print(f"error: failed to copy object {obj_hash}: {e}")
        return False
