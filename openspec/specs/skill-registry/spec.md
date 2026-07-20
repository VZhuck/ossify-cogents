# skill-registry Specification

## Purpose

Defines the registry entry schema (git/local sources, id uniqueness) and the `ossify-cogents registry get`/`registry add` CLI commands for inspecting and managing registered skill sources in `ossify-cogents.json`.

## Requirements

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

### Requirement: Registry entry `id` uniqueness
The system SHALL enforce that every entry's `id` is unique across the registry array.

#### Scenario: Duplicate id rejected
- **WHEN** an entry is added whose `id` already exists in the registry
- **THEN** the system SHALL reject the addition with a duplicate-id error and SHALL NOT modify the stored registry

### Requirement: `registry get` lists all registered sources
The CLI SHALL support `ossify-cogents registry get`, which reads the registry section of the resolved config file and displays every entry.

#### Scenario: Listing a populated registry
- **WHEN** a user runs `ossify-cogents registry get` in a workspace with a config file containing registry entries
- **THEN** the CLI SHALL display each entry's `id`, `name`, `source-type`, and source location

#### Scenario: No config file found
- **WHEN** a user runs `ossify-cogents registry get` and no config file exists at the resolved workspace root
- **THEN** the CLI SHALL report that no config was found and SHALL exit with a non-zero status

### Requirement: `registry add` appends a new source with inferred defaults
The CLI SHALL support `ossify-cogents registry add <uri>`, which validates and appends a new entry to the registry section, creating the config file if none exists at the resolved workspace root.

`uri` SHALL be accepted either as a positional argument or via the `--source.uri` flag (equivalent aliases for the same value); supplying both with differing values SHALL be a usage error. `--source-type` SHALL default to `git`. `--source.ref` SHALL be accepted only when `--source-type` is `git`; supplying it with `--source-type local` SHALL be a usage error. When `--id`, `--name`, or `--description` are omitted, the system SHALL infer them deterministically from the given `uri` via string parsing only, with no network requests.

#### Scenario: Adding a git source with defaults
- **WHEN** a user runs `ossify-cogents registry add https://github.com/acme-org/agent-pack.git`
- **THEN** the system SHALL add an entry with `source-type` `git`, `source.uri` set to the given URL, `source.ref` defaulted to `main`, and `id`/`name`/`description` inferred from the URL

#### Scenario: Adding a local source
- **WHEN** a user runs `ossify-cogents registry add ./experiments/my-skills --source-type local`
- **THEN** the system SHALL add an entry with `source-type` `local` and `source.uri` set to the given path, with no `source.ref` field

#### Scenario: Mismatched source flag rejected
- **WHEN** a user runs `ossify-cogents registry add ./experiments/my-skills --source-type local --source.ref develop`
- **THEN** the CLI SHALL reject the command with a usage error before any registry entry is written

#### Scenario: Conflicting uri inputs rejected
- **WHEN** a user supplies both a positional `uri` and a differing `--source.uri` value in the same `registry add` invocation
- **THEN** the CLI SHALL reject the command with a usage error

#### Scenario: Explicit overrides win over inference
- **WHEN** a user runs `registry add` with an explicit `--id`, `--name`, or `--description`
- **THEN** the system SHALL use the explicitly supplied value instead of the inferred one

#### Scenario: No config file found on add
- **WHEN** a user runs `ossify-cogents registry add <uri>` and no config file exists at the resolved workspace root
- **THEN** the system SHALL create a new config file at that root containing the new entry, rather than raising a not-found error
