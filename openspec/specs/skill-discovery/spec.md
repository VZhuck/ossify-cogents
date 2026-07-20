# skill-discovery Specification

## Purpose

Defines how a registry entry declares *how* to find agents/skills/commands/rules inside a fetched source: the `discovery` field on a registry entry, the `discovery-definitions` config section for custom strategies, the built-in strategy set, and id-resolution/uniqueness rules across both.

## Requirements

### Requirement: `discovery-definitions` custom strategy schema
The system SHALL model a root config section, `discovery-definitions`, as a list of custom discovery-strategy definitions, each with `id`, `type` (`"custom"`), and `mappings`. `mappings` SHALL have four fixed categories — `agents`, `skills`, `commands`, `rules` — each a list of glob rules (`{ type: "file" | "folder", path }`), plus a `by-pattern` list of glob rules that additionally carry a required `category` string, for project-defined capability categories beyond the four fixed ones.

#### Scenario: Custom definition with fixed-category mappings
- **WHEN** a `discovery-definitions` entry declares `mappings.rules` with one glob rule
- **THEN** the system SHALL parse it as a `rules` category mapping for that definition's `id`

#### Scenario: `by-pattern` entry declares its own category
- **WHEN** a `discovery-definitions` entry declares a `by-pattern` rule with `category: "playbooks"`
- **THEN** the system SHALL associate that rule with the `"playbooks"` category rather than one of the four fixed categories

### Requirement: Built-in discovery strategies
The system SHALL ship a set of built-in discovery strategies as packaged code data, each identified by an `ossify-`-prefixed id (e.g. `ossify-open-standard`), resolvable by id without appearing in `ossify-cogents.json`. **NOTE:** the `ossify-` prefix is reserved for built-in discovery strategies by convention/documentation only; it is not enforced by a dedicated validator (see the duplicate-id requirement below for how a colliding custom id is actually caught).

#### Scenario: Built-in strategy resolves without config entry
- **WHEN** a registry entry's `discovery` list includes `"ossify-open-standard"` and no `discovery-definitions` section exists in the config file
- **THEN** the system SHALL resolve `"ossify-open-standard"` against the built-in strategy set and treat it as valid

### Requirement: Discovery id resolution
The system SHALL resolve every id in a registry entry's `discovery` list against the union of built-in strategies and parsed `discovery-definitions` entries, treating an id that matches neither as unresolvable.

#### Scenario: Id resolves to a custom definition
- **WHEN** a registry entry's `discovery` list includes an id that matches a `discovery-definitions` entry's `id`
- **THEN** the system SHALL resolve it to that custom definition

#### Scenario: Unknown id is unresolvable
- **WHEN** a registry entry's `discovery` list includes an id that matches neither a built-in strategy nor any `discovery-definitions` entry
- **THEN** the system SHALL treat that id as unresolvable

### Requirement: `discovery-definitions` id uniqueness against built-ins and other custom entries
The system SHALL reject a `discovery-definitions` entry whose `id` collides with either another `discovery-definitions` entry's `id` or a built-in strategy's `id`, reporting it as an already-defined discovery strategy.

#### Scenario: Custom definition colliding with a built-in id rejected
- **WHEN** a `discovery-definitions` entry is parsed with `id: "ossify-open-standard"`, matching a built-in strategy's id
- **THEN** the system SHALL reject it as an already-defined discovery strategy and SHALL NOT add it to the resolved set of available strategies

#### Scenario: Two custom definitions sharing an id rejected
- **WHEN** two `discovery-definitions` entries are parsed with the same `id`
- **THEN** the system SHALL reject the config as containing an already-defined discovery strategy
