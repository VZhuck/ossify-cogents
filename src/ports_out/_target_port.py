from collections.abc import Iterable
from pathlib import Path
from typing import Protocol


class TargetPort(Protocol):
    """Action-aware writes into a target folder, rooted at construction.

    Layout knowledge (where a canonical item lands per platform) lives in
    `application/`; this port only executes concrete write actions at a path
    relative to the target root. Action *support* is a per-adapter capability:
    an adapter MAY raise `domain.errors.UnsupportedTargetActionError` for an
    operation it cannot perform (e.g. `merge` on a non-JSON target).
    """

    def exists(self, path: Path) -> bool: ...

    def is_symlink(self, path: Path) -> bool:
        """Whether `path` is a symbolic link — checked without following it."""
        ...

    def walk(self, path: Path) -> Iterable[Path]:
        """Yield every file under `path`, as paths relative to `path`."""
        ...

    def read(self, path: Path) -> bytes:
        """Read the bytes already at `path` under the target root."""
        ...

    def children(self, path: Path) -> Iterable[Path]:
        """Yield the immediate children of `path`, as paths relative to the target root."""
        ...

    def link_target(self, path: Path) -> Path | None:
        """The resolved absolute target of the symbolic link at `path`, else `None`."""
        ...

    def create_if_absent(self, path: Path, data: bytes) -> None:
        """`init` semantics: write `data` only when `path` does not yet exist."""
        ...

    def override(self, path: Path, data: bytes) -> None:
        """`replace` semantics: overwrite `path` wholesale."""
        ...

    def merge(self, path: Path, data: bytes) -> None:
        """`json_merge` semantics: deep-merge `data` into the existing target JSON."""
        ...

    def remove(self, path: Path) -> None:
        """Delete `path` (file or directory tree) under the target root; no-op if absent.

        A symbolic link is unlinked, never followed: removing a link must not touch
        what it points at.
        """
        ...

    def link(self, path: Path, source: Path, *, is_directory: bool) -> None:
        """Point `path` at `source` as a symbolic link, replacing what is there.

        `path` is relative to the target root, relaxing this port's usual invariant
        for `source`: that is an already-resolved link target — relative to `path`'s
        parent for an in-workspace source, absolute otherwise — and is written
        verbatim. `is_directory` is the item's *discovered* shape, which decides
        whether a directory or file link is created. Callers are responsible for
        deciding that the existing destination may be replaced. An adapter that
        cannot link raises `domain.errors.UnsupportedTargetActionError`.
        """
        ...
