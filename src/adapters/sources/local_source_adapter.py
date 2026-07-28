"""Implements `ports_out.SourcePort` for `local` sources — read the folder in place."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from adapters.sources import _working_tree
from domain.skill_registry import SkillSource


class LocalSourceAdapter:
    """Materializes a `local` source to its `uri` path as-is, without copying."""

    def materialize(self, entry: SkillSource) -> Path:
        return Path(entry.source.uri).expanduser()

    def walk(self, root: Path, subpath: Path) -> Iterable[Path]:
        return _working_tree.walk(root, subpath)

    def read_bytes(self, root: Path, path: Path) -> bytes:
        return _working_tree.read_bytes(root, path)
