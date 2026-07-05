# ossify-cogents

## What this is

`ossify` is a CLI/TUI package manager for AI coding-assistant configuration — skills, agents,
rules, and other artifacts for tools like Claude Code and GitHub Copilot. It works like npm/uv:
a human-edited config file declares dependencies (each pointing at a git source + ref), a
generated lock file records the exact resolved commit for each one, and `ossify update`
re-resolves refs against their remotes and rewrites the lock file when something moved.

Unlike a symlink-based dotfile manager, ossify always **copies** real files into a project —
it never creates symlinks. The lock file's git commit is what ties an installed copy back to
its upstream source.

## Status

Early scaffold. The CLI is a runnable placeholder only — no real commands exist yet.

## Tech stack

- Python 3.12+, managed with **uv** (`uv sync`, `uv add`, `uv run`, `uv build`)
- **Typer** for the CLI, **Rich** for terminal output (a **Textual** TUI is a later phase)
- **pydantic** for config/lock-file models
- Config file is YAML (human-edited), lock file is JSON (machine-generated)
- **ruff** for lint + format, **mypy** for type checking, **pytest** for tests

## Common commands

```bash
uv sync                    # install/update the dev environment
uv run ossify --help       # run the CLI
uv run pytest              # run tests
uv run ruff check --fix    # lint
uv run ruff format         # format
uv run mypy src            # type-check
```

## General conventions

- Prefer small, focused modules over large ones — one concern per file.
- Don't add abstractions, config options, or error handling for cases that can't happen yet.
  This is a young project; let real requirements drive structure, not speculation.
- Every new module should have type hints and pass `mypy --strict`.
- Favor clear names over comments; only comment on the non-obvious *why*.

## Folder-specific rules

@.claude/rules/cli.md
@.claude/rules/core.md
@.claude/rules/git.md
@.claude/rules/targets.md
@.claude/rules/utils.md
@.claude/rules/tests.md
