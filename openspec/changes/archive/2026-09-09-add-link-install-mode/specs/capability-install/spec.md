## MODIFIED Requirements

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
