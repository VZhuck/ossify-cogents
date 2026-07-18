"""`ossify-cogents registry` sub-app: `get` and `add`."""

from __future__ import annotations

from typing import Annotated, Literal, cast

import typer
from rich.console import Console
from rich.table import Table

from cli._workspace import resolve_root
from container import Container
from domain.errors import OssifyError
from ports_in import RegistryPort

registry_app = typer.Typer(name="registry", help="Manage the skill source registry.")
console = Console()


@registry_app.command("get")
def get(ctx: typer.Context) -> None:
    """List all registered skill sources."""
    root = resolve_root(ctx)
    registry_port: RegistryPort = Container().registry_use_case()

    try:
        entries = registry_port.get_all(root)
    except OssifyError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    table = Table("id", "name", "source-type", "source")
    for entry in entries:
        table.add_row(entry.id, entry.name, entry.source_type, entry.source.uri)
    console.print(table)


@registry_app.command("add")
def add(
    ctx: typer.Context,
    uri: Annotated[str | None, typer.Argument(help="Git URL or local path.")] = None,
    source_uri: Annotated[
        str | None, typer.Option("--source.uri", help="Alias for the positional uri.")
    ] = None,
    source_type: Annotated[
        str, typer.Option("--source-type", help="'git' or 'local'.")
    ] = "git",
    source_ref: Annotated[
        str | None, typer.Option("--source.ref", help="Git ref (git sources only).")
    ] = None,
    id_: Annotated[str | None, typer.Option("--id", help="Override the inferred id.")] = None,
    name: Annotated[str | None, typer.Option("--name", help="Override the inferred name.")] = None,
    description: Annotated[
        str | None, typer.Option("--description", help="Override the inferred description.")
    ] = None,
) -> None:
    """Add a new skill source to the registry."""
    if uri is not None and source_uri is not None and uri != source_uri:
        console.print("[red]uri and --source.uri disagree — pass only one.[/red]")
        raise typer.Exit(code=1)

    resolved_uri = uri or source_uri
    if resolved_uri is None:
        console.print("[red]Missing uri: pass it positionally or via --source.uri.[/red]")
        raise typer.Exit(code=1)

    if source_type not in ("git", "local"):
        console.print(f"[red]--source-type must be 'git' or 'local', got {source_type!r}.[/red]")
        raise typer.Exit(code=1)

    if source_type == "local" and source_ref is not None:
        console.print("[red]--source.ref is only valid with --source-type git.[/red]")
        raise typer.Exit(code=1)

    root = resolve_root(ctx)
    registry_port: RegistryPort = Container().registry_use_case()

    try:
        entry = registry_port.add(
            root,
            uri=resolved_uri,
            source_type=cast(Literal["git", "local"], source_type),
            ref=source_ref,
            id=id_,
            name=name,
            description=description,
        )
    except OssifyError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    console.print(f"Added [bold]{entry.id}[/bold] ({entry.source_type}: {entry.source.uri})")
