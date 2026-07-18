# config-verify Specification

## Purpose

Defines the `ossify-cogents config verify` CLI command, which validates the config file's registry section against the `SkillSource`/`OssifyConfig` schema and reports schema or uniqueness violations.

## Requirements

### Requirement: `config verify` validates config schema
The CLI SHALL support `ossify-cogents config verify`, which reads the config file at the resolved workspace root and validates its registry section against the `SkillSource`/`OssifyConfig` schema, including duplicate-`id` checks. Deeper business-rule validation beyond schema shape and `id` uniqueness is out of scope for this command in this change.

#### Scenario: Valid config passes verification
- **WHEN** a user runs `ossify-cogents config verify` against a config file whose registry section matches the schema and has unique `id`s
- **THEN** the CLI SHALL report success and exit with status code 0

#### Scenario: Schema violation fails verification
- **WHEN** a user runs `ossify-cogents config verify` against a config file whose registry section violates the schema (e.g. a `local` entry with a `source.ref` field, or a missing required field)
- **THEN** the CLI SHALL report the violation and exit with a non-zero status

#### Scenario: Duplicate id fails verification
- **WHEN** a user runs `ossify-cogents config verify` against a config file containing two registry entries with the same `id`
- **THEN** the CLI SHALL report the duplicate and exit with a non-zero status

#### Scenario: No config file found
- **WHEN** a user runs `ossify-cogents config verify` and no config file exists at the resolved workspace root
- **THEN** the CLI SHALL report that no config was found and SHALL exit with a non-zero status
