"""Shared workspace-root resolution helper for CLI subcommands."""

from __future__ import annotations

from pathlib import Path

import typer

from container import Container


def resolve_root(ctx: typer.Context) -> Path:
    explicit: Path | None = ctx.obj.get("workspace") if ctx.obj else None
    return Container().workspace_locator().resolve(explicit)
