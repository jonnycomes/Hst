from pathlib import Path
import zlib
from typing import Optional, Type
from hst.hst_objects import Object, Tree


def read_object(
    hst_dir: Path, oid: str, cls: Type[Object], store: bool = False
) -> Optional[Object]:
    """Read and decompress an object by OID into the given class."""
    obj_path = hst_dir / "objects" / oid[:2] / oid[2:]
    if not obj_path.exists():
        return None

    data = zlib.decompress(obj_path.read_bytes())
    header, _, content = data.partition(b"\x00")
    return cls.deserialize(content, store=store)


def build_tree(repo_root: Path, index: dict, base_path: Optional[Path] = None) -> Tree:
    """
    Recursively build a tree object from the index.

    index: mapping from relative paths (str) to blob OIDs
    base_path: current directory relative to repo_root
    """
    if base_path is None:
        base_path = Path("")

    entries = []

    # Find all direct children (files and subdirectories) under base_path
    direct_children = {}  # name -> oid (for files) or None (for directories)

    for path_str, blob_oid in index.items():
        path = Path(path_str)

        # Skip if not under current base_path
        if base_path != Path(""):
            try:
                rel_path = path.relative_to(base_path)
            except ValueError:
                continue
        else:
            rel_path = path

        # Get the immediate child name
        if len(rel_path.parts) == 1:
            # This is a direct file child
            direct_children[rel_path.parts[0]] = blob_oid
        elif len(rel_path.parts) > 1:
            # This indicates a subdirectory
            subdir_name = rel_path.parts[0]
            if subdir_name not in direct_children:
                direct_children[subdir_name] = None  # Mark as directory

    # Process direct children
    for name, oid in direct_children.items():
        if oid is not None:
            # It's a file
            entries.append(("100644", name, oid))
        else:
            # It's a directory - recursively build its tree
            subdir_path = base_path / name if base_path != Path("") else Path(name)
            sub_tree = build_tree(repo_root, index, subdir_path)
            sub_oid = sub_tree.oid()  # Tree stores itself on creation
            entries.append(("040000", name, sub_oid))

    # Sort entries by name (like Git does)
    entries.sort(key=lambda x: x[1])
    return Tree(entries)
