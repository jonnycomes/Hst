import sys
from pathlib import Path
from hst.repo import find_repo_root, REPO_DIR

def run(argv):
    """
    Run the branch command
    """
    repo_root = find_repo_root(Path.cwd())
    repo_dir = repo_root / REPO_DIR

    if not argv:
        _list_branches(repo_dir)
    elif argv[0] == "-D":
        if len(argv) < 2:
            print("Usage: hst branch -D <branch>")
            sys.exit(1)
        _delete_branch(repo_dir, argv[1])
    else:
        name = argv[0]
        _create_branch(repo_dir, name)


def _list_branches(repo_dir: Path):
    heads_dir = repo_dir / "refs" / "heads"
    branches = [p.name for p in heads_dir.iterdir() if p.is_file()]

    # figure out current branch
    head_file = (repo_dir / "HEAD").read_text().strip()
    current = None
    if head_file.startswith("ref: "):
        current = head_file.split("/")[-1]

    for b in branches:
        prefix = "*" if b == current else " "
        print(f"{prefix} {b}")

def _create_branch(repo_dir: Path, name: str):
    head = (repo_dir / "HEAD").read_text().strip()
    if head.startswith("ref: "):
        ref = head[5:]
        commit_hash = (repo_dir / ref).read_text().strip()
    else:
        commit_hash = head

    branch_path = repo_dir / "refs" / "heads" / name
    if branch_path.exists():
        print(f"Branch {name} already exists")
        sys.exit(1)

    branch_path.write_text(commit_hash)
    print(f"Created branch {name} at {commit_hash[:7]}")

def _delete_branch(repo_dir: Path, name: str):
    head_file = (repo_dir / "HEAD").read_text().strip()
    current = None
    if head_file.startswith("ref: "):
        current = head_file.split("/")[-1]

    if name == current:
        print(f"Cannot delete branch '{name}' while on it")
        sys.exit(1)

    branch_path = repo_dir / "refs" / "heads" / name
    if not branch_path.exists():
        print(f"Branch '{name}' not found")
        sys.exit(1)

    branch_path.unlink()
    print(f"Deleted branch {name}")

