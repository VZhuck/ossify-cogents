# project-skeleton

## Purpose

Initial project structure set up

## Requirements

### Requirement: Hexagonal package layout
The system SHALL organize `src/` into the following top-level packages, each its own installed package with a single responsibility, and no wrapping package folder grouping them: `domain/` (pydantic models and errors), `ports_in/` (interfaces implemented by `application/` and called by entrypoints), `ports_out/` (interfaces implemented by `adapters/` and called by `application/`), `application/` (use cases), `adapters/` (concrete implementations of `ports_out`; subpackages such as `sources/`, `targets/`, `persistence/` are added by the feature work that needs them, not pre-scaffolded), `cli/` (Typer entrypoint), `tui/` (Textual entrypoint placeholder), and `container.py` (dependency-injector wiring).

#### Scenario: Package layout exists
- **WHEN** the repository is inspected after this change
- **THEN** `src/domain/`, `src/ports_in/`, `src/ports_out/`, `src/application/`, `src/adapters/`, `src/cli/`, `src/tui/`, and `src/container.py` all exist directly under `src/`

#### Scenario: Adapters package has no concrete adapters or subpackages yet
- **WHEN** `src/adapters/` is inspected
- **THEN** it contains only `__init__.py`
- **THEN** no `sources/`, `targets/`, `persistence/`, or other adapter subpackage exists until a feature adds one

### Requirement: Import boundaries are enforced by tooling
The system SHALL enforce, via `import-linter` configuration, that: `domain` imports nothing else from this project; `ports_in` and `ports_out` import only from `domain`; and `application`, `adapters`, `cli`, and `tui` never import one another directly.

#### Scenario: Boundary violation fails the lint check
- **WHEN** a developer adds an import from `cli/` directly into `application/` (bypassing `ports_in/`)
- **THEN** running the import-linter check SHALL fail with a contract violation identifying the offending import

#### Scenario: Compliant code passes the lint check
- **WHEN** the skeleton is implemented as specified, with no cross-ring-1 imports
- **THEN** running the import-linter check SHALL pass with no violations

### Requirement: Only container.py wires implementations together
The system SHALL ensure `container.py` is the only module that imports both `application/` and `adapters/` in order to construct and wire concrete use-case and adapter instances via `dependency-injector`.

#### Scenario: Entrypoints obtain wired use cases through the container
- **WHEN** `cli/` needs to invoke a use case
- **THEN** it SHALL obtain the wired use case instance via `container.py`, not by importing or constructing an `application/` class directly

### Requirement: Package builds and installs via uv
The system SHALL be buildable and installable as distribution `ossify-cogents` using `uv`, with each top-level layer package (`domain`, `ports_in`, `ports_out`, `application`, `adapters`, `cli`, `tui`) and the `container` module included in the build from their flat locations under `src/`.

#### Scenario: Editable install succeeds
- **WHEN** a developer runs `uv sync` in the repository
- **THEN** every layer package SHALL be importable (e.g. `import domain`, `import cli`) and the `ossify-cogents` console script SHALL be available on PATH

#### Scenario: Wheel build succeeds
- **WHEN** a developer runs `uv build`
- **THEN** a wheel and sdist SHALL be produced containing all layer packages and `container.py`, with no build errors

### Requirement: Public package surface via `__init__.py` re-exports
The system SHALL expose each package's public API through re-exports in its `__init__.py`, so consumers import from the package root (e.g. `from ports_out import SourcePort`) rather than from internal submodules.

#### Scenario: Consumer imports from package root
- **WHEN** `application/` needs a type defined in `ports_out/`
- **THEN** it SHALL import it from `ports_out`, not from a submodule path such as `ports_out._source_port`
