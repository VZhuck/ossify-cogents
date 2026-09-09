## ADDED Requirements

### Requirement: `ossify install` runs the end-to-end install pipeline

The system SHALL provide a top-level `install` command that, for every registry
entry, materializes the entry's source, executes its resolved discovery
strategies, resolves the entry's `install` selections against the discovered ids,
and writes the selected capabilities into the repo. The command SHALL apply the
dynamic selection resolution policy (an exact literal matching nothing is an
error; a glob matching nothing is a warning) already defined for the `install`
model.

#### Scenario: Selected capabilities are installed from a source

- **WHEN** `ossify install` runs with a registry entry whose `install` selects one
  or more discovered capabilities
- **THEN** the system SHALL fetch the source, select the matching capabilities, and
  write them into the repo
- **AND** SHALL exit with a zero status when all entries install without error

#### Scenario: Nothing selected installs nothing

- **WHEN** `ossify install` runs with an entry whose `install` block selects
  nothing (all lists empty)
- **THEN** the system SHALL fetch and enumerate the source but write no
  capabilities for that entry

#### Scenario: Unmatched exact selection fails the command

- **WHEN** an entry's `install` names an exact literal capability that no
  discovered id matches
- **THEN** the system SHALL report an error identifying the unmatched selection and
  SHALL exit non-zero

### Requirement: Fixed-category install into a target-platform layout

The system SHALL write each selected fixed-category capability into the layout of
every target platform listed in the entry's `install.target-platforms`,
translating the canonical item into that platform's layout. Fixed-category
installs SHALL use `replace` semantics: an existing destination item SHALL be
removed before the selected item is written, so no stale files survive.
Target-layout knowledge SHALL live in the application layer.

Layouts SHALL be defined as an application-layer **constant registry** keyed by
platform, and the layout for an entry SHALL be selected **dynamically by the
platform key** taken from `install.target-platforms` (so the registry can later
become config-driven without changing the pipeline). Installs perform **verbatim
content copy** only — the layout changes an item's destination directory and file
extension, never its byte content. A `(platform, category)` pair with no entry in
the registry SHALL be reported as an error rather than silently skipped.

Each registry entry maps `(platform, category)` to a **list** of destinations
(each a destination template plus a shape); most are single-element. The
discovered `<id>` fills the template, and file-shaped categories re-add the
extension the bare discovery stem lacks. v1 populates:

| Platform  | Category   | Destination                                 | Shape |
|-----------|------------|---------------------------------------------|-------|
| `claude`  | `skills`   | `.claude/skills/<id>/`                       | dir   |
| `claude`  | `agents`   | `.claude/agents/<id>.md`                     | file  |
| `claude`  | `commands` | `.claude/commands/<id>.md`                   | file  |
| `claude`  | `rules`    | `.claude/rules/<id>.md`                       | file  |
| `copilot` | `skills`   | `.github/skills/<id>/`                        | dir   |
| `copilot` | `agents`   | `.github/agents/<id>.agent.md`                | file  |
| `copilot` | `rules`    | `.github/instructions/<id>.instructions.md`  | file  |
| `codex`   | `skills`   | `.agents/skills/<id>/`                        | dir   |

Deliberately **absent** (no registry entry → error if selected): `copilot`
`commands`; `codex` `agents`, `commands`, `rules`. These would require
content/format translation (Codex agents are TOML; Codex rules a merged
`AGENTS.md`), which the verbatim-copy pipeline does not perform in v1. The list
shape is retained so a category that maps to several destinations on some future
platform is a data-only addition.

Verbatim copy carries platform-specific frontmatter conventions unchanged: a
`copilot` rule installed from a Claude rule keeps its source frontmatter, so
Claude's path-scoping key (`paths:`) is NOT rewritten to Copilot's (`applyTo:`) —
the rule body installs, but path-scoping metadata does not translate. This is an
accepted v1 limitation of verbatim copy.

#### Scenario: Selected skill written into the Claude skills directory

- **WHEN** `install.target-platforms` includes `claude` and a skill `code-review`
  is selected
- **THEN** the system SHALL write the skill as the directory
  `.claude/skills/code-review/` (its `SKILL.md` and any supporting files)

#### Scenario: File-shaped categories get the `.md` extension

- **WHEN** an agent `planner` is selected for the `claude` platform
- **THEN** the system SHALL write it to `.claude/agents/planner.md`, re-adding the
  `.md` extension that the bare discovery id `planner` lacks

#### Scenario: Same item installs into a different platform's layout

- **WHEN** an agent `planner` is selected and `install.target-platforms` includes
  `copilot`
- **THEN** the system SHALL write the same bytes to
  `.github/agents/planner.agent.md`, using the `copilot` registry entry selected
  dynamically by the platform key

#### Scenario: Codex is supported for skills only in v1

- **WHEN** `install.target-platforms` includes `codex` and both a `skills` item
  and an `agents` item are selected
- **THEN** the system SHALL install the skill to `.agents/skills/<id>/`
- **AND** SHALL report an error for the selected `codex` agent, because no
  `(codex, agents)` layout entry exists

#### Scenario: Replace removes a stale destination first

- **WHEN** a fixed-category item is re-installed and its destination already exists
- **THEN** the system SHALL remove the existing destination item before writing, so
  files no longer present in the source do not remain

#### Scenario: Unsupported target platform errors

- **WHEN** an entry's `install.target-platforms` names a platform for which no
  layout is available
- **THEN** the system SHALL report an error and SHALL NOT write for that platform

### Requirement: `by-pattern` install mirrors verbatim with its action

The system SHALL install each `by-pattern` entry by mirroring the discovered
file(s) for its `category` verbatim to that discovery rule's `path` in the repo,
ignoring `target-platforms`. The entry's `action` SHALL govern how an existing
target is handled: `init` SHALL write only when the target path does not exist;
`replace` SHALL overwrite it wholesale; `json_merge` SHALL deep-merge the source
content into the existing target JSON. An `action` a target cannot perform SHALL
be reported as an unsupported-target-action error.

> **Out of scope for v1 (future reference).** There is no dedicated **MCP-server**
> or **hooks** capability in v1. For Claude these can already be carried by the
> generic `by-pattern` lane above (e.g. `json_merge` into `.mcp.json` or
> `.claude/settings.json`), but no MCP/hooks-specific handling exists. Cross-
> platform MCP and hooks (Copilot `.vscode/mcp.json` / settings UI, Codex TOML
> `[mcp_servers]` / `[hooks]`) require format translation and are deferred; the
> verified per-platform layouts are recorded in `design.md`.

#### Scenario: by-pattern destination comes from the discovery path

- **WHEN** a `by-pattern` entry references a discovery rule whose `path` is
  `.vscode/settings.json`
- **THEN** the system SHALL install to `.vscode/settings.json` regardless of
  `target-platforms`

#### Scenario: init does not clobber an existing file

- **WHEN** a `by-pattern` entry uses `action: init` and the target already exists
- **THEN** the system SHALL leave the existing target unchanged

#### Scenario: json_merge deep-merges into existing JSON

- **WHEN** a `by-pattern` entry uses `action: json_merge` and the target JSON file
  exists
- **THEN** the system SHALL deep-merge the source content into the existing target
  JSON and write the merged result
