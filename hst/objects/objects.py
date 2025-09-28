from __future__ import annotations
import abc
import hashlib
import zlib
from typing import List, Tuple


class Object(abc.ABC):
    """Abstract base class for all stored objects.

    Defines the common interface for objects, including serialization,
    deserialization, computing an object ID, and compression.
    """

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


class Blob(Object):
    """Blob (Binary Large Object): stores the raw content of a file.

    A blob represents the file’s data as a sequence of bytes, without
    metadata such as the filename or file permissions.
    """

    def __init__(self, data: bytes):
        self.data = data

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
    parent commits, author and committer information, and a commit message.
    """

    def __init__(
        self, tree: str, parents: List[str], author: str, committer: str, message: str
    ):
        self.tree = tree
        self.parents = parents
        self.author = author
        self.committer = committer
        self.message = message

    @property
    def type(self) -> str:
        return "commit"

    def serialize(self) -> bytes:
        lines = [f"tree {self.tree}"]
        for p in self.parents:
            lines.append(f"parent {p}")
        lines.append(f"author {self.author}")
        lines.append(f"committer {self.committer}")
        lines.append("")  # blank line before message
        lines.append(self.message)
        return "\n".join(lines).encode()

    @classmethod
    def deserialize(cls, data: bytes) -> Commit:
        text = data.decode()
        headers, message = text.split("\n\n", 1)
        tree = ""
        parents = []
        author = ""
        committer = ""
        for line in headers.split("\n"):
            if line.startswith("tree "):
                tree = line[5:]
            elif line.startswith("parent "):
                parents.append(line[7:])
            elif line.startswith("author "):
                author = line[7:]
            elif line.startswith("committer "):
                committer = line[10:]
        return cls(tree, parents, author, committer, message.strip())


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
