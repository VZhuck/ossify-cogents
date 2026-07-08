## Why

`ossify-cogents` is currently an empty repository (README + CLAUDE.md only, no `pyproject.toml`, no source). Every future capability (source adapters, target adapters, sync/status/audit, TUI) will be built on whatever package layout is chosen first, and the project already commits to `dependency-injector` for wiring adapters to use cases — a decision that only pays off inside a ports-and-adapters style layout. Establishing that layout now, before any real business logic exists, means the first real feature (a source or target adapter) lands in a structure built for it instead of forcing a mid-project restructure. The only user-visible behavior needed to prove the skeleton end-to-end is a `--version` command.

## What Changes

- Initialize the Python package (`uv`-managed, src-layout) with `pyproject.toml`, build backend, and dev tooling (ruff, mypy, pytest, import-linter).
- Establish the hexagonal package layout directly under `src/` (no wrapping package folder): `domain/`, `ports_in/`, `ports_out/`, `application/`, `adapters/`, `cli/`, `tui/` (skeleton only), `container.py` — each layer is its own top-level installed package.
- Add `import-linter` contracts enforcing the layer boundaries (domain has no outward deps; ports depend only on domain; application/adapters/cli/tui are mutually independent and only wired together via `container.py`), wired into local dev workflow.
- Implement one vertical slice end-to-end through every layer: a `--version` CLI flag, proving `cli/ → ports_in/ → application/ → domain/` actually works as a pattern, wired via `container.py`.
- Add packaging conventions: distribution name `ossify-cogents`, Typer `app` exported from `cli/__init__.py`, `[project.scripts] ossify-cogents = "cli:app"` entry point, version sourced from package metadata (no duplicated version string). No `python -m` module execution — there is no unifying package to host a `__main__.py` under the flat layout, so the console script is the sole supported entry point.
- Update `CLAUDE.md`'s "Architecture" section (currently "TBD") with the finalized layout and a pointer to the detailed rules.
- Add `.claude/rules/architecture.md` (package responsibilities, import boundary rules, packaging conventions) and `.claude/rules/python_style.md` (typing, pydantic, Protocol-based ports, DI conventions) to guide future code generation.

**Explicitly out of scope for this change**: real source/target adapters (git, local folder, Claude/Copilot/Cursor/Windsurf layouts), the `sync`/`status`/`audit` use cases, config/lock file parsing, and the Textual TUI implementation. Those are future features that will land inside this skeleton, not part of establishing it.

## Capabilities

### New Capabilities
- `project-skeleton`: the hexagonal package layout, import-boundary enforcement (import-linter), and packaging/build conventions (uv, entry points, versioning) that every future capability will build inside.
- `cli-version`: the `--version` flag/command, implemented as a full vertical slice through the skeleton (cli → ports_in → application → domain), serving as the skeleton's proof-of-concept.

### Modified Capabilities
- None — this is a greenfield repository with no existing specs.

## Impact

- **New files**: `pyproject.toml`, `src/{domain,ports_in,ports_out,application,adapters,cli,tui}/**`, `src/container.py`, `tests/**`, import-linter config, `.claude/rules/architecture.md`, `.claude/rules/python_style.md`.
- **Modified files**: `CLAUDE.md` (Architecture section).
- **New dev dependencies**: `dependency-injector`, `import-linter` (alongside already-mandated typer, rich, pydantic, ruff, mypy, pytest).
- **No runtime behavior changes** beyond the new `--version` command, since no prior CLI exists.
