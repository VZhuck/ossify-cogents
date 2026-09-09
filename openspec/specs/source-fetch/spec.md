# source-fetch Specification

## Purpose
TBD - created by archiving change add-install-command. Update Purpose after archive.
## Requirements
### Requirement: Materialize a registry source to a local working tree

The system SHALL materialize a registry entry's source into a local working-tree
root that can be walked and read. A `git` source SHALL be materialized by
cloning or updating a persistent cache and checking out the entry's `ref`; a
`local` source SHALL be materialized in place at its `uri` path without copying,
with `~` expanded.
The chosen adapter SHALL be selected by the entry's `source-type`.

Materializing a `local` entry whose path does not exist SHALL raise a
source-fetch error naming the entry and the missing path. The system SHALL NOT
treat a missing local source as an empty source.

#### Scenario: Git source is cloned and checked out at its ref

- **WHEN** `ossify install` materializes a `git` entry whose cache directory does
  not yet exist
- **THEN** the system SHALL clone the source into the cache and check out the
  entry's `ref`
- **AND** SHALL return the cache working-tree root

#### Scenario: Local source is read in place

- **WHEN** `ossify install` materializes a `local` entry
- **THEN** the system SHALL use the source `uri` path directly as the working-tree
  root
- **AND** SHALL NOT copy the source elsewhere

#### Scenario: Local source path with a tilde is expanded

- **WHEN** a `local` registry entry's `uri` begins with `~`
- **THEN** the system SHALL expand it to the user's home directory before use

#### Scenario: Missing local source fails loudly

- **WHEN** a `local` registry entry's `uri` names a path that does not exist
- **THEN** the system SHALL raise a source-fetch error naming the entry id and the
  missing path
- **AND** SHALL NOT report a successful install of zero items for that entry

#### Scenario: Fetch failure is reported

- **WHEN** materializing a `git` source fails (e.g. the remote is unreachable or
  the `ref` does not exist)
- **THEN** the system SHALL report a source-fetch error and SHALL NOT proceed to
  install that entry

### Requirement: Persistent, OS-specific source cache with override

Git sources SHALL be cached under a durable, OS-specific cache root so the clone
survives between `install` runs and across reboots until the cache is cleaned.
The cache root SHALL be `$OSSIFY_CACHE_DIR` when that environment variable is
set; otherwise it SHALL be the platform user-cache directory for the application.
Each source SHALL occupy a distinct subdirectory under `repos/` named
`<short-slug>-<sha256[:8]>`, where `short-slug` is the source `uri`'s last path
segment (`.git` suffix stripped, sanitized to filesystem-safe characters) and the
suffix is the first 8 hexadecimal characters of the SHA-256 of the normalized
`uri`. An existing cache for a source SHALL be reused by fetching and checking
out the requested `ref` rather than re-cloning.

#### Scenario: Cache subdirectory is a readable slug plus a uri hash

- **WHEN** a `git` source `https://github.com/anthropics/skills.git` is
  materialized
- **THEN** the system SHALL place its cache under `repos/skills-<8 hex chars>/`,
  where the hex suffix is the first 8 characters of the SHA-256 of the normalized
  `uri`

#### Scenario: `OSSIFY_CACHE_DIR` takes highest priority

- **WHEN** `OSSIFY_CACHE_DIR` is set and a `git` source is materialized
- **THEN** the system SHALL place the cache under `$OSSIFY_CACHE_DIR` rather than
  the default platform cache directory

#### Scenario: Existing cache is reused across runs

- **WHEN** a `git` source is materialized and its cache directory already contains
  a clone
- **THEN** the system SHALL update the existing clone (fetch + checkout) rather
  than clone anew

#### Scenario: Distinct sources get distinct cache directories

- **WHEN** two registry entries have different source `uri`s
- **THEN** the system SHALL materialize each into a distinct cache subdirectory

### Requirement: Deterministic uri normalization for cache identity

The system SHALL derive the normalized `uri` — which feeds both the cache-name
hash and the cache-reuse decision — through a deterministic normalization, so
that two spellings of the same source resolve to the same cache directory. The
entry's `ref` SHALL NOT participate in normalization; a single repo cache holds
whichever `ref` is checked out. A `git` `uri` SHALL be normalized by trimming
whitespace, rewriting scp-style `[user@]host:path` into `host/path`, dropping the
scheme and any userinfo to keep `host[/path]`, lowercasing the host only (path
case preserved), dropping a default port, stripping a trailing `.git`, stripping
trailing slashes, and dropping any `?query` and `#fragment`. A `local` `uri`
SHALL be normalized by expanding a leading `~`, resolving to an absolute
symlink-resolved canonical path, and stripping trailing slashes, with path case
preserved.

#### Scenario: SSH and HTTPS spellings of one repo share a cache

- **WHEN** one entry uses `git@github.com:anthropics/skills.git` and another uses
  `https://github.com/anthropics/skills`
- **THEN** both SHALL normalize to `github.com/anthropics/skills` and SHALL
  resolve to the same cache subdirectory

#### Scenario: Ref is not part of cache identity

- **WHEN** the same source `uri` is materialized once at `ref` `main` and once at
  a tag
- **THEN** both SHALL use the same cache subdirectory, and the second SHALL check
  out its `ref` in the existing clone rather than create a new directory

### Requirement: Uniform read side over the working tree

The system SHALL expose a uniform read side over a materialized working-tree root
— enumerating files under a relative subpath and reading a file's bytes —
identically for `git` and `local` sources, so downstream discovery and install
consume both source types the same way.

#### Scenario: Selected file bytes are read from the working tree

- **WHEN** the install pipeline needs the contents of a discovered item at a
  relative path within the working tree
- **THEN** the system SHALL read that file's bytes from the materialized root
  regardless of whether the source is `git` or `local`

