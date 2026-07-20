---
paths:
  - "/src/**"
description: Package layout and import boundaries for ossify-cogents. Applies to all files under ./src.
---

# Architecture Rules

ossify-cogents follows a ports-and-adapters (hexagonal) layout. These rules override generic organization habits when in conflict.

## Package layout

Every layer is its own top-level package directly under `src/` — there is no wrapping `ossify_cogents/` package folder.

- `domain/` — pydantic models, packaged built-in data, and domain errors only. No imports from any other package in this project. See the "Imports & packaging" exception below — unlike every other layer, `domain/` isn't re-exported through `__init__.py`.
- `ports_in/` — interfaces the CLI/TUI call into. Implemented by `application/`. Depends only on `domain/`.
- `ports_out/` — interfaces `application/` depends on (sources, targets, persistence). Implemented by `adapters/`. Depends only on `domain/`.
- `application/` — use cases (e.g. `GetVersion`, future `SyncCapabilities`, `CheckStatus`). Implements `ports_in/`, depends on `ports_out/` — never on `adapters/`, `cli/`, or `tui/` directly.
- `adapters/` — concrete implementations of `ports_out/` (`sources/`, `targets/`, `persistence/`). Never imported by `application/`, `cli/`, or `tui/` directly — only wired in via `container.py`.
- `cli/`, `tui/` — entrypoints. Depend only on `ports_in/` (and `domain/` for display types), never on `application/` or `adapters/` directly.
- `container.py` — the only module allowed to import `application/` and `adapters/` together and wire them via `dependency-injector`.

## Import boundary rule

`application/`, `adapters/`, `cli/`, and `tui/` must never import each other. If a CLI command needs use-case logic, it goes through `ports_in/` and the container — not a direct import of `application`. This is enforced by `import-linter` (`uv run lint-imports`, configured in `pyproject.toml` under `[tool.importlinter]`); a failing contract means the boundary was crossed, not that the tool is wrong.

## New adapters

Adding a new source, target, or persistence backend means: one new file under the matching `adapters/*/` subfolder implementing the relevant `ports_out` interface, plus one registration in `container.py`. It should never require changes to `application/`, `cli/`, or `tui/`.

## Imports & packaging

- **Flat layout, no unifying package name.** Each layer (`domain`, `ports_in`, `ports_out`, `application`, `adapters`, `cli`, `tui`) is installed as its own top-level Python package; `container.py` is a top-level module. This is a deliberate trade-off: it keeps import paths short (`from ports_out import SourcePort`) and matches the architecture diagrams exactly, at the cost of a real (if currently low) risk that a generic name like `domain` or `adapters` collides with an identically-named package from some other dependency. If that risk ever materializes, fix it by renaming the one colliding package — don't restructure everything else.
- Use absolute imports for cross-package references (e.g. `from ports_out import SourcePort`), not relative imports across package boundaries — relative imports (`from ._source_port import ...`) are fine only within the same package.
- Each package exposes its public surface via `__init__.py` re-exports (e.g. `application/__init__.py` re-exports `GetVersion`). Consumers import from the package, not from internal submodules (`from application import GetVersion`, not `from application._get_version import GetVersion`).
- Prefix internal-only submodules with a leading underscore (`_get_version.py`) if a package needs to split across files but keep them out of its public surface.
- **Exception: `domain/`.** `domain/__init__.py` stays a bare docstring, no re-exports — every consumer across every layer imports straight from the submodule (`from domain.skill_registry import SkillSource`, `from domain.errors import OssifyError`, `from domain.discovery import DiscoveryDefinition`, etc.), never `from domain import SkillSource`. This is deliberate and consistent, not an oversight — keep following it for new domain submodules rather than adding `domain/__init__.py` re-exports. The leading-underscore convention still applies within `domain/`, but for a different reason than elsewhere: `domain/_builtins.py` (packaged built-in discovery-strategy data) is underscored to mark it as data, not schema — regular domain models (`skill_registry.py`, `discovery.py`, `config_model.py`, `errors.py`, `ossify_config.py`) stay unprefixed since they're all imported directly by name anyway.
- Distribution name is `ossify-cogents` (PyPI-style hyphens); the console script `ossify-cogents = "cli:app"` is the only supported entry point — there is no `python -m` invocation, since no package is named after the distribution.
- Version is sourced from installed package metadata (`importlib.metadata.version("ossify-cogents")`), never hardcoded or duplicated in source.
- `pyproject.toml`'s `[tool.hatch.build.targets.wheel]` lists every top-level layer package explicitly under `packages`, plus a `force-include` for `container.py` (it's a loose module, not a package) — there's no single implicit package root to rely on. When adding a new top-level layer package, add it to this list.
- **`force-include`d loose modules are physically copied into the editable install, not symlinked.** After editing `container.py`, `uv run ossify-cogents ...` can run a stale copy from `.venv/lib/*/site-packages/container.py` until you `uv sync --reinstall-package ossify-cogents`. `pytest` never hits this — it runs against `src/` directly via `pythonpath` — so a green test suite doesn't guarantee the installed CLI reflects the latest `container.py`. Reinstall (or re-run `uv sync`) before manually exercising the CLI after touching `container.py`.
- **`scripts/` and `schema/` sit outside the layer architecture.** `scripts/generate_schema.py` is dev-only tooling (not part of any `src/` layer, not wheel-packaged) that composes the known config-section models into `schema/v1.json`, a generated-and-committed artifact validating `ossify-cogents.json` independently of the CLI. Both are deliberately absent from `[tool.hatch.build.targets.wheel]`. The `schema-drift` pre-commit hook (`.pre-commit-config.yaml`) regenerates and diffs `schema/v1.json` on every commit — if you add a new config-section model, wire it into `scripts/generate_schema.py`'s section map or the hook will fail on drift.
