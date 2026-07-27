## ADDED Requirements

### Requirement: `ossify init` scaffolds a default config

The system SHALL provide a top-level `init` command that writes a default
`ossify-cogents.json` at the resolved workspace root. On success it SHALL exit
with a zero status.

#### Scenario: Writes a default config in an empty workspace

- **WHEN** `ossify init` runs in a workspace that has no `ossify-cogents.json`
- **THEN** the system SHALL create `ossify-cogents.json` at the workspace root
- **AND** SHALL exit with a zero status
- **AND** the written file SHALL be valid against the config schema (it passes
  `config verify`)

### Requirement: Default config contents

The default `ossify-cogents.json` SHALL contain an `ossify-skills-registry`
section holding exactly one registry entry: a curated `git` source with `uri`
`https://github.com/anthropics/skills` and `ref` `main`, `discovery` set to
`["ossify-open-standard"]`, and an `install` block written as an explicit empty
skeleton — `target-platforms` set to `["claude"]` and every selection list
(`agents`, `skills`, `commands`, `rules`, `by-pattern`) present but empty. The
entry's identity fields (`id`, `name`, `description`) SHALL be fixed curated
values, not derived from the uri. Field names SHALL serialize as kebab-case on
disk (`source-type`, `target-platforms`, `by-pattern`).

The default config SHALL also contain a `discovery-definitions` section holding
one example custom discovery definition whose `mappings` mirror the built-in
`ossify-open-standard` strategy (a `folder` rule per fixed category), so the
written file documents the shape of a custom strategy — which is otherwise
invisible because built-in strategies are packaged code data and never appear in
the config. The example definition's `id` SHALL be a distinct value that does not
collide with any built-in strategy id and does not use the reserved `ossify-`
prefix, so that the written config passes `config verify`.

#### Scenario: Single curated registry item

- **WHEN** `ossify init` writes the default config
- **THEN** the `ossify-skills-registry` section SHALL contain exactly one entry
- **AND** that entry's `source.uri` SHALL be `https://github.com/anthropics/skills`
  with `source-type` `git` and `ref` `main`
- **AND** that entry's `discovery` SHALL be `["ossify-open-standard"]`

#### Scenario: Install block written as an explicit empty skeleton

- **WHEN** `ossify init` writes the default config
- **THEN** the entry's `install` block SHALL set `target-platforms` to `["claude"]`
- **AND** SHALL include `agents`, `skills`, `commands`, and `rules` as empty lists
- **AND** SHALL include `by-pattern` as an empty list
- **AND** the block SHALL therefore select nothing for installation

#### Scenario: Example custom discovery definition documents the strategy shape

- **WHEN** `ossify init` writes the default config
- **THEN** the `discovery-definitions` section SHALL contain exactly one custom
  definition whose `mappings` mirror the built-in `ossify-open-standard` strategy
- **AND** that definition's `id` SHALL NOT collide with any built-in strategy id
- **AND** the written config SHALL pass `config verify`

### Requirement: `ossify init` fast-fails when a config already exists

Absent the `--force` flag, the system SHALL treat an existing
`ossify-cogents.json` at the resolved workspace root as a hard error: `ossify
init` SHALL report the error, SHALL exit with a non-zero status, and SHALL write
nothing. It SHALL NOT overwrite, merge into, or partially modify the existing
file.

#### Scenario: Existing config is left untouched

- **WHEN** `ossify init` runs without `--force` in a workspace that already has a
  `ossify-cogents.json`
- **THEN** the system SHALL report an error identifying the existing config
- **AND** SHALL exit with a non-zero status
- **AND** SHALL leave the existing `ossify-cogents.json` byte-for-byte unchanged

### Requirement: `ossify init --force` overrides an existing config

When the `--force` flag is passed, `ossify init` SHALL write the default config
even if an `ossify-cogents.json` already exists, overriding the existing modeled
sections wholesale rather than merging into them. The result SHALL be equivalent
to running `ossify init` on an empty workspace: the `ossify-skills-registry` and
`discovery-definitions` sections SHALL hold exactly the default contents. `--force`
SHALL NOT require the existing file to be valid or parseable.

#### Scenario: Force overwrites an existing config with the default

- **WHEN** `ossify init --force` runs in a workspace whose `ossify-cogents.json`
  contains other, hand-edited registry entries
- **THEN** the system SHALL replace the modeled sections with the default config
  contents
- **AND** SHALL exit with a zero status

#### Scenario: Force succeeds against an invalid existing config

- **WHEN** `ossify init --force` runs in a workspace whose `ossify-cogents.json`
  is malformed or invalid
- **THEN** the system SHALL still write the default config
- **AND** SHALL NOT require the existing file to be parseable
