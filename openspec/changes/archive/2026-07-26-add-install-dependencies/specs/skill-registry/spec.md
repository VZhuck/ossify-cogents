## MODIFIED Requirements

### Requirement: Registry entry schema
The system SHALL model a registry entry as `id`, `name`, `description`, `source-type` (`git` or `local`), a `source` object shaped by `source-type`, a `discovery` field, and an `install` field: a `git` entry's `source` SHALL have `uri` and `ref` (defaulting to `main` when omitted); a `local` entry's `source` SHALL have only `uri` (no `ref`). `discovery` SHALL be a list of discovery-strategy ids, defaulting to an empty list when omitted; an empty `discovery` list is valid and represents an entry with no declared discovery strategy. `install` SHALL be the install block (see the `capability-install` spec); it is always present and defaults to an empty block when omitted, and an empty `install` selects nothing for installation.

#### Scenario: Git entry defaults ref
- **WHEN** a `git` registry entry is created without an explicit `source.ref`
- **THEN** the system SHALL set `source.ref` to `"main"`

#### Scenario: Local entry has no ref concept
- **WHEN** a `local` registry entry is parsed
- **THEN** the system SHALL NOT require or accept a `source.ref` field on that entry

#### Scenario: Discovery defaults to an empty list
- **WHEN** a registry entry is parsed without a `discovery` field
- **THEN** the system SHALL set `discovery` to an empty list and SHALL NOT treat the entry as invalid

#### Scenario: Install defaults to an empty block
- **WHEN** a registry entry is parsed without an `install` field
- **THEN** the system SHALL set `install` to an empty block that selects nothing and SHALL NOT treat the entry as invalid

## ADDED Requirements

### Requirement: Registry update preserves the `install` block
The system SHALL preserve an existing entry's `install` block across a registry add/update operation. An update SHALL patch the stored entry — overlaying only the identity, source, and discovery fields it is changing — rather than reconstructing the entry from operation inputs, so that a hand-authored `install` block is never dropped or overwritten unless the operation explicitly targets it.

#### Scenario: Updating source metadata keeps install intact
- **WHEN** an existing registry entry carries an `install` block and a registry update changes its `source.ref` without supplying an `install` value
- **THEN** the system SHALL retain the original `install` block unchanged in the updated entry
