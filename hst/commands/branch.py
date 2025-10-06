import sys
from pathlib import Path
from typing import List
from hst.repo import get_repo_paths
from hst.repo.head import get_current_commit_oid, get_current_branch


def run(argv: List[str]):
    """
    Run the branch command
    """
    repo_root, hst_dir = get_repo_paths()

    if not argv:
        _list_branches(hst_dir)
    elif argv[0] == "-D":
        if len(argv) < 2:
            print("Usage: hst branch -D <branch>")
            sys.exit(1)
        _delete_branch(hst_dir, argv[1])
    else:
        name = argv[0]
        _create_branch(hst_dir, name)


def _list_branches(hst_dir: Path):
    heads_dir = hst_dir / "refs" / "heads"
    branches = [p.name for p in heads_dir.iterdir() if p.is_file()]

    # figure out current branch
    current = get_current_branch(hst_dir)

    for b in branches:
        prefix = "*" if b == current else " "
        print(f"{prefix} {b}")


def _create_branch(hst_dir: Path, name: str):
    commit_hash = get_current_commit_oid(hst_dir)
    if not commit_hash:
        print("No commits yet")
        sys.exit(1)

    branch_path = hst_dir / "refs" / "heads" / name
    if branch_path.exists():
        print(f"Branch {name} already exists")
        sys.exit(1)

    branch_path.write_text(commit_hash)
    print(f"Created branch {name} at {commit_hash[:7]}")


def _delete_branch(hst_dir: Path, name: str):
    current = get_current_branch(hst_dir)

    if name == current:
        print(f"Cannot delete branch '{name}' while on it")
        sys.exit(1)

    branch_path = hst_dir / "refs" / "heads" / name
    if not branch_path.exists():
        print(f"Branch '{name}' not found")
        sys.exit(1)

    branch_path.unlink()
    print(f"Deleted branch {name}")
