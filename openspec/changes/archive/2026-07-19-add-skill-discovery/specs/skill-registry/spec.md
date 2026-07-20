## MODIFIED Requirements

### Requirement: Registry entry schema
The system SHALL model a registry entry as `id`, `name`, `description`, `source-type` (`git` or `local`), a `source` object shaped by `source-type`, and a `discovery` field: a `git` entry's `source` SHALL have `uri` and `ref` (defaulting to `main` when omitted); a `local` entry's `source` SHALL have only `uri` (no `ref`). `discovery` SHALL be a list of discovery-strategy ids, defaulting to an empty list when omitted; an empty `discovery` list is valid and represents an entry with no declared discovery strategy.

#### Scenario: Git entry defaults ref
- **WHEN** a `git` registry entry is created without an explicit `source.ref`
- **THEN** the system SHALL set `source.ref` to `"main"`

#### Scenario: Local entry has no ref concept
- **WHEN** a `local` registry entry is parsed
- **THEN** the system SHALL NOT require or accept a `source.ref` field on that entry

#### Scenario: Discovery defaults to an empty list
- **WHEN** a registry entry is parsed without a `discovery` field
- **THEN** the system SHALL set `discovery` to an empty list and SHALL NOT treat the entry as invalid
