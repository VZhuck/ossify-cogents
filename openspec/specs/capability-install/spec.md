# capability-install Specification

## Purpose

Defines the declarative `install` model on a registry entry: its block schema (target platforms, fixed-category selection lists, and `by-pattern` entries), the fixed-category selection semantics, and the dynamic selection resolution policy applied at sync time.

> **Scope note — apply lives in `install-apply`.** This capability covers only
> the declarative `install` model, its selection semantics, and the dynamic
> resolution policy. The imperative *apply* layer — installing selected
> fixed-category items into target-platform layouts and mirroring `by-pattern`
> files with `init`/`replace`/`json_merge` action semantics — is specified in the
> `install-apply` capability and driven by the `ossify install` command. A
> declarative lock/`sync` reconciler (drift detection, SHA persistence) remains
> future work.

## Requirements

### Requirement: `install` block schema
The system SHALL model an optional `install` block on a registry entry with the following shape: `mode` (either `copy` or `link`, defaulting to `copy` when absent), `target-platforms` (a list of target-adapter ids, or `["*"]` meaning all supported target adapters), four fixed-category selection lists — `agents`, `skills`, `commands`, `rules` — each a list of `fnmatch` name-glob strings, and a `by-pattern` list whose entries are objects of `{ category, action }` where `action` is one of `init`, `replace`, or `json_merge`. All fields SHALL default such that an absent field selects nothing (empty list / absent block installs nothing) and an absent `mode` means `copy`. Field names SHALL serialize as kebab-case on disk (`target-platforms`, `by-pattern`).

`mode` SHALL be the only control over copy-versus-link behavior. The system SHALL NOT provide a command-line option that overrides an entry's `mode`.

#### Scenario: Install block parses fixed categories and by-pattern
- **WHEN** a registry entry declares `install` with `skills: ["code-review", "spec-*"]` and `by-pattern: [{ category: "vs-code-settings", action: "json_merge" }]`
- **THEN** the system SHALL parse the `skills` list as two name-globs and the `by-pattern` entry with `category` `"vs-code-settings"` and `action` `json_merge`

#### Scenario: Invalid by-pattern action rejected
- **WHEN** a registry entry declares a `by-pattern` entry whose `action` is not one of `init`, `replace`, or `json_merge`
- **THEN** the system SHALL reject the entry as a schema violation

#### Scenario: Absent mode defaults to copy
- **WHEN** an `install` block omits `mode`
- **THEN** the system SHALL treat the entry's mode as `copy`

#### Scenario: Mode parses as link
- **WHEN** an `install` block declares `"mode": "link"`
- **THEN** the system SHALL parse the entry's mode as `link`

#### Scenario: Unknown mode is rejected
- **WHEN** an `install` block declares a `mode` value other than `copy` or `link`
- **THEN** the system SHALL reject the entry as invalid

#### Scenario: Absent selection lists install nothing
- **WHEN** an `install` block omits `commands` or sets `commands: []`
- **THEN** the system SHALL select no commands for installation

### Requirement: Fixed-category selection semantics
The system SHALL treat each fixed-category list (`agents`, `skills`, `commands`, `rules`) as a set of `fnmatch` name-glob patterns matched against the ids of items discovered for that category. An absent category or an empty list SHALL select nothing. A pattern of `"*"` SHALL match every discovered id in that category.

#### Scenario: Absent and empty select nothing
- **WHEN** an `install` block omits `commands` or sets `commands: []`
- **THEN** the system SHALL select no commands for installation

#### Scenario: Glob selects the matching subset
- **WHEN** `skills: ["spec-*"]` is resolved against discovered skill ids `{ "spec-writer", "planner" }`
- **THEN** the system SHALL select `spec-writer` and SHALL NOT select `planner`

#### Scenario: Star selects all discovered ids
- **WHEN** `rules: ["*"]` is resolved against any set of discovered rule ids
- **THEN** the system SHALL select every discovered rule id

### Requirement: Dynamic selection resolution policy
The system SHALL resolve fixed-category selections against actually-discovered ids at sync time (after fetch and discovery). An **exact literal** pattern (one containing no glob metacharacters) that matches zero discovered ids SHALL be reported as an error. A pattern containing glob metacharacters that matches zero discovered ids SHALL be reported as a warning and SHALL NOT fail the operation.

#### Scenario: Exact literal matching nothing is an error
- **WHEN** `skills: ["code-review"]` is resolved and no discovered skill id equals `"code-review"`
- **THEN** the system SHALL report an error identifying the unmatched literal `code-review`

#### Scenario: Glob matching nothing is a warning
- **WHEN** `skills: ["spec-*"]` is resolved and no discovered skill id matches `"spec-*"`
- **THEN** the system SHALL report a warning and SHALL NOT fail the sync

### Requirement: Git branch refs resolve to the current upstream tip
When a registry entry's `source.ref` names a branch, the git source SHALL materialize that branch's current upstream commit on every `install` run, not a commit cached from a previous run. This applies only to branch refs; a `ref` that is a tag or a commit SHA is immutable by nature and SHALL continue to resolve to exactly that tag or commit.

#### Scenario: Branch ref reflects new upstream commits on repeat install
- **WHEN** a registry entry's `source.ref` is a branch (e.g. `main`) and the upstream remote has advanced past the last locally cached commit for that branch
- **THEN** running `install` SHALL fetch and materialize the branch's new upstream tip, and the resulting working tree SHALL match that tip rather than the previously cached commit

#### Scenario: Tag or commit-SHA ref is unaffected
- **WHEN** a registry entry's `source.ref` is a tag name or a full commit SHA
- **THEN** running `install` SHALL materialize exactly that tag or commit, regardless of any other branch activity on the remote
