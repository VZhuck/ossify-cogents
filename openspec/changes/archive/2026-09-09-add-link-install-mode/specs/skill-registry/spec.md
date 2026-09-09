## MODIFIED Requirements

### Requirement: Registry entry schema
The system SHALL model a registry entry as `id`, `name`, `description`, `source-type` (`git` or `local`), a `source` object shaped by `source-type`, a `discovery` field, and an `install` field: a `git` entry's `source` SHALL have `uri` and `ref` (defaulting to `main` when omitted); a `local` entry's `source` SHALL have only `uri` (no `ref`). `discovery` SHALL be a list of discovery-strategy ids, defaulting to an empty list when omitted; an empty `discovery` list is valid and represents an entry with no declared discovery strategy. `install` SHALL be the install block (see the `capability-install` spec); it is always present and defaults to an empty block when omitted, and an empty `install` selects nothing for installation.

An entry whose `install.mode` is `link` SHALL have `source-type` `local`. The system SHALL reject an entry declaring `install.mode: link` with `source-type: git` as an invalid registry entry, because a git source's working tree is refetched and reset on every install and edits made through a link into it would be destroyed without warning.

#### Scenario: Git entry defaults ref to main

- **WHEN** a registry entry declares `source-type: git` and omits `source.ref`
- **THEN** the system SHALL set `source.ref` to `main`

#### Scenario: Local entry rejects ref

- **WHEN** a registry entry declares `source-type: local` and sets `source.ref`
- **THEN** the system SHALL reject the entry as invalid

#### Scenario: Link mode on a local source is accepted

- **WHEN** a registry entry declares `source-type: local` and `install.mode: link`
- **THEN** the system SHALL accept the entry

#### Scenario: Link mode on a git source is rejected

- **WHEN** a registry entry declares `source-type: git` and `install.mode: link`
- **THEN** the system SHALL reject the entry as invalid, naming the entry id and the reason
- **AND** the rejection SHALL occur at parse time, so that offline config verification reports it without fetching any source

#### Scenario: Discovery defaults to an empty list

- **WHEN** a registry entry is parsed without a `discovery` field
- **THEN** the system SHALL set `discovery` to an empty list and SHALL NOT treat the entry as invalid

#### Scenario: Install defaults to an empty block

- **WHEN** a registry entry omits `install`
- **THEN** the system SHALL set `install` to an empty block that selects nothing and SHALL NOT treat the entry as invalid
