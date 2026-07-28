from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from domain.skill_registry import SkillSource


class SourcePort(Protocol):
    """Materializes a registry source to a local working tree and reads from it.

    `materialize` turns a registry entry into a working-tree root (a git source
    into a durable per-source cache checked out at its `ref`; a local source read
    in place at its `uri`). The read side — `walk` and `read_bytes` — is uniform
    across source types: both operate on relative paths under the returned root,
    so downstream discovery and install consume `git` and `local` sources the same
    way. A missing path yields no files rather than an error.
    """

    def materialize(self, entry: SkillSource) -> Path: ...

    def walk(self, root: Path, subpath: Path) -> Iterable[Path]:
        """Yield every file under `root/subpath`, as paths relative to `root`."""
        ...

    def read_bytes(self, root: Path, path: Path) -> bytes: ...
