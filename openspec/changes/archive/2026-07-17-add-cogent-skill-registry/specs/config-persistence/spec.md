## ADDED Requirements

### Requirement: Workspace root resolution
The system SHALL resolve a single workspace root for every CLI invocation by: (1) using the path passed via the global `--workspace`/`-ws` option if given; otherwise (2) walking up from the current directory looking for a `.git` directory or an `ossify-cogents.json` file, whichever is found first at the closest directory; otherwise (3) using the current directory. This resolution SHALL always succeed and SHALL NOT raise an error regardless of whether a config file exists at the resolved root.

#### Scenario: Explicit workspace override
- **WHEN** a user runs any command with `--workspace ../some-repo`
- **THEN** the system SHALL use `../some-repo` as the workspace root without searching for `.git` or an existing config file

#### Scenario: Walk-up finds a git repository root
- **WHEN** no `--workspace` is given and a `.git` directory exists in an ancestor of the current directory before any `ossify-cogents.json` is found
- **THEN** the system SHALL use that ancestor directory as the workspace root

#### Scenario: Walk-up finds an existing config file
- **WHEN** no `--workspace` is given and an `ossify-cogents.json` file exists in an ancestor of the current directory before any `.git` directory is found
- **THEN** the system SHALL use that ancestor directory as the workspace root

#### Scenario: No markers found
- **WHEN** no `--workspace` is given and neither a `.git` directory nor an `ossify-cogents.json` file is found in any ancestor directory
- **THEN** the system SHALL use the current directory as the workspace root

### Requirement: Section-keyed, round-trip-safe config persistence
The system SHALL read and write `ossify-cogents.json` by top-level section key, such that writing one section preserves every other top-level key already present in the file, including keys not modeled by this codebase.

#### Scenario: Writing the registry section preserves unrelated sections
- **WHEN** `ossify-cogents.json` contains a top-level key not recognized by this codebase and the registry section is written via `registry add`
- **THEN** the resulting file SHALL retain the unrecognized key and its value unchanged

#### Scenario: Atomic write
- **WHEN** a config section is written
- **THEN** the write SHALL be atomic (via a temporary file and rename), such that a failure mid-write SHALL NOT leave a partially-written `ossify-cogents.json`
