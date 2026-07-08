## 1. Project & tooling bootstrap

- [x] 1.1 Create `pyproject.toml`: distribution name `ossify-cogents`, Python `>=3.12`, hatchling build backend
- [x] 1.2 Configure `[tool.hatch.build.targets.wheel] packages = ["src/domain", "src/ports_in", "src/ports_out", "src/application", "src/adapters", "src/cli", "src/tui"]` plus a `force-include` entry mapping `src/container.py` to `container.py` (flat layout — no single implicit package root; see design.md decision 10)
- [x] 1.3 Add runtime dependencies: `typer`, `rich`, `pydantic`, `dependency-injector`
- [x] 1.4 Add dev dependencies: `ruff`, `mypy`, `pytest`, `import-linter`
- [x] 1.5 Configure `[project.scripts] ossify-cogents = "cli:app"`
- [x] 1.6 Configure ruff and mypy (strict) settings in `pyproject.toml`
- [x] 1.7 Run `uv sync` and confirm the environment installs cleanly, with `domain`, `ports_in`, `ports_out`, `application`, `adapters`, `cli`, `tui`, and `container` all importable as top-level modules

## 2. Domain layer

- [x] 2.1 Create `src/domain/__init__.py`
- [x] 2.2 Create `src/domain/models.py` (empty/minimal for now — no models required by `--version`)
- [x] 2.3 Create `src/domain/errors.py` with a single `OssifyError` base exception

## 3. Ports layer

- [x] 3.1 Create `src/ports_in/__init__.py` and define a `GetVersionPort` `Protocol` (or equivalent minimal inbound port for the version use case)
- [x] 3.2 Create `src/ports_out/__init__.py` (empty for now — no outbound port is needed until the first real adapter; document the intended future contents per design.md)

## 4. Application layer

- [x] 4.1 Create `src/application/__init__.py`
- [x] 4.2 Implement a `GetVersion` use case implementing `GetVersionPort`, reading the version via `importlib.metadata.version("ossify-cogents")`

## 5. Adapters skeleton

- [x] 5.1 Create `src/adapters/__init__.py`
- [x] 5.2 Create empty `adapters/sources/__init__.py`, `adapters/targets/__init__.py`, `adapters/persistence/__init__.py` extension points (no concrete adapters)

## 6. Container wiring

- [x] 6.1 Create `src/container.py` using `dependency-injector` to provide a wired `GetVersion` use case behind `GetVersionPort`

## 7. CLI entrypoint

- [x] 7.1 Create `src/cli/__init__.py` re-exporting the Typer `app` object
- [x] 7.2 Implement the root Typer app with a `--version` eager callback that resolves `GetVersionPort` via the container, prints the version with Rich, and exits 0

## 8. TUI placeholder

- [x] 8.1 Create `src/tui/__init__.py` as an empty placeholder package (no implementation)

## 9. Import boundary enforcement

- [x] 9.1 Add `import-linter` configuration (`pyproject.toml` `[tool.importlinter]` or `.importlinter`) with the three contracts: `domain` has no outward deps; `ports_in`/`ports_out` depend only on `domain`; `application`/`adapters`/`cli`/`tui` are mutually independent
- [x] 9.2 Run `uv run lint-imports` and confirm all contracts pass against the implemented skeleton
- [x] 9.3 Wire the import-linter check into the local dev workflow (pre-commit hook and/or documented `uv run` step) so it runs alongside ruff/mypy

## 10. Tests

- [x] 10.1 Add `tests/cli/test_version.py` using Typer's `CliRunner` to verify `ossify-cogents --version` prints the version and exits 0
- [x] 10.2 Add a test verifying the CLI does not import `application` directly (or rely on the import-linter run in CI as the enforcement mechanism, per design.md decision 7)

## 11. Documentation

- [x] 11.1 Update `CLAUDE.md`'s "Architecture" section with the finalized flat folder diagram and layering summary, replacing "TBD"
- [x] 11.2 Create `.claude/rules/architecture.md` (paths scoped to `/src/**`) documenting package responsibilities, import boundary rules, and packaging/import conventions — including the flat-layout naming-collision trade-off from design.md decision 10
- [x] 11.3 Create `.claude/rules/python_style.md` (paths scoped to `/src/**`) documenting typing, pydantic, Protocol-based ports, and DI conventions

## 12. Verification

- [x] 12.1 Run `uv build` and confirm a wheel/sdist build cleanly, containing all layer packages and `container.py`
- [x] 12.2 Run `ossify-cogents --version` (installed console script) and confirm correct output
- [x] 12.3 Run the full test suite (`pytest`) and confirm all tests pass
- [x] 12.4 Run ruff, mypy, and import-linter and confirm all pass with no violations
