from __future__ import annotations
import abc
from pathlib import Path
import hashlib
import zlib
import time
from typing import List, Tuple
from hst.repo import REPO_DIR, find_repo_root


class Object(abc.ABC):
    """Abstract base class for all stored objects.

    Defines the common interface for objects, including serialization,
    deserialization, computing an object ID, and compression.
    """

    def __init__(self):
        # Persist the object in the repo after subclass init is done
        repo_root = find_repo_root(Path.cwd())
        self._store(repo_root)

    @property
    @abc.abstractmethod
    def type(self) -> str:
        """Return the object type: blob, tree, commit, or tag."""
        pass

    @abc.abstractmethod
    def serialize(self) -> bytes:
        """Return the raw content bytes (excluding header)."""
        pass

    @classmethod
    @abc.abstractmethod
    def deserialize(cls, data: bytes) -> Object:
        """Construct an object from raw content bytes."""
        pass

    def oid(self) -> str:
        """Compute the SHA-1 identifier of this object."""
        content = self.serialize()
        header = f"{self.type} {len(content)}".encode() + b"\x00"
        store = header + content
        return hashlib.sha1(store).hexdigest()

    def compressed(self) -> bytes:
        """Return the zlib-compressed form (header + content)."""
        content = self.serialize()
        header = f"{self.type} {len(content)}".encode() + b"\x00"
        store = header + content
        return zlib.compress(store)

    def _store(self, repo_root: Path):
        """Write this object into .hst/objects/ by its oid if not already stored."""
        oid = self.oid()
        obj_path = repo_root / REPO_DIR / "objects" / oid[:2] / oid[2:]
        if not obj_path.exists():
            obj_path.parent.mkdir(parents=True, exist_ok=True)
            with open(obj_path, "wb") as f:
                f.write(self.compressed())


class Blob(Object):
    """Blob (Binary Large Object): stores the raw content of a file.

    A blob represents the file’s data as a sequence of bytes, without
    metadata such as the filename or file permissions.
    """

    def __init__(self, data: bytes):
        self.data = data
        super().__init__()

    @property
    def type(self) -> str:
        return "blob"

    def serialize(self) -> bytes:
        return self.data

    @classmethod
    def deserialize(cls, data: bytes) -> Blob:
        return cls(data)


class Tree(Object):
    """Tree object: directory listing of blobs and other trees.

    Each entry maps a name to an object ID (blob or tree) and includes
    the file mode. Trees represent the hierarchical structure of directories.
    """

    def __init__(self, entries: List[Tuple[str, str, str]]):
        """
        entries: list of (mode, name, oid) tuples
        - mode: file mode string (e.g., "100644", "040000")
        - name: filename or directory name
        - oid: SHA-1 hex of the referenced object
        """
        self.entries = entries
        super().__init__()

    @property
    def type(self) -> str:
        return "tree"

    def serialize(self) -> bytes:
        out = b""
        for mode, name, oid in self.entries:
            out += f"{mode} {name}".encode() + b"\x00"
            out += bytes.fromhex(oid)
        return out

    @classmethod
    def deserialize(cls, data: bytes) -> Tree:
        entries = []
        i = 0
        while i < len(data):
            j = data.find(b"\x00", i)
            mode_name = data[i:j].decode()
            mode, name = mode_name.split(" ", 1)
            oid = data[j + 1 : j + 21].hex()
            entries.append((mode, name, oid))
            i = j + 21
        return cls(entries)


class Commit(Object):
    """Commit object: represents a snapshot of the repository at a point in time.

    Stores a reference to a tree (root directory snapshot), zero or more
    parent commits, author and committer information, timestamps, and a commit message.
    """

    def __init__(
        self,
        tree: str,
        parents: list[str],
        author: str,
        committer: str,
        message: str,
        author_timestamp: int | None = None,
        committer_timestamp: int | None = None,
        author_tz: str = "-0000",
        committer_tz: str = "-0000",
    ):
        self.tree = tree
        self.parents = parents
        self.author = author
        self.committer = committer
        self.message = message
        self.author_timestamp = author_timestamp or int(time.time())
        self.committer_timestamp = committer_timestamp or int(time.time())
        self.author_tz = author_tz
        self.committer_tz = committer_tz

        super().__init__()

    @property
    def type(self) -> str:
        return "commit"

    def serialize(self) -> bytes:
        lines = [f"tree {self.tree}"]
        for p in self.parents:
            lines.append(f"parent {p}")
        lines.append(f"author {self.author} {self.author_timestamp} {self.author_tz}")
        lines.append(f"committer {self.committer} {self.committer_timestamp} {self.committer_tz}")
        lines.append("")  # blank line before message
        lines.append(self.message)
        return "\n".join(lines).encode()

    @classmethod
    def deserialize(cls, data: bytes) -> "Commit":
        text = data.decode()
        headers, message = text.split("\n\n", 1)
        tree = ""
        parents = []
        author = ""
        committer = ""
        author_timestamp = None
        committer_timestamp = None
        author_tz = "-0000"
        committer_tz = "-0000"

        for line in headers.split("\n"):
            if line.startswith("tree "):
                tree = line[5:]
            elif line.startswith("parent "):
                parents.append(line[7:])
            elif line.startswith("author "):
                parts = line[7:].rsplit(" ", 2)
                author = parts[0]
                author_timestamp = int(parts[1])
                author_tz = parts[2]
            elif line.startswith("committer "):
                parts = line[10:].rsplit(" ", 2)
                committer = parts[0]
                committer_timestamp = int(parts[1])
                committer_tz = parts[2]

        return cls(
            tree,
            parents,
            author,
            committer,
            message.strip(),
            author_timestamp,
            committer_timestamp,
            author_tz,
            committer_tz,
        )



class Tag(Object):
    """Annotated tag object: a labeled reference to another object.

    Stores the object ID being tagged, the type of that object, the tag
    name, tagger information, and a message. Tags can reference commits,
    trees, blobs, or even other tags.
    """

    def __init__(self, object_id: str, type_: str, tag: str, tagger: str, message: str):
        self.object_id = object_id
        self.object_type = type_
        self.tag = tag
        self.tagger = tagger
        self.message = message

        super().__init__()

    @property
    def type(self) -> str:
        return "tag"

    def serialize(self) -> bytes:
        lines = [
            f"object {self.object_id}",
            f"type {self.object_type}",
            f"tag {self.tag}",
            f"tagger {self.tagger}",
            "",
            self.message,
        ]
        return "\n".join(lines).encode()

    @classmethod
    def deserialize(cls, data: bytes) -> Tag:
        text = data.decode()
        headers, message = text.split("\n\n", 1)
        object_id = ""
        type_ = ""
        tag = ""
        tagger = ""
        for line in headers.split("\n"):
            if line.startswith("object "):
                object_id = line[7:]
            elif line.startswith("type "):
                type_ = line[5:]
            elif line.startswith("tag "):
                tag = line[4:]
            elif line.startswith("tagger "):
                tagger = line[7:]
        return cls(object_id, type_, tag, tagger, message.strip())
