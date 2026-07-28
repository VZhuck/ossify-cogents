"""`ossify-cogents install`: fetch and install selected capabilities into the repo."""

from __future__ import annotations

import typer
from rich.console import Console

from cli._workspace import resolve_root
from container import Container
from domain.errors import OssifyError
from ports_in import InstallPort

console = Console()


def install(ctx: typer.Context) -> None:
    """Install selected capabilities from every registry source into the workspace."""
    root = resolve_root(ctx)
    install_port: InstallPort = Container().install_use_case()

    try:
        report = install_port.install(root)
    except OssifyError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    for entry in report.entries:
        console.print(f"[bold]{entry.entry_id}[/bold]: {len(entry.installed)} item(s) installed")
        for line in entry.installed:
            console.print(f"  [green]+[/green] {line}")
        for warning in entry.warnings:
            console.print(f"  [yellow]![/yellow] {warning}")
