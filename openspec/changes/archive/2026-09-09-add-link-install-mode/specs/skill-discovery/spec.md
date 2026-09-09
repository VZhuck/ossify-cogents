## MODIFIED Requirements

### Requirement: Execute a discovery strategy against a materialized source

The system SHALL execute a resolved discovery strategy's `mappings` against a
materialized source working tree to enumerate the capabilities present, producing
for each fixed category (`agents`, `skills`, `commands`, `rules`) and each
`by-pattern` category the set of discovered ids and, for each id, its **location**
within the working tree and its **shape** (`dir` or `file`).

A `folder`-type glob rule SHALL enumerate the immediate children of the referenced
folder. A child SHALL be recorded with shape `dir` when the working tree contains
files beneath it, and with shape `file` when the child is itself a file. The
discovered id SHALL be the child's name when its shape is `dir`, and the child's
**stem** — its name with the final extension removed — when its shape is `file`.

A `file`-type glob rule SHALL enumerate the files matching its pattern, each with
shape `file` and an id equal to the file's stem. A rule whose path is absent from
the working tree SHALL contribute no ids for that rule.

Item ids SHALL therefore be extension-free canonical names in every case, so that a
target layout can apply its own per-platform naming and extension without doubling
one the id already carries.

#### Scenario: Folder rule enumerates its children as ids

- **WHEN** a resolved strategy maps `skills` to a `folder` rule at path `skills`
  and the materialized tree contains `skills/code-review/` and `skills/planner/`
- **THEN** the system SHALL discover skill ids `code-review` and `planner`
- **AND** SHALL record each id's location under the working tree with shape `dir`

#### Scenario: Folder rule over file children records file shape and stem id

- **WHEN** a resolved strategy maps `commands` to a `folder` rule at path
  `commands` and the materialized tree contains `commands/md-to-word.md`
- **THEN** the system SHALL record an item with id `md-to-word`, location
  `commands/md-to-word.md`, and shape `file`
- **AND** the id SHALL NOT retain the `.md` extension

#### Scenario: Folder rule enumerates mixed children

- **WHEN** a `folder` rule over `capabilities` is executed against a tree
  containing both `capabilities/alpha/SKILL.md` and `capabilities/beta.md`
- **THEN** the system SHALL record `alpha` with shape `dir` and `beta` with shape
  `file`

#### Scenario: File rule records file shape

- **WHEN** a resolved strategy maps `rules` to a `file` rule with pattern
  `rules/*.md` and the tree contains `rules/style.md`
- **THEN** the system SHALL record an item with id `style`, location
  `rules/style.md`, and shape `file`

#### Scenario: Missing path yields no ids

- **WHEN** a resolved strategy maps `agents` to a `folder` rule at path `agents`
  and the materialized tree has no `agents` directory
- **THEN** the system SHALL discover no `agents` ids and SHALL NOT error

#### Scenario: by-pattern rule enumerates under its own category

- **WHEN** a resolved strategy declares a `by-pattern` rule with `category`
  `vs-code-settings` and the matching file exists in the tree
- **THEN** the system SHALL record the discovered item under the
  `vs-code-settings` category with its location and shape
