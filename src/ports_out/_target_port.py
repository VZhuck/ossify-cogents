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

    def create_if_absent(self, path: Path, data: bytes) -> None:
        """`init` semantics: write `data` only when `path` does not yet exist."""
        ...

    def override(self, path: Path, data: bytes) -> None:
        """`replace` semantics: overwrite `path` wholesale."""
        ...

    def merge(self, path: Path, data: bytes) -> None:
        """`json_merge` semantics: deep-merge `data` into the existing target JSON."""
        ...
