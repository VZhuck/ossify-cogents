## ADDED Requirements

### Requirement: Git branch refs resolve to the current upstream tip
When a registry entry's `source.ref` names a branch, the git source SHALL materialize that branch's current upstream commit on every `install` run, not a commit cached from a previous run. This applies only to branch refs; a `ref` that is a tag or a commit SHA is immutable by nature and SHALL continue to resolve to exactly that tag or commit.

#### Scenario: Branch ref reflects new upstream commits on repeat install
- **WHEN** a registry entry's `source.ref` is a branch (e.g. `main`) and the upstream remote has advanced past the last locally cached commit for that branch
- **THEN** running `install` SHALL fetch and materialize the branch's new upstream tip, and the resulting working tree SHALL match that tip rather than the previously cached commit

#### Scenario: Tag or commit-SHA ref is unaffected
- **WHEN** a registry entry's `source.ref` is a tag name or a full commit SHA
- **THEN** running `install` SHALL materialize exactly that tag or commit, regardless of any other branch activity on the remote
