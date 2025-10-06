from pathlib import Path
import zlib
from typing import Optional, Type
from hst.hst_objects import Object


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
