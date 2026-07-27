"""`ossify-cogents init`: scaffold a default ossify-cogents.json."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console

from cli._workspace import resolve_root
from container import Container
from domain.errors import OssifyError
from ports_in import InitPort

console = Console()


def init(
    ctx: typer.Context,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Overwrite an existing ossify-cogents.json with the default config.",
        ),
    ] = False,
) -> None:
    """Create a default ossify-cogents.json at the workspace root."""
    root = resolve_root(ctx)
    init_port: InitPort = Container().init_use_case()

    try:
        init_port.init(root, force=force)
    except OssifyError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    console.print(f"[green]Created ossify-cogents.json at {root}.[/green]")
