"""`ossify-cogents install`: fetch and install selected capabilities into the repo."""

from __future__ import annotations

import typer
from rich.console import Console

from cli._privileges import sudo_warning
from cli._workspace import resolve_root
from container import Container
from domain.errors import OssifyError
from domain.install_report import InstalledItem
from ports_in import InstallPort

console = Console()


def install(ctx: typer.Context) -> None:
    """Install selected capabilities from every registry source into the workspace."""
    root = resolve_root(ctx)
    elevated = sudo_warning()
    if elevated is not None:
        console.print(f"[yellow]![/yellow] {elevated}")
    install_port: InstallPort = Container().install_use_case()

    try:
        report = install_port.install(root)
    except OssifyError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    for entry in report.entries:
        console.print(f"[bold]{entry.entry_id}[/bold]: {len(entry.installed)} item(s) installed")
        for item in entry.installed:
            console.print(f"  {_render(item)}")
        for warning in entry.warnings:
            console.print(f"  [yellow]![/yellow] {warning}")

    for destination in report.pruned:
        console.print(f"[dim]-[/dim] {destination} (stale link removed)")
    for warning in report.warnings:
        console.print(f"[yellow]![/yellow] {warning}")


def _render(item: InstalledItem) -> str:
    """One installed item. Links show where they point — the shared state is the point."""
    label = f"{item.platform}:{item.category}:{item.item_id}"
    if item.mode == "link":
        return f"[cyan]=>[/cyan] {label} -> {item.destination} => {item.link_target}"
    return f"[green]+[/green] {label} -> {item.destination}"
