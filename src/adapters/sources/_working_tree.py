"""Shared read side over a materialized working-tree root.

Both the git and local source adapters expose the same walk/read behaviour over
a real filesystem root; only `materialize` differs between them. These free
functions hold the shared logic so neither adapter subclasses the other.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path


def walk(root: Path, subpath: Path) -> Iterator[Path]:
    """Yield every file under `root/subpath`, as paths relative to `root`, sorted.

    A subpath pointing at a single file yields just that file; a missing path
    yields nothing.
    """
    base = root / subpath
    if not base.exists():
        return
    if base.is_file():
        yield base.relative_to(root)
        return
    for path in sorted(base.rglob("*")):
        if path.is_file():
            yield path.relative_to(root)


def read_bytes(root: Path, path: Path) -> bytes:
    return (root / path).read_bytes()
