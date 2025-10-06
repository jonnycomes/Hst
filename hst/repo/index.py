import json
from pathlib import Path
from typing import Dict


def read_index(hst_dir: Path) -> Dict[str, str]:
    """Read the index file into a path->oid mapping."""
    index_path = hst_dir / "index"
    if not index_path.exists():
        return {}

    with open(index_path, "r") as f:
        return json.load(f)


def write_index(hst_dir: Path, index: Dict[str, str]) -> None:
    """Write the index mapping to disk."""
    index_path = hst_dir / "index"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2))
