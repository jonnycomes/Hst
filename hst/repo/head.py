from pathlib import Path
from typing import Optional


def get_current_commit_oid(hst_dir: Path) -> Optional[str]:
    """Get the current commit OID that HEAD points to."""
    head_path = hst_dir / "HEAD"
    if not head_path.exists():
        return None

    head_contents = head_path.read_text().strip()
    if head_contents.startswith("ref: "):
        # HEAD points to a branch
        ref_path = hst_dir / head_contents[5:]
        if ref_path.exists():
            return ref_path.read_text().strip() or None
        return None
    else:
        # Detached HEAD
        return head_contents or None


def get_current_branch(hst_dir: Path) -> Optional[str]:
    """Get the current branch name, or None if in detached HEAD."""
    head_path = hst_dir / "HEAD"
    if not head_path.exists():
        return None

    head_contents = head_path.read_text().strip()
    if head_contents.startswith("ref: "):
        return head_contents.split("/")[-1]
    return None


def update_head(hst_dir: Path, commit_oid: str) -> None:
    """Update HEAD after creating a new commit.

    - If HEAD points to a branch (symbolic ref), update that branch ref.
    - If HEAD is detached (points directly to a commit), update HEAD itself.
    """
    head_path = hst_dir / "HEAD"
    head_contents = head_path.read_text().strip()

    if head_contents.startswith("ref: "):
        # Symbolic ref: update the branch
        ref_path = hst_dir / head_contents[5:]
        ref_path.write_text(commit_oid + "\n")
    else:
        # Detached HEAD: update HEAD directly
        head_path.write_text(commit_oid + "\n")
