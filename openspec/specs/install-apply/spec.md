# install-apply Specification

## Purpose
TBD - created by archiving change add-install-command. Update Purpose after archive.
## Requirements
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
translating the canonical item into that platform's layout. Under `mode: copy`,
fixed-category installs SHALL use `replace` semantics: an existing destination
item SHALL be removed before the selected item is written, so no stale files
survive. Under `mode: link` the destination is established by the link-mode
requirements below, which govern when an existing destination may be replaced.
Target-layout knowledge SHALL live in the application layer.

Layouts SHALL be defined as an application-layer **constant registry** keyed by
platform, and the layout for an entry SHALL be selected **dynamically by the
platform key** taken from `install.target-platforms` (so the registry can later
become config-driven without changing the pipeline). Installs perform **verbatim
content copy** only — the layout changes an item's destination directory and file
extension, never its byte content. A `(platform, category)` pair with no entry in
the registry SHALL be reported as an error rather than silently skipped.

The **shape** of a written item (directory tree versus single file) SHALL be taken
from the shape recorded by discovery for that item, not inferred from the target
layout. The target layout SHALL supply the destination path and name only —
including any per-platform rename or extension. A target layout entry SHALL
declare the shape it expects; when an item's discovered shape does not match the
expected shape of a resolved destination, the system SHALL raise an error
identifying the item, the platform, and both shapes, and SHALL NOT write that
destination.

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

#### Scenario: File-shaped item installs without a doubled extension

- **WHEN** a discovered item with shape `file` and id `md-to-word` installs to a
  `claude` `commands` layout whose template is `.claude/commands/{id}.md`
- **THEN** the system SHALL write `.claude/commands/md-to-word.md`

#### Scenario: Shape mismatch fails the destination

- **WHEN** a discovered item with shape `file` resolves to a destination whose
  layout expects shape `dir`
- **THEN** the system SHALL raise an error naming the item, the target platform,
  the expected shape, and the observed shape
- **AND** SHALL NOT write that destination

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

### Requirement: Link-mode install writes symbolic links

When a registry entry's `install.mode` is `link`, the system SHALL install that
entry's selected fixed-category capabilities as symbolic links pointing at their
location in the materialized source tree, rather than copying their bytes. The
link SHALL be created with the shape recorded by discovery for that item: a
`dir`-shaped item SHALL be linked as a single directory symlink, and a
`file`-shaped item as a file symlink.

A directory symlink SHALL NOT be replaced by a real directory containing per-file
links, so that files added to the source afterwards appear in the workspace
without re-running install.

When an entry's `install.mode` is `copy` or absent, the system SHALL copy bytes
exactly as it does today.

#### Scenario: Directory-shaped item links as one directory symlink

- **WHEN** an entry with `mode: link` installs a `dir`-shaped item `word-to-md` to
  `.claude/skills/word-to-md`
- **THEN** the system SHALL create a single symbolic link at
  `.claude/skills/word-to-md` pointing at the item's location in the source tree
- **AND** SHALL NOT create a real directory at that path

#### Scenario: File added to a linked source appears without re-installing

- **WHEN** a new file is created inside a source directory that is already linked
  into the workspace
- **THEN** that file SHALL be visible at the corresponding path under the workspace
  destination without running install again

#### Scenario: File-shaped item links as a file symlink

- **WHEN** an entry with `mode: link` installs a `file`-shaped item `architecture`
  to `.claude/rules/architecture.md`
- **THEN** the system SHALL create a symbolic link at `.claude/rules/architecture.md`
  pointing at the item's source file

#### Scenario: Edits propagate in both directions

- **WHEN** a capability has been installed as a link and its content is modified
  through either the source path or the workspace destination
- **THEN** the modification SHALL be observable from the other path without running
  install

#### Scenario: One canonical item linked to several platforms

- **WHEN** an entry with `mode: link` lists two target platforms whose layouts name
  the same canonical item differently
- **THEN** the system SHALL create one link per platform destination, each pointing
  at the same source file
- **AND** an edit through either destination SHALL be observable from the other

#### Scenario: Copy mode is unchanged

- **WHEN** an entry's `install.mode` is absent or `copy`
- **THEN** the system SHALL write file contents into the destination and SHALL NOT
  create symbolic links

### Requirement: Link target form follows source position

The system SHALL determine a link's target form from the resolved source path's
position relative to the workspace root. When the resolved source path is inside
the workspace root, the system SHALL create a **relative** symbolic link.
Otherwise it SHALL create an **absolute** symbolic link.

#### Scenario: In-workspace source produces a relative link

- **WHEN** an entry with `mode: link` has a `local` source resolving to a path
  inside the workspace root
- **THEN** every link the entry creates SHALL have a relative target
- **AND** the link SHALL resolve correctly after the workspace is cloned to another
  location

#### Scenario: Out-of-workspace source produces an absolute link

- **WHEN** an entry with `mode: link` has a `local` source resolving to a path
  outside the workspace root
- **THEN** every link the entry creates SHALL have an absolute target

### Requirement: Machine-specific link destinations are excluded from version control

The system SHALL record every destination it links with an **absolute** target in
the repository's local, non-committed VCS exclude file, within a delimited block
that the system rewrites in full on each install run. The system SHALL NOT record
destinations linked with a **relative** target, which are portable and intended to
be committed. The system SHALL NOT write to the repository's committed ignore
file.

When the workspace root is not a version-controlled repository, the system SHALL
skip exclude maintenance and report it, and SHALL still create the links.

#### Scenario: Absolute link destinations are excluded

- **WHEN** an install run creates one or more links with absolute targets
- **THEN** the system SHALL write those destination paths into the local exclude
  file inside its delimited block

#### Scenario: Relative link destinations are not excluded

- **WHEN** an install run creates links with relative targets
- **THEN** the system SHALL NOT add those destinations to the exclude file

#### Scenario: Exclude block is rewritten, not appended

- **WHEN** an install run follows an earlier run whose linked destinations differ
- **THEN** the delimited block SHALL contain exactly the current run's absolute link
  destinations
- **AND** SHALL NOT retain destinations from the earlier run
- **AND** content outside the delimited block SHALL be preserved unchanged

#### Scenario: Non-repository workspace skips exclusion

- **WHEN** the workspace root is not a version-controlled repository
- **THEN** the system SHALL create the links, skip exclude maintenance, and report
  that it was skipped

### Requirement: `by-pattern` linkability follows its action

Under `mode: link`, the system SHALL link a `by-pattern` item whose action is
`replace`, because `replace` already means the source owns the destination file.
The system SHALL copy a `by-pattern` item whose action is `init` or `json_merge`,
because both mean the workspace owns the destination, and SHALL emit a warning for
each such item identifying the category and the action.

#### Scenario: replace by-pattern links

- **WHEN** an entry with `mode: link` installs a `by-pattern` item whose action is
  `replace`
- **THEN** the system SHALL create a symbolic link at the item's mirrored
  destination
- **AND** an existing destination SHALL be adopted or reported as severed by the
  same rule as fixed-category destinations

#### Scenario: json_merge by-pattern copies with a warning

- **WHEN** an entry with `mode: link` installs a `by-pattern` item whose action is
  `json_merge`
- **THEN** the system SHALL merge into the destination file as in copy mode
- **AND** SHALL emit a warning naming the category and stating that the action
  cannot be linked

#### Scenario: init by-pattern copies with a warning

- **WHEN** an entry with `mode: link` installs a `by-pattern` item whose action is
  `init`
- **THEN** the system SHALL apply create-if-absent semantics as in copy mode
- **AND** SHALL emit a warning naming the category and stating that the action
  cannot be linked

### Requirement: Matching destinations are adopted, diverged destinations are severed

When a registry entry declares `mode: link` and a destination it would write already exists as a regular file or a real directory rather than a symbolic link, the system SHALL compare that destination's content with the source it would link to. When the content is identical — the destination is a copy-mode install of the same capability — the system SHALL **adopt** it: remove the destination and replace it with the link, reporting the item as linked. A directory destination is identical when it contains exactly the same relative paths with the same bytes.

When the content differs, the system SHALL treat the destination as **severed**:
it SHALL NOT remove or overwrite it, and SHALL report it as an error naming the
destination and the source path it was expected to link to. Divergence is the only
case that carries content the link cannot preserve, so it is the only case that
blocks.

#### Scenario: Matching copy-installed destination is adopted

- **WHEN** an entry switches from `mode: copy` to `mode: link` and its destinations
  still hold the copies of the current source content
- **THEN** the system SHALL replace each destination with a link to its source
- **AND** SHALL NOT report severance

#### Scenario: Diverged regular file at a linked destination is preserved

- **WHEN** an entry with `mode: link` installs to a destination that currently holds
  a regular file whose content differs from the source
- **THEN** the system SHALL leave that file's content untouched
- **AND** SHALL report the destination as severed, naming the expected link target

#### Scenario: Existing correct link is re-established idempotently

- **WHEN** an entry with `mode: link` installs to a destination that is already a
  symbolic link
- **THEN** the system SHALL leave the destination as a symbolic link pointing at the
  current source location
- **AND** SHALL NOT report it as severed

#### Scenario: Copy mode is unaffected by severance detection

- **WHEN** an entry with `mode: copy` installs to a destination holding a regular
  file
- **THEN** the system SHALL replace it as it does today and SHALL NOT report
  severance

### Requirement: Stale links are pruned

The system SHALL remove a workspace destination that is a symbolic link whose
target resolves inside a configured `local` source root but which is no longer
selected by any registry entry. Pruning SHALL unlink only the symbolic link and
SHALL NOT modify, traverse, or remove the file or directory it points at. The
system SHALL report each pruned destination.

The system SHALL NOT prune copied destinations, which carry no provenance
distinguishing them from files authored in the workspace.

#### Scenario: Deselected linked capability is unlinked

- **WHEN** a capability previously installed as a link is no longer selected by any
  entry's `install` selections
- **THEN** the system SHALL unlink its destination and report it as pruned
- **AND** the source file or directory it pointed at SHALL remain unchanged

#### Scenario: Links outside a configured source root are left alone

- **WHEN** a workspace destination is a symbolic link whose target does not resolve
  inside any configured `local` source root
- **THEN** the system SHALL leave it in place

#### Scenario: Copied destinations are not pruned

- **WHEN** a capability previously installed as a copy is no longer selected
- **THEN** the system SHALL leave its destination in place

### Requirement: Link creation never silently degrades to a copy

When the operating system cannot create a symbolic link for a destination the entry declares as linked, the system SHALL attempt a platform-appropriate equivalent for a directory destination, and SHALL raise an error for a file destination naming the destination and the platform requirement. The system SHALL NOT fall back to copying the file's bytes, because a silent copy would stop propagating edits while appearing to succeed.

#### Scenario: Directory link falls back to a platform equivalent

- **WHEN** symbolic link creation for a directory destination is denied by the
  operating system and an equivalent directory-link mechanism is available
- **THEN** the system SHALL create the destination using that mechanism and report
  the destination as linked

#### Scenario: File link failure is an error, not a copy

- **WHEN** symbolic link creation for a file destination is denied by the operating
  system
- **THEN** the system SHALL raise an error naming the destination and how to enable
  link creation on that platform
- **AND** SHALL NOT write the file's bytes to the destination

### Requirement: Install report distinguishes linked from copied items

The system SHALL report each installed item as structured data carrying at least
the target platform, category, item id, destination path, and the mode under which
it was written. The entrypoint SHALL render linked and copied items
distinguishably, and SHALL render a linked item's target path.

#### Scenario: Report carries mode per item

- **WHEN** an install run writes both copied and linked items
- **THEN** the report SHALL identify each item's mode individually

#### Scenario: Linked items render their target

- **WHEN** the entrypoint renders a linked item
- **THEN** the rendered line SHALL show the destination and the source path it
  points at

### Requirement: Destination removal is symlink-safe

Before replacing a fixed-category destination, and when pruning, the system SHALL
remove any existing item at that destination. Removal SHALL distinguish a
symbolic link from a real directory: a symbolic link SHALL be unlinked without
being followed, and only a real directory SHALL be removed recursively. Removal
of an absent destination SHALL be a no-op.

#### Scenario: Symlinked destination is unlinked, not traversed

- **WHEN** a destination path is a symbolic link pointing at a directory
- **THEN** the system SHALL unlink the symbolic link itself
- **AND** SHALL NOT remove, traverse, or otherwise modify the directory it points
  at

#### Scenario: Real directory destination is removed recursively

- **WHEN** a destination path is a real directory containing files
- **THEN** the system SHALL remove the directory and its contents

#### Scenario: Absent destination removal is a no-op

- **WHEN** a destination path does not exist
- **THEN** the system SHALL treat removal as a no-op and SHALL NOT raise an error
