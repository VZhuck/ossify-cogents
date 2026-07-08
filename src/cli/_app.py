from __future__ import annotations

import typer
from rich.console import Console

from container import Container
from ports_in import VersionPort

app = typer.Typer(name="ossify-cogents", no_args_is_help=True)
console = Console()


def _version_callback(show_version: bool) -> None:
    if not show_version:
        return
    container = Container()
    version_port: VersionPort = container.get_version_use_case()
    console.print(version_port.get_version())
    raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the ossify-cogents version and exit.",
    ),
) -> None:
    """ossify-cogents: manage, version, and synchronize AI coding agent configurations."""
