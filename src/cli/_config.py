"""`ossify-cogents config` sub-app: `verify`."""

from __future__ import annotations

import typer
from rich.console import Console

from cli._workspace import resolve_root
from container import Container
from domain.errors import OssifyError
from ports_in import OssifyConfigPort

config_app = typer.Typer(name="config", help="Validate the ossify-cogents.json config file.")
console = Console()


@config_app.command("verify")
def verify(ctx: typer.Context) -> None:
    """Validate the config file's registry section against the schema."""
    root = resolve_root(ctx)
    config_port: OssifyConfigPort = Container().ossify_config_use_case()

    try:
        config_port.verify(root)
    except OssifyError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    console.print("[green]Config is valid.[/green]")
