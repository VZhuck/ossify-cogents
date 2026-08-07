# Development

For contributing to `ossify-cogents` itself — running from source instead of installing the published tool.

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/VZhuck/ossify-cogents.git
cd ossify-cogents
uv sync
```

This creates a local virtual environment with the project and its dependencies (including the `dev` group: `ruff`, `mypy`, `pytest`, `import-linter`).

## Running the CLI from source

```bash
uv run ossify-cogents --version
```

If the virtual environment is already activated (`source .venv/bin/activate`), drop the `uv run` prefix:

```bash
ossify-cogents --version
```

## Quality gate

```bash
uv run pytest          # tests
uv run ruff check .    # lint
uv run mypy src        # type check (strict)
uv run lint-imports     # architecture boundary rules (see .claude/rules/architecture.md)
```

A pre-commit hook also regenerates `schema/v1.json` from the domain models and fails the commit on drift — if you change a config-section model, update `scripts/generate_schema.py` accordingly.

See `CLAUDE.md` and `.claude/rules/` for the project's architecture and style conventions.
