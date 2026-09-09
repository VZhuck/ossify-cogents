"""Implements `ports_out.SourcePort` for `local` sources — read the folder in place."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from adapters.sources import _working_tree
from domain.errors import SourceFetchError
from domain.skill_registry import SkillSource


class LocalSourceAdapter:
    """Materializes a `local` source to its `uri` path as-is, without copying."""

    def materialize(self, entry: SkillSource) -> Path:
        path = Path(entry.source.uri).expanduser()
        if not path.exists():
            # Without this the walk simply yields nothing and the entry installs
            # zero items with a zero exit — a silent no-op for what is really a
            # broken config, and a destructive one under `mode: link`, where the
            # run would prune the links the missing source used to own.
            raise SourceFetchError(
                f"local source {entry.id!r} points at a path that does not exist: {path}"
            )
        return path

    def walk(self, root: Path, subpath: Path) -> Iterable[Path]:
        return _working_tree.walk(root, subpath)

    def read_bytes(self, root: Path, path: Path) -> bytes:
        return _working_tree.read_bytes(root, path)
