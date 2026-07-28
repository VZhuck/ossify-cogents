"""Implements `ports_out.TargetPort` — a filesystem writer rooted at a target folder.

This adapter is JSON-capable: `merge` deep-merges JSON payloads. It raises
`UnsupportedTargetActionError` when asked to `merge` content that is not valid
JSON, the one write action a plain filesystem target cannot perform.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from domain.errors import UnsupportedTargetActionError


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
        return self._resolve(path).exists()

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
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink(missing_ok=True)

    def _resolve(self, path: Path) -> Path:
        return self._root / path

    def _write(self, target: Path, data: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def _parse_json(self, data: bytes) -> Any:
        try:
            return json.loads(data)
        except json.JSONDecodeError as exc:
            raise UnsupportedTargetActionError("merge requires JSON content on both sides") from exc
