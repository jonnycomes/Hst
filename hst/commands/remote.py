import sys
from pathlib import Path
from typing import List
from hst.repo import get_repo_paths
from hst.repo.config import add_remote, remove_remote, list_remotes, get_remote_url


def run(argv: List[str]):
    """
    Run the remote command.
    
    Usage:
    hst remote                    - list remote names
    hst remote -v                 - list remote names and URLs
    hst remote add <name> <url>   - add a new remote
    hst remote remove <name>      - remove a remote
    hst remote get-url <name>     - get URL of a remote
    """
    repo_root, hst_dir = get_repo_paths()
    
    if not argv:
        # List remotes (names only)
        list_remotes(hst_dir, verbose=False)
    elif argv[0] == "-v":
        # List remotes with URLs
        list_remotes(hst_dir, verbose=True)
    elif argv[0] == "add":
        if len(argv) < 3:
            print("Usage: hst remote add <name> <url>")
            sys.exit(1)
        _add_remote(hst_dir, argv[1], argv[2])
    elif argv[0] == "remove" or argv[0] == "rm":
        if len(argv) < 2:
            print("Usage: hst remote remove <name>")
            sys.exit(1)
        _remove_remote(hst_dir, argv[1])
    elif argv[0] == "get-url":
        if len(argv) < 2:
            print("Usage: hst remote get-url <name>")
            sys.exit(1)
        _get_remote_url(hst_dir, argv[1])
    else:
        print("Usage: hst remote [-v] | add <name> <url> | remove <name> | get-url <name>")
        sys.exit(1)


def _add_remote(hst_dir: Path, name: str, url: str):
    """Add a remote."""
    # Validate the URL/path
    url_path = Path(url)
    if url_path.exists():
        # It's a local path - convert to absolute path
        url = str(url_path.resolve())
        # Check if it's a valid hst repository
        if not (url_path / ".hst").exists():
            print(f"fatal: '{url}' does not appear to be a hst repository")
            sys.exit(1)
    # For non-local URLs, we'll accept them as-is for future use
    
    if add_remote(hst_dir, name, url):
        print(f"Added remote '{name}' -> '{url}'")
    else:
        print(f"fatal: remote '{name}' already exists")
        sys.exit(1)


def _remove_remote(hst_dir: Path, name: str):
    """Remove a remote."""
    if remove_remote(hst_dir, name):
        print(f"Removed remote '{name}'")
    else:
        print(f"fatal: No such remote '{name}'")
        sys.exit(1)


def _get_remote_url(hst_dir: Path, name: str):
    """Get the URL of a remote."""
    url = get_remote_url(hst_dir, name)
    if url:
        print(url)
    else:
        print(f"fatal: No such remote '{name}'")
        sys.exit(1)