import sys
from pathlib import Path
from typing import List, Dict, Optional
from hst.repo import get_repo_paths
from hst.repo.head import get_current_commit_oid, get_current_branch, update_head
from hst.repo.index import read_index, write_index
from hst.repo.objects import read_object
from hst.repo.worktree import read_tree_recursive, checkout_commit, clear_working_directory, restore_files_from_tree, scan_working_tree
from hst.components import Commit, Blob, Tree


def run(argv: List[str]):
    """
    Run the merge command.
    """
    if not argv:
        print("usage: hst merge <branch-name>")
        sys.exit(1)
    
    target = argv[0]
    
    # Handle special flags
    if target == "--abort":
        abort_merge()
        return
    elif target == "--continue":
        continue_merge()
        return
    
    repo_root, hst_dir = get_repo_paths()
    
    # Get current state
    current_commit_oid = get_current_commit_oid(hst_dir)
    if not current_commit_oid:
        print("error: no commits yet")
        sys.exit(1)
    
    current_branch = get_current_branch(hst_dir)
    
    # Resolve target commit
    target_commit_oid = resolve_target_commit(hst_dir, target)
    if not target_commit_oid:
        print(f"error: unknown revision '{target}'")
        sys.exit(1)
    
    # Check if already up to date
    if current_commit_oid == target_commit_oid:
        print("Already up to date.")
        return
    
    # Find merge base
    merge_base_oid = find_merge_base(hst_dir, current_commit_oid, target_commit_oid)
    if not merge_base_oid:
        print("error: no common ancestor found")
        sys.exit(1)
    
    # Determine merge strategy
    if merge_base_oid == current_commit_oid:
        # Fast-forward merge
        perform_fast_forward_merge(repo_root, hst_dir, target_commit_oid, target)
    elif merge_base_oid == target_commit_oid:
        # Already up to date
        print("Already up to date.")
    else:
        # True merge needed
        perform_three_way_merge(repo_root, hst_dir, current_commit_oid, target_commit_oid, merge_base_oid, target, current_branch)


def resolve_target_commit(hst_dir: Path, target: str) -> Optional[str]:
    """Resolve branch name or commit hash to a commit OID."""
    # First try as a commit hash
    if len(target) >= 7:  # Minimum hash length
        try:
            commit_obj = read_object(hst_dir, target, Commit, store=False)
            if commit_obj:
                return target
        except Exception:
            pass
    
    # Try as a branch name
    branch_file = hst_dir / "refs" / "heads" / target
    if branch_file.exists():
        return branch_file.read_text().strip()
    
    return None


def find_merge_base(hst_dir: Path, commit1_oid: str, commit2_oid: str) -> Optional[str]:
    """Find the merge base (common ancestor) of two commits."""
    # Simple implementation: BFS to find first common ancestor
    visited1 = set()
    visited2 = set()
    queue1 = [commit1_oid]
    queue2 = [commit2_oid]
    
    while queue1 or queue2:
        # Process commits from first branch
        if queue1:
            current = queue1.pop(0)
            if current in visited2:
                return current
            if current not in visited1:
                visited1.add(current)
                commit_obj = read_object(hst_dir, current, Commit, store=False)
                if commit_obj:
                    queue1.extend(commit_obj.parents)
        
        # Process commits from second branch
        if queue2:
            current = queue2.pop(0)
            if current in visited1:
                return current
            if current not in visited2:
                visited2.add(current)
                commit_obj = read_object(hst_dir, current, Commit, store=False)
                if commit_obj:
                    queue2.extend(commit_obj.parents)
    
    return None


def perform_fast_forward_merge(repo_root: Path, hst_dir: Path, target_commit_oid: str, target: str):
    """Perform a fast-forward merge."""
    print(f"Updating {get_current_commit_oid(hst_dir)[:7]}..{target_commit_oid[:7]}")
    print("Fast-forward")
    
    # Update HEAD to point to target commit
    update_head(hst_dir, target_commit_oid)
    
    # Update working tree and index
    if not checkout_commit(hst_dir, repo_root, target_commit_oid):
        print("error: failed to update working tree")
        sys.exit(1)


def perform_three_way_merge(repo_root: Path, hst_dir: Path, current_oid: str, target_oid: str, base_oid: str, target: str, current_branch: Optional[str]):
    """Perform a three-way merge."""
    print("Merge made by the 'recursive' strategy.")
    
    # Get tree mappings for all three commits
    base_tree = read_tree_recursive(hst_dir, read_object(hst_dir, base_oid, Commit, store=False).tree)
    current_tree = read_tree_recursive(hst_dir, read_object(hst_dir, current_oid, Commit, store=False).tree)
    target_tree = read_tree_recursive(hst_dir, read_object(hst_dir, target_oid, Commit, store=False).tree)
    
    # Perform the merge
    merged_tree, conflicts = merge_trees(hst_dir, repo_root, base_tree, current_tree, target_tree)
    
    if conflicts:
        # Write conflicted files and set up merge state
        print("Automatic merge failed; fix conflicts and then commit the result.")
        write_merge_state(hst_dir, current_oid, target_oid, conflicts)
        
        # Update index with merged content (including conflict markers)
        write_index(hst_dir, merged_tree)
        
        # Write conflict files to working tree
        write_conflicts_to_worktree(repo_root, hst_dir, merged_tree, conflicts)
        sys.exit(1)
    else:
        # Successful merge - create merge commit
        # Update working tree first
        clear_working_directory(repo_root)
        restore_files_from_tree(hst_dir, repo_root, merged_tree)
        
        # Update index
        write_index(hst_dir, merged_tree)
        
        # Create merge commit
        message = f"Merge branch '{target}'"
        if current_branch and target != current_branch:
            message = f"Merge branch '{target}' into {current_branch}"
        
        # Get current user info (simplified)
        author = "User"  # TODO: Get from config
        
        # Create commit with two parents
        commit_obj = Commit(
            tree=create_tree_from_index(hst_dir, merged_tree),
            parents=[current_oid, target_oid],
            author=author,
            committer=author,
            message=message,
            store=True
        )
        
        # Update HEAD
        update_head(hst_dir, commit_obj.oid())
        print(f"Merge commit {commit_obj.oid()[:7]} created.")


def merge_trees(hst_dir: Path, repo_root: Path, base_tree: Dict[str, str], current_tree: Dict[str, str], target_tree: Dict[str, str]) -> tuple[Dict[str, str], List[str]]:
    """Merge three trees and return the result plus any conflicts."""
    merged_tree = {}
    conflicts = []
    
    # Get all files that exist in any tree
    all_files = set(base_tree.keys()) | set(current_tree.keys()) | set(target_tree.keys())
    
    for file_path in all_files:
        base_oid = base_tree.get(file_path)
        current_oid = current_tree.get(file_path)
        target_oid = target_tree.get(file_path)
        
        # Determine what happened to this file
        if base_oid == current_oid == target_oid:
            # No change
            if current_oid:
                merged_tree[file_path] = current_oid
        elif base_oid == current_oid:
            # Only target changed
            if target_oid:
                merged_tree[file_path] = target_oid
        elif base_oid == target_oid:
            # Only current changed  
            if current_oid:
                merged_tree[file_path] = current_oid
        elif current_oid == target_oid:
            # Both changed to same thing
            if current_oid:
                merged_tree[file_path] = current_oid
        else:
            # Conflict: both branches modified the file differently
            conflict_content = create_conflict_markers(hst_dir, file_path, current_oid, target_oid)
            
            # Store conflicted content as a new blob
            conflict_blob = Blob(conflict_content.encode('utf-8'), store=True)
            merged_tree[file_path] = conflict_blob.oid()
            conflicts.append(file_path)
    
    return merged_tree, conflicts


def create_conflict_markers(hst_dir: Path, file_path: str, current_oid: Optional[str], target_oid: Optional[str]) -> str:
    """Create conflict markers for a file."""
    current_content = ""
    target_content = ""
    
    if current_oid:
        blob_obj = read_object(hst_dir, current_oid, Blob, store=False)
        if blob_obj:
            try:
                current_content = blob_obj.data.decode('utf-8')
            except UnicodeDecodeError:
                current_content = "[Binary file]"
    
    if target_oid:
        blob_obj = read_object(hst_dir, target_oid, Blob, store=False)
        if blob_obj:
            try:
                target_content = blob_obj.data.decode('utf-8')
            except UnicodeDecodeError:
                target_content = "[Binary file]"
    
    # Create conflict markers
    conflict_content = f"""<<<<<<< HEAD
{current_content}=======
{target_content}>>>>>>> MERGE_HEAD
"""
    return conflict_content


def create_tree_from_index(hst_dir: Path, index: Dict[str, str]) -> str:
    """Create a tree object from the current index."""
    # Create tree with all files in root directory (simplified)
    entries = []
    for file_path, blob_oid in sorted(index.items()):
        # For simplicity, treat all files as regular files in root
        entries.append(("100644", file_path, blob_oid))
    
    tree_obj = Tree(entries, store=True)
    return tree_obj.oid()


def write_merge_state(hst_dir: Path, current_oid: str, target_oid: str, conflicts: List[str]):
    """Write merge state files for conflict resolution."""
    # Write MERGE_HEAD
    merge_head_file = hst_dir / "MERGE_HEAD"
    merge_head_file.write_text(target_oid + "\n")
    
    # Write MERGE_MSG
    merge_msg_file = hst_dir / "MERGE_MSG"
    merge_msg_file.write_text("Merge commit\n\nConflicts:\n" + "\n".join(f"\t{f}" for f in conflicts) + "\n")


def abort_merge():
    """Abort an in-progress merge."""
    repo_root, hst_dir = get_repo_paths()
    
    merge_head_file = hst_dir / "MERGE_HEAD"
    if not merge_head_file.exists():
        print("error: no merge in progress")
        sys.exit(1)
    
    # Reset to original state
    original_commit = get_current_commit_oid(hst_dir)
    if original_commit:
        checkout_commit(hst_dir, repo_root, original_commit)
    
    # Clean up merge state files
    merge_head_file.unlink()
    merge_msg_file = hst_dir / "MERGE_MSG"
    if merge_msg_file.exists():
        merge_msg_file.unlink()
    
    print("Merge aborted.")


def continue_merge():
    """Continue an in-progress merge after resolving conflicts."""
    repo_root, hst_dir = get_repo_paths()
    
    merge_head_file = hst_dir / "MERGE_HEAD"
    if not merge_head_file.exists():
        print("error: no merge in progress")
        sys.exit(1)
    
    # Check if there are still conflicts
    index = read_index(hst_dir)
    conflicts_remaining = []
    
    for file_path, blob_oid in index.items():
        file_full_path = repo_root / file_path
        if file_full_path.exists():
            with open(file_full_path, 'r') as f:
                content = f.read()
                if "<<<<<<< HEAD" in content and ">>>>>>> MERGE_HEAD" in content:
                    conflicts_remaining.append(file_path)
    
    if conflicts_remaining:
        print("error: you have unresolved conflicts")
        print("hint: fix conflicts and then commit the result")
        for conflict in conflicts_remaining:
            print(f"\t{conflict}")
        sys.exit(1)
    
    # Create merge commit
    target_oid = merge_head_file.read_text().strip()
    current_oid = get_current_commit_oid(hst_dir)
    
    # Read merge message
    merge_msg_file = hst_dir / "MERGE_MSG"
    message = "Merge commit"
    if merge_msg_file.exists():
        message = merge_msg_file.read_text().strip()
    
    # Get author info
    author = "User"  # TODO: Get from config
    
    # Update index with current working tree
    current_worktree = scan_working_tree(repo_root, store_blobs=True)
    write_index(hst_dir, current_worktree)
    
    # Create merge commit
    tree_oid = create_tree_from_index(hst_dir, current_worktree)
    commit_obj = Commit(
        tree=tree_oid,
        parents=[current_oid, target_oid],
        author=author,
        committer=author,
        message=message,
        store=True
    )
    
    # Update HEAD
    update_head(hst_dir, commit_obj.oid())
    
    # Clean up merge state
    merge_head_file.unlink()
    if merge_msg_file.exists():
        merge_msg_file.unlink()
    
    print(f"Merge commit {commit_obj.oid()[:7]} created.")


def write_conflicts_to_worktree(repo_root: Path, hst_dir: Path, merged_tree: Dict[str, str], conflicts: List[str]):
    """Write conflict files with markers to the working tree."""
    for file_path in conflicts:
        blob_oid = merged_tree[file_path]
        blob_obj = read_object(hst_dir, blob_oid, Blob, store=False)
        if blob_obj:
            file_full_path = repo_root / file_path
            # Ensure parent directories exist
            file_full_path.parent.mkdir(parents=True, exist_ok=True)
            # Write the conflict content to the file
            with open(file_full_path, 'wb') as f:
                f.write(blob_obj.data)