## ADDED Requirements

### Requirement: Execute a discovery strategy against a materialized source

The system SHALL execute a resolved discovery strategy's `mappings` against a
materialized source working tree to enumerate the capabilities present, producing
for each fixed category (`agents`, `skills`, `commands`, `rules`) and each
`by-pattern` category the set of discovered ids and, for each id, its location
within the working tree. A `folder`-type glob rule SHALL enumerate the immediate
children of the referenced folder, using each child's name as the discovered id.
A `file`-type glob rule SHALL enumerate the files matching its pattern, using each
file's stem as the discovered id. A rule whose path is absent from the working
tree SHALL contribute no ids for that rule.

#### Scenario: Folder rule enumerates its children as ids

- **WHEN** a resolved strategy maps `skills` to a `folder` rule at path `skills`
  and the materialized tree contains `skills/code-review/` and `skills/planner/`
- **THEN** the system SHALL discover skill ids `code-review` and `planner`
- **AND** SHALL record each id's location under the working tree

#### Scenario: Missing path yields no ids

- **WHEN** a resolved strategy maps `agents` to a `folder` rule at path `agents`
  and the materialized tree has no `agents` directory
- **THEN** the system SHALL discover no `agents` ids and SHALL NOT error

#### Scenario: by-pattern rule enumerates under its own category

- **WHEN** a resolved strategy declares a `by-pattern` rule with `category`
  `vs-code-settings` and the matching file exists in the tree
- **THEN** the system SHALL record the discovered item under the `vs-code-settings`
  category with its location
