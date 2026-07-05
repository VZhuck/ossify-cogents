"""Entry point for the ossify CLI.

Placeholder only — no commands are implemented yet. This exists so the
package is runnable end-to-end (`uv run ossify`) while the engine
(config/lockfile/resolver/installer) and real subcommands are built out.
"""

from __future__ import annotations

import typer

app = typer.Typer(name="ossify", help="Package manager for AI coding-assistant skills and agents.")


@app.command()
def status() -> None:
    """Placeholder command — real functionality is not implemented yet."""
    print("ossify: skeleton only, no commands implemented yet")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
