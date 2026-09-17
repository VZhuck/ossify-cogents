"""Implements `ports_out.TargetPort` — a filesystem writer rooted at a target folder.

This adapter is JSON-capable: `merge` deep-merges JSON payloads. It raises
`UnsupportedTargetActionError` when asked to `merge` content that is not valid
JSON, the one write action a plain filesystem target cannot perform.

It is also symlink-aware: destinations may themselves be links into a source tree
(`install.mode: link`), so every path operation here is careful to act on the link
rather than on what it points at.

Every mutation goes through `_filesystem`, which reports a denied write as an
actionable `TargetNotWritableError` and hands anything created back to the user
behind a `sudo` invocation. Installing must never require elevation, and an
elevated run must not leave capabilities its own user cannot edit.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from adapters import _filesystem
from domain.errors import LinkNotSupportedError, UnsupportedTargetActionError


def _is_junction(target: Path) -> bool:
    return target.is_junction()


def _is_link(target: Path) -> bool:
    return target.is_symlink() or _is_junction(target)


def _deep_merge(base: Any, overlay: Any) -> Any:
    """Recursively merge `overlay` into `base`; on any non-object conflict, `overlay` wins."""
    if isinstance(base, dict) and isinstance(overlay, dict):
        merged = dict(base)
        for key, value in overlay.items():
            merged[key] = _deep_merge(merged[key], value) if key in merged else value
        return merged
    return overlay


class FilesystemTargetAdapter:
    """Writes files under a fixed target root, using create-if-absent/override/merge semantics."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def exists(self, path: Path) -> bool:
        target = self._resolve(path)
        # A broken link still occupies the path, so `exists()` alone would miss it.
        return target.exists() or _is_link(target)

    def is_symlink(self, path: Path) -> bool:
        return _is_link(self._resolve(path))

    def walk(self, path: Path) -> Iterable[Path]:
        root = self._resolve(path)
        for absolute in self._walk_files(root):
            yield absolute.relative_to(root)

    def read(self, path: Path) -> bytes:
        return self._resolve(path).read_bytes()

    def children(self, path: Path) -> Iterable[Path]:
        root = self._resolve(path)
        if not root.is_dir() or _is_link(root):
            return
        for entry in sorted(root.iterdir()):
            yield path / entry.name

    def link_target(self, path: Path) -> Path | None:
        target = self._resolve(path)
        if not _is_link(target):
            return None
        return target.resolve()

    def _walk_files(self, root: Path) -> Iterable[Path]:
        """Files under `root`, never descending through a symlinked directory."""
        if _is_link(root) or not root.is_dir():
            return
        for entry in sorted(root.iterdir()):
            if _is_link(entry):
                continue
            if entry.is_dir():
                yield from self._walk_files(entry)
            elif entry.is_file():
                yield entry

    def create_if_absent(self, path: Path, data: bytes) -> None:
        target = self._resolve(path)
        if target.exists():
            return
        self._write(target, data)

    def override(self, path: Path, data: bytes) -> None:
        self._write(self._resolve(path), data)

    def merge(self, path: Path, data: bytes) -> None:
        target = self._resolve(path)
        incoming = self._parse_json(data)
        if target.exists():
            merged = _deep_merge(self._parse_json(target.read_bytes()), incoming)
        else:
            merged = incoming
        self._write(target, json.dumps(merged, indent=2).encode() + b"\n")

    def remove(self, path: Path) -> None:
        target = self._resolve(path)
        with _filesystem.writable(target):
            self._remove(target)

    def _remove(self, target: Path) -> None:
        # Order matters: `is_dir()` *follows* symlinks, so a link to a directory would
        # take the `rmtree` branch — which refuses a symlink and raises. Unlinking
        # first also keeps `remove()` from ever reaching through a link: `rmtree`
        # with `ignore_errors=True`, or any hand-rolled recursion, would delete the
        # source tree the link points at.
        if target.is_symlink():
            target.unlink()
        elif _is_junction(target):
            target.rmdir()
        elif target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink(missing_ok=True)

    def link(self, path: Path, source: Path, *, is_directory: bool) -> None:
        target = self._resolve(path)
        self.remove(path)
        _filesystem.mkdir(target.parent)
        # Not wrapped in `_filesystem.writable`: Windows reports "no symlink privilege"
        # as a permission errno, and translating it would preempt the junction fallback
        # below. `mkdir` above already guards the case a POSIX box can actually hit.
        try:
            os.symlink(source, target, target_is_directory=is_directory)
        except OSError as exc:
            if is_directory and self._junction(target, source):
                return
            if not is_directory and self._hardlink(target, source):
                return
            raise LinkNotSupportedError(
                f"cannot create a symbolic link at {path} -> {source}: {exc}. "
                "On Windows, enable Developer Mode or run as administrator; for file links, "
                "make sure source and destination are on the same drive so ossify can fall "
                "back to a hard link. Ossify does not fall back to copying, which would stop "
                "edits propagating back to the source."
            ) from exc
        _filesystem.deescalate(target)

    def _hardlink(self, target: Path, source: Path) -> bool:
        """File-link fallback: a hard link needs no Windows symlink privilege."""
        resolved = source if source.is_absolute() else (target.parent / source).resolve()
        try:
            os.link(resolved, target)
        except OSError:
            return False
        return True

    def _junction(self, target: Path, source: Path) -> bool:
        """Windows directory-link fallback: a junction needs no elevation. False elsewhere."""
        if os.name != "nt":
            return False
        resolved = source if source.is_absolute() else (target.parent / source).resolve()
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["cmd", "/c", "mklink", "/J", str(target), str(resolved)],  # noqa: S607
            capture_output=True,
            check=False,
        )
        return result.returncode == 0

    def _resolve(self, path: Path) -> Path:
        return self._root / path

    def _write(self, target: Path, data: bytes) -> None:
        _filesystem.mkdir(target.parent)
        with _filesystem.writable(target):
            target.write_bytes(data)
        _filesystem.deescalate(target)

    def _parse_json(self, data: bytes) -> Any:
        try:
            return json.loads(data)
        except json.JSONDecodeError as exc:
            raise UnsupportedTargetActionError("merge requires JSON content on both sides") from exc
