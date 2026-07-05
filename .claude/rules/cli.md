# src/ossify/cli/

The Typer app and its subcommands — the user-facing entry point, nothing else.

- `app.py` defines the Typer `app` instance; each subcommand lives in its own file under
  `commands/` and imports `app` from `cli.app` to register itself.
- Commands only: parse args, call into `core/`, and print results (via Rich). No business
  logic, no direct filesystem/git calls here — if a command needs to compute something, that
  computation belongs in `core/` so it can be unit-tested without invoking the CLI.
- One command per file, named after the command (`add.py` -> `ossify add`).
- Errors surfaced to the user should be `typer.Exit(code=...)` with a clear Rich-formatted
  message, not raw stack traces.
