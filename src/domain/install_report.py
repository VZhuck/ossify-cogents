"""Result of an `ossify install` run: what was written per entry, plus warnings.

Not a config section — this is a return DTO the CLI renders, so it is a plain
frozen `BaseModel` rather than a `ConfigModel`.

`installed` carries structured items rather than formatted strings so the CLI can
render copies and links differently without parsing its own output, and so a
future `status` can reuse the model instead of re-deriving it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict


class InstalledItem(BaseModel):
    """One written destination: what it is, where it landed, and how it was written.

    `link_target` is the path the symlink points at (relative to the destination's
    parent for an in-workspace source, absolute otherwise), and is `None` for a copy.
    """

    model_config = ConfigDict(frozen=True)

    platform: str
    category: str
    item_id: str
    destination: Path
    mode: Literal["copy", "link"]
    link_target: Path | None = None


class EntryInstallSummary(BaseModel):
    """Per-registry-entry outcome: the destinations written and any glob warnings."""

    model_config = ConfigDict(frozen=True)

    entry_id: str
    installed: list[InstalledItem] = []
    warnings: list[str] = []


class InstallReport(BaseModel):
    """The whole-run summary across every registry entry.

    `pruned` is run-wide rather than per-entry: a stale link is by definition one
    no entry claimed this run, so it cannot be attributed to one.
    """

    model_config = ConfigDict(frozen=True)

    entries: list[EntryInstallSummary] = []
    pruned: list[Path] = []
    warnings: list[str] = []
