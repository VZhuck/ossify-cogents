"""Result of an `ossify install` run: what was written per entry, plus warnings.

Not a config section — this is a return DTO the CLI renders, so it is a plain
frozen `BaseModel` rather than a `ConfigModel`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class EntryInstallSummary(BaseModel):
    """Per-registry-entry outcome: the destinations written and any glob warnings."""

    model_config = ConfigDict(frozen=True)

    entry_id: str
    installed: list[str] = []
    warnings: list[str] = []


class InstallReport(BaseModel):
    """The whole-run summary across every registry entry."""

    model_config = ConfigDict(frozen=True)

    entries: list[EntryInstallSummary] = []
