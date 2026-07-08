# ossify-cogents

`ossify-cogents` is a lightweight CLI/TUI tool designed to manage, version, and synchronize AI coding agent configurations (such as custom skills, agent prompts, system instructions, and rules) for your repository. The tool can work with different sources (git hub repos with standard or custom layout, local folders). Regardless chosen source the tool will support different target coding agents, such as Claude Code, GitHub Copilot, Cursor, Windsurf, or custom in-house setups, ossify-cogents keeps your AI capabilities structured, up-to-date, and ensure reproducible set up.

## Key Features
- The Configuration File (ossify-cogents.json / .yaml) is stored in the root of your repository, this file defines your upstream sources and how their files map to your project    
- The Lock File (ossify-cogents.lock.json) guarantees reproducible environments by locking the exact Git commit SHA or local folder state of each capability currently checked out in your workspace
- Provide out of the box source mapping used by claude and other repos; Also support custom mapping configuration to ensure flexability. 
- Support different tartget coding agent configs (e.g., .claude/, .github/, .cursor/)
- provides cli & TUI interfaces to status autid  & update: Inspect local drift, check for upstream updates, and sync changes to your repos


## Tech stack
- Python 3.12+, managed with **uv** (`uv sync`, `uv add`, `uv run`, `uv build`)
- **Typer** for the CLI, **Rich** for terminal output (a **Textual** TUI is a later phase)
- **pydantic** - enforces data validation and type constraints at runtime, using standard Python type hints, especially helpful for domain models.
- **dependency-injector** for wiring adapters to use cases (see "Dependency injection" below)
- **ruff** for lint + format, **mypy** for type checking, **pytest** for tests

## Architecture

ossify-cogents follows a ports-and-adapters (hexagonal) layout, sized for a small-to-mid app — no layer exists until it has a real inhabitant. Each layer is its own top-level package directly under `src/` (no wrapping package folder):

```
src/
├── domain/        # pydantic models + errors — no dependencies on the rest of the app
├── ports_in/      # interfaces the CLI/TUI call into (implemented by application/)
├── ports_out/     # interfaces application/ depends on (implemented by adapters/)
├── application/   # use cases (GetVersion, ...) — implements ports_in, depends on ports_out
├── adapters/      # sources/, targets/, persistence/ — concrete implementations of ports_out
├── cli/           # Typer entrypoint — depends only on ports_in
├── tui/           # Textual entrypoint (later phase) — depends only on ports_in
└── container.py   # the only module allowed to see application/ and adapters/ together and wire them
```

Dependency rules, at a glance:

- `domain/` - domain models, has no dependencies on other components
- `ports_in/`, `ports_out/` are shared contracts anyone may depend on.
- `application/`, `adapters/`, `cli/`, and `tui/` never import each other directly.
- New source/target/persistence backends only touch `adapters/*/` plus a registration in `container.py`.
- `container.py` is the only module allowed to import `application/` and `adapters/` together.
- There's no unifying `ossify_cogents` package name — each layer is its own top-level Python package. The CLI is invoked via the `ossify-cogents` console script only.

See `.claude/rules/architecture.md` for full per-package import rules and packaging conventions, and `.claude/rules/python_style.md` for code-level conventions (typing, pydantic model style, ports as `Protocol`, DI usage).
