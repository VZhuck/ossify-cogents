## MODIFIED Requirements

### Requirement: `config verify` validates config schema
The CLI SHALL support `ossify-cogents config verify`, which reads the config file at the resolved workspace root and validates its registry section against the `SkillSource`/`OssifyConfig` schema, including duplicate-`id` checks, and additionally validates: (1) that every id in every registry entry's `discovery` list resolves against the union of built-in discovery strategies and the config file's `discovery-definitions` section, and (2) that no `discovery-definitions` entry's `id` collides with another `discovery-definitions` entry's `id` or with a built-in strategy's `id` (this is also how an `ossify-`-prefixed custom id gets rejected — as an already-defined id, not via a dedicated reserved-prefix check). Deeper business-rule validation beyond schema shape, `id` uniqueness (across registry entries, `discovery-definitions` entries, and built-ins), and discovery-id resolvability is out of scope for this command in this change.

#### Scenario: Valid config passes verification
- **WHEN** a user runs `ossify-cogents config verify` against a config file whose registry section matches the schema, has unique `id`s, and every `discovery` id resolves to a known strategy
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

#### Scenario: Unresolvable discovery id fails verification
- **WHEN** a user runs `ossify-cogents config verify` against a config file where a registry entry's `discovery` list includes an id matching neither a built-in strategy nor any `discovery-definitions` entry
- **THEN** the CLI SHALL report the unresolvable id and exit with a non-zero status

#### Scenario: Custom definition colliding with a built-in id fails verification
- **WHEN** a user runs `ossify-cogents config verify` against a config file containing a `discovery-definitions` entry whose `id` matches a built-in strategy's id (e.g. `ossify-open-standard`)
- **THEN** the CLI SHALL report it as an already-defined discovery strategy and exit with a non-zero status

#### Scenario: Duplicate discovery-definition id fails verification
- **WHEN** a user runs `ossify-cogents config verify` against a config file containing two `discovery-definitions` entries with the same `id`
- **THEN** the CLI SHALL report the duplicate and exit with a non-zero status
