## Context

`ossify-cogents` is a greenfield repository: only `README.md` and `CLAUDE.md` exist, `src/` and `tests/` are empty. CLAUDE.md already mandates Python 3.12+/uv, Typer, Rich, pydantic, `dependency-injector` ("for wiring adapters to use cases"), ruff, mypy, and pytest — but its Architecture section is "TBD".

The domain has a known shape even though no code exists yet: the tool resolves *sources* (GitHub repos in standard or custom layout, local folders) and materializes them into *targets* (Claude Code, Copilot, Cursor, Windsurf, custom layouts), tracked via a config file and a commit/state-pinning lock file, with CLI now and a Textual TUI later reusing the same core logic. This is an N-sources × M-targets pluggable-adapter domain, and the `dependency-injector` mandate only makes sense against a design with an explicit adapter-wiring seam.

This design was arrived at through an extended exploration (`/opsx:explore`) comparing flat, layered, hexagonal, and vertical-slice styles, researching precedent (buckpal, cosmicpython's "Architecture Patterns with Python", pre-commit, DVC), and iterating on naming.

## Goals / Non-Goals

**Goals:**
- Establish a package layout that comfortably absorbs many future source/target adapters and CLI verbs without a rewrite, while staying appropriately light for a small-to-mid app today.
- Make the dependency direction machine-checked, not just documented, from day one.
- Prove the layout works end-to-end with the smallest possible real feature (`--version`).
- Leave clear, concrete conventions (in CLAUDE.md and `.claude/rules/`) so future feature work (real adapters, use cases) has an unambiguous place to land.

**Non-Goals:**
- Implementing any real source adapter (GitHub, local folder), target adapter (Claude/Copilot/Cursor/Windsurf), or the config/lock file format itself.
- Implementing the `sync`/`status`/`audit` use cases.
- Implementing the Textual TUI (only the empty `tui/` package + rule that it depends solely on `ports_in/` is established now).
- Optimizing for a scale (dozens of packages, plugin distribution, etc.) beyond "small-to-mid app" — several deliberately-simpler alternatives were chosen over more elaborate ones for this reason (see Decisions).

## Decisions

### 1. Ports-and-adapters (hexagonal), not flat/layered/vertical-slice

Four styles were compared. Flat (organic growth) was rejected because the sources×targets shape is already known — deferring structure discards information rather than avoiding premature decisions. Vertical-slice (organize by `sync/`, `status/`, `audit/` feature folders) was rejected because the pluggable axis (sources, targets) is *shared* across every feature, not owned by one; slicing by feature would force a `shared/` folder that quietly reinvents a worse-organized hexagon. Plain layered (`cli/core/adapters/infra`) was the closest runner-up but leaves the use-case/DI wiring implicit, under-using the mandated `dependency-injector` and inviting orchestration logic to leak into command bodies or a swelling services module.

Hexagonal wins because: (a) it's the only style where `dependency-injector` earns its place, (b) "add a source/target" becomes a one-file-plus-one-registration operation, matching the axis known to grow fastest, (c) it makes the later CLI→TUI transition additive rather than a rewrite.

### 2. Ports promoted to top level; no `core/` wrapper

Ports were initially sketched nested under a `core/` package alongside `application/` (mirroring the buckpal reference project's `application/port/in`, `application/port/out`, `application/service`). This was changed to promote `ports_in/` and `ports_out/` to top-level siblings of `domain/`, `application/`, `adapters/`, `cli/`, `tui/`.

Rationale: ports and domain are **ring 0** — shared contracts any package may depend on. `application/`, `adapters/`, `cli/`, `tui/` are **ring 1** — restricted implementations that must never import each other; only `container.py` is allowed to see more than one at once. Nesting ports inside `core/` alongside `application/` put a ring-0 contract and a ring-1 restricted implementation at the same visual depth, obscuring which was which. Promoting ports also removed a wrapper directory (`core/`) that, once ports left it, would have contained exactly one child (`application/`) — a smell for a small-app skeleton.

### 3. `ports_in` / `ports_out` naming (not `ports/in`, `ports/out`, `ports/driving`, `ports/driven`, or `ports/api`+`ports/spi`)

The most common reference naming (`port.in`, `port.out`, per the buckpal/Java convention) is not viable in Python: `in` is a reserved keyword and cannot be a package name. `driving`/`driven` (Cockburn's original terms) were considered but read as an easy-to-misread near-homophone pair. `api`/`spi` were rejected as Java-ecosystem jargon unlikely to be recognized without that background. `inbound`/`outbound` nested under one `ports/` package was the runner-up; flattened to `ports_in`/`ports_out` for one fewer level of nesting, consistent with the overall preference for a flatter tree at this project's size.

### 4. `adapters/`, not `infrastructure/`

"Infrastructure" (a DDD-flavored synonym) was considered and briefly adopted, then reverted to `adapters/` for internal consistency: the pattern is literally named "ports and adapters," and pairing `ports_in`/`ports_out` with `adapters/` reads more coherently than pairing them with `infrastructure/`.

### 5. Bare top-level `cli/` and `tui/`, not nested under `presentation/`, and not `host_cli`/`host_tui`

`presentation/cli/`, `presentation/tui/` added an extra nesting level for no benefit at this scale. `host_cli`/`host_tui` (a naming idea floated mid-exploration) was rejected: "host" doesn't pair with anything else in the layout (there's no "guest_" counterpart), reads as infrastructure-hosting/deployment terminology rather than "driving adapter," and — more importantly — minting a new top-level `host_X` package per future entrypoint (e.g. a future `host_api/`) doesn't scale as cleanly as it first appears, versus either a shared `entrypoints/` parent or (chosen here) plain bare names matching their tech: `cli/`, `tui/`.

### 6. No `core_` naming prefix on domain/ports/application

A `core_` prefix on `domain`, `ports_in`, `ports_out`, and `application` was proposed purely to visually cluster them in an alphabetically-sorted file tree. Rejected for two reasons: (a) applying it to all four would blur exactly the ring-0/ring-1 distinction decision #2 exists to make visible — `application` is ring-1 (restricted) and would look identical in kind to the three ring-0 contracts; (b) at 8 top-level entries, the whole tree fits on screen regardless of sort order — the grouping problem the prefix solves doesn't really exist yet at this project's size. The import-linter contracts (decision #7) are the actual enforcement mechanism for the ring-0/ring-1 boundary; naming doesn't need to carry that weight.

### 7. Import boundaries enforced by `import-linter`, not convention alone

Three contracts, chosen to match the two rings exactly:
- `domain` has no outward dependencies (forbidden contract).
- `ports_in`/`ports_out` depend only on `domain` (forbidden contract).
- `application`, `adapters`, `cli`, `tui` are mutually independent — none may import another (independence contract). `container.py` is a plain module, not a package under contract, so it alone is free to import across all of ring 1 to wire concrete adapters into use cases.

This was made explicit (rather than left as a documented convention) because the boundary most likely to erode silently over time is "ring 1 packages don't import each other" — it's the one contributors are most tempted to violate for a quick shortcut (e.g. a CLI command importing a use case class directly instead of going through `ports_in`).

### 8. `ports_in` kept despite being more debatable than `ports_out`

`ports_out` earns its keep unambiguously — it's what allows `SourcePort`/`TargetPort` to have multiple swappable implementations. `ports_in` is weaker justified in the same way, since each use case will likely have exactly one implementation; the interface's main value is letting `cli/`/`tui/` be tested against a fake use case without invoking real application logic. Kept because the CLI/TUI-over-one-core boundary is a first-class goal of this project (not a hypothetical), and consistency of "entrypoints only ever depend on ports_in, never on application" is easier for contributors to internalize as a blanket rule than a case-by-case exception.

### 9. Adapter subfolders (`sources/`, `targets/`, `persistence/`) are not pre-populated

The proposal explicitly defers creating any concrete source/target adapter file. Only the `adapters/` package (and empty `sources/`, `targets/`, `persistence/` subpackages, if needed to establish the shape) exists after this change — populating them is future feature work. Building the skeleton and the first adapter in the same change would make it hard to tell which parts of the structure are load-bearing versus incidental to that specific adapter.

### 10. True flat `src/` layout — no `src/ossify_cogents/` wrapper package

Every layer (`domain/`, `ports_in/`, `ports_out/`, `application/`, `adapters/`, `cli/`, `tui/`) sits directly under `src/` as its own top-level installed package, alongside a top-level `container.py` module. There is no unifying `src/ossify_cogents/` namespace folder.

This was raised as a correction: an earlier draft of this design introduced `src/ossify_cogents/` as a wrapper without flagging it as a new decision, contradicting every layout sketched during exploration (which always put layers directly under `src/`). Revisited explicitly, with the trade-off made plain:

- **Standard practice** for a `src/`-layout Python project is a single top-level package named after the distribution (`src/ossify_cogents/`), specifically to avoid import collisions — generic layer names like `domain`, `application`, `adapters`, `errors` are common enough that a truly flat layout risks colliding with an identically-named top-level package from some other installed dependency, with no namespace to disambiguate `import domain` from someone else's `domain`.
- **The flat option was chosen anyway**, prioritizing the shorter import paths (`from domain.models import ...` vs `from ossify_cogents.domain.models import ...`) and a `src/` tree that reads exactly as sketched throughout exploration, with no packaging concern intruding on the architectural picture. The collision risk is accepted as a known, deliberate trade-off (see Risks) rather than an oversight.
- **Consequence for packaging config**: `[tool.hatch.build.targets.wheel]` cannot rely on a single implicit package root: `packages` must list each top-level layer package explicitly (`src/domain`, `src/ports_in`, `src/ports_out`, `src/application`, `src/adapters`, `src/cli`, `src/tui`), and `container.py` — a loose top-level module, not a package — needs an explicit `force-include` entry to end up at the wheel root.
- **Consequence for the CLI entry point**: `[project.scripts] ossify-cogents = "cli:app"` (not `ossify_cogents.cli:app`), since `cli` is now a top-level package in its own right.
- **Consequence for module execution**: `python -m ossify_cogents` is no longer possible — there is no `ossify_cogents` package to host a `__main__.py`. The supported entry point is the installed `ossify-cogents` console script only; this change drops the module-execution requirement rather than substitute an awkward `python -m cli`.

### 11. Packaging conventions

- Distribution name `ossify-cogents` (PyPI-style hyphens). No single import package name — see decision #10 for the flat top-level layout this implies.
- Build backend: hatchling (uv's default), wheel `packages` listing each top-level layer directory individually plus a `force-include` for `container.py` (decision #10).
- `cli/__init__.py` re-exports the Typer `app` object as the package's public surface; `[project.scripts] ossify-cogents = "cli:app"`.
- Version sourced from installed package metadata (`importlib.metadata.version("ossify-cogents")`) as the single source of truth — never duplicated as a hardcoded string in source. This lookup is keyed by the PyPI-style distribution name, unaffected by the import-layout choice.
- Absolute imports for cross-package references (e.g. `from ports_out import SourcePort`); relative imports permitted only within the same package.
- Each package exposes its public surface via `__init__.py` re-exports; internal-only submodules get a leading underscore. This keeps import-linter contracts simple (contracts reference package names, not deep submodule paths) and gives every package one obvious import path for consumers.

## Risks / Trade-offs

- **[Risk] Day-one ceremony feels heavy for a single `--version` flag** (7 top-level packages + a container module for one trivial feature) → **Mitigation**: this is the accepted, deliberate trade-off per decision #1 — the alternative (flat, refactor later) was rejected because the multi-adapter shape is already known, not hypothetical. The `--version` slice itself stays minimal (no real ports_out/adapters involvement); only the skeleton exists in full.
- **[Risk] `ports_in` may turn out to be unused ceremony if no test ever exploits the fake-use-case seam** → **Mitigation**: decision #8 accepts this as a conscious, revisitable trade-off, not an oversight. If it proves to add no value after a couple of real use cases exist, dropping it later is a small, contained change (delete one package, update a handful of imports and one import-linter contract).
- **[Risk] import-linter contracts could be loosened or ignored under deadline pressure** → **Mitigation**: wire the check into CI (not just an optional local script) so it's a hard gate, not an opt-in habit.
- **[Risk] Naming (`ports_in`/`ports_out`/`ring 0`/`ring 1`) is unfamiliar vocabulary to a new contributor** → **Mitigation**: `.claude/rules/architecture.md` documents the layout and rules directly next to the code, and CLAUDE.md's Architecture section carries a summary + diagram, so onboarding doesn't depend on reading this design doc or the exploration history.
- **[Risk] Flat top-level package names (`domain`, `application`, `adapters`, `cli`, `errors`, ...) can collide with an identically-named package from another dependency in the same environment** → **Mitigation**: accepted per decision #10 given this project's dependency set is small and controlled; if a real collision is ever hit, the fix is scoped to renaming the one colliding package, not a structural rewrite. Worth re-checking this trade-off if the dependency list grows substantially.
- **[Risk] Flat layout makes the wheel build config more verbose** (explicit `packages` list + `force-include` for `container.py`, vs. one implicit package root) → **Mitigation**: this is a one-time packaging-config cost, documented in decision #10 and tasks.md; it doesn't recur as the app grows since new subpackages (e.g. `adapters/sources/`) nest inside already-declared top-level packages.

## Migration Plan

Not applicable — greenfield repository, no existing users, no data, no prior release to migrate from or roll back to. This change is additive: it creates files, it does not modify or remove any existing runtime behavior.

## Open Questions

- Should `import-linter` run as a pre-commit hook, a CI-only step, or both? (Design assumes both; final wiring is a tasks-level detail.)
- Should `adapters/sources/`, `adapters/targets/`, `adapters/persistence/` be created as empty packages now (to make the intended shape discoverable) or left entirely absent until the first real adapter lands? Leaning toward creating them empty (with just an `__init__.py`) since it costs nothing and makes the intended extension points visible — final call left to implementation.
