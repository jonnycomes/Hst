import sys
from pathlib import Path
from hst.repo import find_repo_root, REPO_DIR


def run(argv):
    """
    Run the switch command.
    Usage:
      hst switch <branch>       # switch to existing branch
      hst switch -c <branch>    # create a new branch and switch to it
    """
    repo_root = find_repo_root(Path.cwd())
    repo_dir = repo_root / REPO_DIR

    if not argv:
        print("Usage: hst switch [-c] <branch>")
        sys.exit(1)

    if argv[0] == "-c":
        if len(argv) < 2:
            print("Usage: hst switch -c <branch>")
            sys.exit(1)
        _create_and_switch(repo_dir, argv[1])
    else:
        _switch_branch(repo_dir, argv[0])


def _switch_branch(repo_dir: Path, name: str):
    branch_path = repo_dir / "refs" / "heads" / name
    if not branch_path.exists():
        print(f"Branch '{name}' does not exist")
        sys.exit(1)

    # Update HEAD
    (repo_dir / "HEAD").write_text(f"ref: refs/heads/{name}")
    print(f"Switched to branch '{name}'")


def _create_and_switch(repo_dir: Path, name: str):
    branch_path = repo_dir / "refs" / "heads" / name
    if branch_path.exists():
        print(f"Branch '{name}' already exists")
        sys.exit(1)

    # Get current commit hash
    head_file = (repo_dir / "HEAD").read_text().strip()
    if head_file.startswith("ref: "):
        ref = head_file[5:]
        commit_hash = (repo_dir / ref).read_text().strip()
    else:
        commit_hash = head_file

    # Create new branch
    branch_path.write_text(commit_hash)
    # Update HEAD
    (repo_dir / "HEAD").write_text(f"ref: refs/heads/{name}")
    print(f"Created and switched to branch '{name}' at {commit_hash[:7]}")
