from pathlib import Path
from typing import Dict, List
from hst.repo import HST_DIRNAME
from hst.repo.objects import read_object
from hst.repo.utils import path_matches_filter
from hst.components import Commit, Tree, Blob


def checkout_commit(hst_dir: Path, repo_root: Path, commit_oid: str):
    """
    Update the working directory and index to match the given commit.
    """
    from hst.repo.index import write_index
    
    # Read the commit object
    commit_obj = read_object(hst_dir, commit_oid, Commit, store=False)
    if not commit_obj:
        print(f"Error: Cannot read commit {commit_oid}")
        return False

    # Get the tree mapping from the commit
    tree_mapping = read_tree_recursive(hst_dir, commit_obj.tree)

    # Clear current working directory (except .hst)
    clear_working_directory(repo_root)

    # Restore files from the tree
    restore_files_from_tree(hst_dir, repo_root, tree_mapping)

    # Update index to match the tree
    write_index(hst_dir, tree_mapping)

    return True


def checkout_from_commit(hst_dir: Path, repo_root: Path, commit_oid: str):
    """
    Restore working directory and index from a commit without clearing first.
    This is useful for operations like clone where the working directory is already empty.
    """
    from hst.repo.index import write_index
    
    # Read the commit object
    commit_obj = read_object(hst_dir, commit_oid, Commit, store=False)
    if not commit_obj:
        raise Exception(f"Could not read commit {commit_oid}")

    # Get the tree mapping from the commit
    tree_mapping = read_tree_recursive(hst_dir, commit_obj.tree)

    # Restore files from the tree (don't clear since working directory may be empty/new)
    restore_files_from_tree(hst_dir, repo_root, tree_mapping)

    # Update index to match the tree
    write_index(hst_dir, tree_mapping)

    return True


def read_tree_recursive(hst_dir: Path, tree_oid: str, prefix="") -> Dict[str, str]:
    """Recursively read a tree object into {path: blob_oid}."""
    tree_obj = read_object(hst_dir, tree_oid, Tree, store=False)
    mapping = {}
    if not tree_obj:
        return mapping

    for mode, name, child_oid in tree_obj.entries:
        path = f"{prefix}{name}"
        if mode == "040000":  # sub-tree
            mapping.update(read_tree_recursive(hst_dir, child_oid, prefix=f"{path}/"))
        else:
            mapping[path] = child_oid
    return mapping


def clear_working_directory(repo_root: Path):
    """
    Remove all files in the working directory except .hst.
    """
    for path in repo_root.rglob("*"):
        if path.is_file() and HST_DIRNAME not in path.parts:
            try:
                path.unlink()
            except OSError as e:
                print(f"Warning: Could not remove {path}: {e}")

    # Remove empty directories (but not .hst)
    for path in sorted(repo_root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir() and path.name != HST_DIRNAME and HST_DIRNAME not in path.parts:
            try:
                if not any(path.iterdir()):  # Only remove if empty
                    path.rmdir()
            except OSError:
                pass  # Directory not empty or other error, skip


def restore_files_from_tree(
    hst_dir: Path, repo_root: Path, tree_mapping: Dict[str, str]
):
    """
    Restore files in the working directory from the tree mapping.
    """
    for file_path, blob_oid in tree_mapping.items():
        # Read the blob object
        blob_obj = read_object(hst_dir, blob_oid, Blob, store=False)
        if not blob_obj:
            print(f"Warning: Could not read blob {blob_oid} for {file_path}")
            continue

        # Create the full path
        full_path = repo_root / file_path

        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file content
        try:
            full_path.write_bytes(blob_obj.data)
        except OSError as e:
            print(f"Warning: Could not write {file_path}: {e}")


def scan_working_tree(
    repo_root: Path, filter_paths: List[str] = None, store_blobs: bool = False
) -> Dict[str, str]:
    """
    Walk repo_root (excluding .hst) and hash each file into {path: oid}.
    If filter_paths is provided, only scan files matching those paths.
    If store_blobs is True, blob objects will be stored to disk.
    """
    mapping = {}
    for path in repo_root.rglob("*"):
        if path.is_file() and HST_DIRNAME not in path.parts:
            rel_path = str(path.relative_to(repo_root))

            # Apply path filter if specified
            if filter_paths and not path_matches_filter(rel_path, filter_paths):
                continue

            with open(path, "rb") as f:
                data = f.read()
            blob = Blob(data, store=store_blobs)  # Store based on parameter
            mapping[rel_path] = blob.oid()
    return mapping


def check_for_staged_changes(hst_dir: Path) -> bool:
    """
    Check if there are staged changes that differ from HEAD.
    Returns True if there are staged changes, False otherwise.
    """
    from hst.repo.head import get_current_commit_oid
    from hst.repo.objects import read_object
    from hst.repo.index import read_index
    from hst.components import Commit

    # Read current index
    index = read_index(hst_dir)

    # Get current commit
    current_commit_oid = get_current_commit_oid(hst_dir)
    if not current_commit_oid:
        # No commits yet, any files in index are staged changes
        return len(index) > 0

    # Read HEAD commit tree
    commit_obj = read_object(hst_dir, current_commit_oid, Commit, store=False)
    if not commit_obj:
        return len(index) > 0

    head_tree = read_tree_recursive(hst_dir, commit_obj.tree)

    # Compare index with HEAD tree
    return index != head_tree


# End of file
