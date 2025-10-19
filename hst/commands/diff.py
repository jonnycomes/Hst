import sys
import difflib
from pathlib import Path
from typing import List, Dict, Optional
from hst.repo import get_repo_paths
from hst.repo.head import get_current_commit_oid
from hst.repo.index import read_index
from hst.repo.objects import read_object
from hst.repo.worktree import read_tree_recursive, scan_working_tree
from hst.repo.refs import resolve_commit_ref
from hst.components import Commit, Blob
from hst.colors import CYAN, GREEN, RED, BOLD, RESET


def run(argv: List[str]):
    """
    Run the diff command.
    """
    repo_root, hst_dir = get_repo_paths()

    # Parse arguments
    staged = "--staged" in argv or "--cached" in argv
    if staged:
        argv = [arg for arg in argv if arg not in ["--staged", "--cached"]]

    if not argv:
        # No commits specified
        if staged:
            _diff_index_vs_head(repo_root, hst_dir)
        else:
            _diff_worktree_vs_index(repo_root, hst_dir)
    elif len(argv) == 1:
        # One commit specified
        if staged:
            print("error: --staged can only be used with no arguments")
            sys.exit(1)
        _diff_worktree_vs_commit(repo_root, hst_dir, argv[0])
    elif len(argv) == 2:
        # Two commits specified
        if staged:
            print("error: --staged can only be used with no arguments")
            sys.exit(1)
        _diff_commit_vs_commit(repo_root, hst_dir, argv[0], argv[1])
    else:
        print("Usage: hst diff [--staged] [<commit>] [<commit>]")
        sys.exit(1)


def _diff_worktree_vs_index(repo_root: Path, hst_dir: Path):
    """Show differences between working tree and index."""
    print(f"{BOLD}diff --hst a/index b/worktree{RESET}")

    index = read_index(hst_dir)
    worktree = scan_working_tree(repo_root)

    _show_diff_between_trees("index", index, "worktree", worktree, hst_dir, repo_root)


def _diff_index_vs_head(repo_root: Path, hst_dir: Path):
    """Show differences between index and HEAD."""
    print(f"{BOLD}diff --hst a/HEAD b/index{RESET}")

    # Get HEAD tree
    current_commit_oid = get_current_commit_oid(hst_dir)
    if not current_commit_oid:
        print("No HEAD commit found")
        return

    commit_obj = read_object(hst_dir, current_commit_oid, Commit, store=False)
    if not commit_obj:
        print("Cannot read HEAD commit")
        return

    head_tree = read_tree_recursive(hst_dir, commit_obj.tree)
    index = read_index(hst_dir)

    _show_diff_between_trees("HEAD", head_tree, "index", index, hst_dir, repo_root)


def _diff_worktree_vs_commit(repo_root: Path, hst_dir: Path, commit_ref: str):
    """Show differences between working tree and a specific commit."""
    # Resolve commit reference
    commit_oid = resolve_commit_ref(hst_dir, commit_ref)
    if not commit_oid:
        print(f"fatal: bad revision '{commit_ref}'")
        sys.exit(1)

    print(f"{BOLD}diff --hst a/{commit_oid[:7]} b/worktree{RESET}")

    # Get commit tree
    commit_obj = read_object(hst_dir, commit_oid, Commit, store=False)
    if not commit_obj:
        print(f"Cannot read commit {commit_oid}")
        sys.exit(1)

    commit_tree = read_tree_recursive(hst_dir, commit_obj.tree)
    worktree = scan_working_tree(repo_root)

    _show_diff_between_trees(
        commit_oid[:7], commit_tree, "worktree", worktree, hst_dir, repo_root
    )


def _diff_commit_vs_commit(
    repo_root: Path, hst_dir: Path, commit1_ref: str, commit2_ref: str
):
    """Show differences between two commits."""
    # Resolve commit references
    commit1_oid = resolve_commit_ref(hst_dir, commit1_ref)
    if not commit1_oid:
        print(f"fatal: bad revision '{commit1_ref}'")
        sys.exit(1)

    commit2_oid = resolve_commit_ref(hst_dir, commit2_ref)
    if not commit2_oid:
        print(f"fatal: bad revision '{commit2_ref}'")
        sys.exit(1)

    print(f"{BOLD}diff --hst a/{commit1_oid[:7]} b/{commit2_oid[:7]}{RESET}")

    # Get first commit tree
    commit1_obj = read_object(hst_dir, commit1_oid, Commit, store=False)
    if not commit1_obj:
        print(f"Cannot read commit {commit1_oid}")
        sys.exit(1)

    # Get second commit tree
    commit2_obj = read_object(hst_dir, commit2_oid, Commit, store=False)
    if not commit2_obj:
        print(f"Cannot read commit {commit2_oid}")
        sys.exit(1)

    tree1 = read_tree_recursive(hst_dir, commit1_obj.tree)
    tree2 = read_tree_recursive(hst_dir, commit2_obj.tree)

    _show_diff_between_trees(
        commit1_oid[:7], tree1, commit2_oid[:7], tree2, hst_dir, repo_root
    )


def _show_diff_between_trees(
    name1: str,
    tree1: Dict[str, str],
    name2: str,
    tree2: Dict[str, str],
    hst_dir: Path,
    repo_root: Path = None,
):
    """Show differences between two trees."""
    all_paths = set(tree1.keys()) | set(tree2.keys())

    for path in sorted(all_paths):
        oid1 = tree1.get(path)
        oid2 = tree2.get(path)

        if oid1 == oid2:
            continue  # No change

        if oid1 is None:
            # File added in tree2
            _show_file_diff(path, None, oid2, name1, name2, hst_dir, repo_root)
        elif oid2 is None:
            # File deleted in tree2
            _show_file_diff(path, oid1, None, name1, name2, hst_dir, repo_root)
        else:
            # File modified
            _show_file_diff(path, oid1, oid2, name1, name2, hst_dir, repo_root)


def _show_file_diff(
    path: str,
    oid1: Optional[str],
    oid2: Optional[str],
    name1: str,
    name2: str,
    hst_dir: Path,
    repo_root: Path = None,
):
    """Show diff for a single file."""
    print(f"{BOLD}diff --hst a/{path} b/{path}{RESET}")

    if oid1 is None:
        print(f"{BOLD}new file mode 100644{RESET}")
        print(f"{CYAN}index 0000000..{oid2[:7]}{RESET}")
        print(f"{BOLD}--- /dev/null{RESET}")
        print(f"{BOLD}+++ b/{path}{RESET}")
        content2 = _get_file_content(oid2, hst_dir, name2, path, repo_root)
        _show_unified_diff([], content2.splitlines() if content2 else [])
    elif oid2 is None:
        print(f"{BOLD}deleted file mode 100644{RESET}")
        print(f"{CYAN}index {oid1[:7]}..0000000{RESET}")
        print(f"{BOLD}--- a/{path}{RESET}")
        print(f"{BOLD}+++ /dev/null{RESET}")
        content1 = _get_file_content(oid1, hst_dir, name1, path, repo_root)
        _show_unified_diff(content1.splitlines() if content1 else [], [])
    else:
        print(f"{CYAN}index {oid1[:7]}..{oid2[:7]} 100644{RESET}")
        print(f"{BOLD}--- a/{path}{RESET}")
        print(f"{BOLD}+++ b/{path}{RESET}")
        content1 = _get_file_content(oid1, hst_dir, name1, path, repo_root)
        content2 = _get_file_content(oid2, hst_dir, name2, path, repo_root)
        lines1 = content1.splitlines() if content1 else []
        lines2 = content2.splitlines() if content2 else []
        _show_unified_diff(lines1, lines2)


def _get_file_content(
    oid: Optional[str],
    hst_dir: Path,
    tree_name: str = "",
    file_path: str = "",
    repo_root: Path = None,
) -> str:
    """Get content of a file by its blob OID or from working tree."""
    if not oid:
        return ""

    # If this is worktree content, read directly from the file
    if tree_name == "worktree" and repo_root and file_path:
        try:
            file_full_path = repo_root / file_path
            if file_full_path.exists():
                with open(file_full_path, "r", encoding="utf-8") as f:
                    return f.read()
        except UnicodeDecodeError:
            return "[Binary file]"
        return ""

    # Otherwise, read from blob object
    blob_obj = read_object(hst_dir, oid, Blob, store=False)
    if not blob_obj:
        return ""

    try:
        return blob_obj.data.decode("utf-8")
    except UnicodeDecodeError:
        return "[Binary file]"


def _show_unified_diff(lines1: List[str], lines2: List[str]):
    """Show unified diff between two lists of lines."""
    # Simple diff implementation - could be enhanced with proper difflib
    diff = difflib.unified_diff(
        lines1,
        lines2,
        lineterm="",
        n=3,  # 3 lines of context
    )

    # Skip the first two lines (file headers) as we already printed them
    diff_lines = list(diff)
    if len(diff_lines) > 2:
        for line in diff_lines[2:]:
            if line.startswith("@@"):
                # Hunk header (context line numbers)
                print(f"{CYAN}{line}{RESET}")
            elif line.startswith("+"):
                # Added line
                print(f"{GREEN}{line}{RESET}")
            elif line.startswith("-"):
                # Removed line
                print(f"{RED}{line}{RESET}")
            else:
                # Context line (unchanged)
                print(line)


