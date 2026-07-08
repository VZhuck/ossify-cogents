# cli-version

## Purpose

Get CLI version which will define if tool need to be updated

## Requirements

### Requirement: `--version` flag reports the installed package version
The CLI SHALL support a `--version` flag on the root command that prints the installed `ossify-cogents` package version and exits successfully without executing any other command logic.

#### Scenario: User requests the version
- **WHEN** a user runs `ossify-cogents --version`
- **THEN** the CLI SHALL print the version string sourced from installed package metadata
- **THEN** the process SHALL exit with status code 0

#### Scenario: Version is not hardcoded
- **WHEN** the package version in `pyproject.toml` changes and the package is reinstalled
- **THEN** `ossify-cogents --version` SHALL reflect the updated version without any source code change

### Requirement: `--version` exercises the full skeleton vertical slice
The `--version` command SHALL be implemented as a complete pass through the skeleton's layers: `cli/` calls a `ports_in/` interface, implemented by an `application/` use case, which reads version information via `domain/`, wired together by `container.py`.

#### Scenario: Version flag routes through the use-case layer
- **WHEN** `ossify-cogents --version` is invoked
- **THEN** the CLI command SHALL NOT read package metadata directly; it SHALL call a use case through its `ports_in/` interface, obtained via `container.py`

### Requirement: `ossify-cogents` console script is the sole entry point
The system SHALL expose the CLI only via the installed `ossify-cogents` console script. `python -m` module execution is not supported, since the flat `src/` layout (no unifying top-level package — see design.md) leaves no package to host a `__main__.py`.

#### Scenario: Console script is available after install
- **WHEN** a developer runs `uv sync`
- **THEN** the `ossify-cogents` console script SHALL be available on PATH and `ossify-cogents --version` SHALL succeed
