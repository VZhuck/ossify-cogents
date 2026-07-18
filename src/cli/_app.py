from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from cli._config import config_app
from cli._registry import registry_app
from container import Container
from ports_in import VersionPort

app = typer.Typer(name="ossify-cogents", no_args_is_help=True)
app.add_typer(registry_app, name="registry")
app.add_typer(config_app, name="config")
console = Console()

_WORKSPACE_OPTION = typer.Option(
    None,
    "--workspace",
    "-ws",
    help="Explicit workspace root, overriding auto-detection of .git/ossify-cogents.json.",
)


def _version_callback(show_version: bool) -> None:
    if not show_version:
        return
    container = Container()
    version_port: VersionPort = container.get_version_use_case()
    console.print(version_port.get_version())
    raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the ossify-cogents version and exit.",
    ),
    workspace: Path | None = _WORKSPACE_OPTION,
) -> None:
    """ossify-cogents: manage, version, and synchronize AI coding agent configurations."""
    ctx.obj = {"workspace": workspace}
