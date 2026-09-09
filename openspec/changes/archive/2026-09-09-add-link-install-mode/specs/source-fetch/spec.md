## MODIFIED Requirements

### Requirement: Materialize a registry source to a local working tree

The system SHALL materialize a registry entry into a local working-tree root before discovery and install read from it. A `git` entry SHALL be materialized into a durable per-source cache checked out at its `ref`. A `local` entry SHALL be materialized to its `uri` path in place, without copying, with `~` expanded.

Materializing a `local` entry whose path does not exist SHALL raise a source-fetch error naming the entry and the missing path. The system SHALL NOT treat a missing local source as an empty source.

#### Scenario: Local source materializes in place

- **WHEN** a `local` registry entry whose `uri` names an existing directory is materialized
- **THEN** the system SHALL return that directory as the working-tree root without copying it

#### Scenario: Local source path with a tilde is expanded

- **WHEN** a `local` registry entry's `uri` begins with `~`
- **THEN** the system SHALL expand it to the user's home directory before use

#### Scenario: Missing local source fails loudly

- **WHEN** a `local` registry entry's `uri` names a path that does not exist
- **THEN** the system SHALL raise a source-fetch error naming the entry id and the missing path
- **AND** SHALL NOT report a successful install of zero items for that entry
