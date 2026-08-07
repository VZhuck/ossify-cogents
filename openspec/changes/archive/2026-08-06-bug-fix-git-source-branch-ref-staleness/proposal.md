## Why

`ossify-cogents install` re-fetches on every run, but for any registry entry whose `source.ref` is a branch (e.g. `main`, `python_claude`) rather than a tag or commit SHA, the checked-out working tree silently stays pinned to whatever commit it was on at first clone. `git fetch` updates the remote-tracking ref (`origin/<branch>`) but never moves the local branch; the subsequent `git checkout <ref>` just re-selects the same stale local branch. Confirmed live against a real cache: `git branch -vv` reported `[origin/python_claude: behind 1]` after a fresh `install` run. Users get no error and no indication that they're installing an outdated commit.

## What Changes

- `GitSourceAdapter.materialize()` forces the local branch to the fetched remote-tracking tip instead of a plain `checkout <ref>`, so branch refs always resolve to the latest upstream commit on every `install` run.
- Tag and commit-SHA refs keep their current (already-correct) behavior — no remote-tracking counterpart exists for them, so no behavior change is needed there.
- Add regression test coverage: push a new commit to the bare-remote fixture between two `materialize()` calls on the same cache and assert the second call's working tree reflects the new commit (existing tests only exercise a static remote).

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `capability-install`: installing from a git source with a branch `ref` SHALL always materialize the branch's current upstream tip, not a previously-cached local commit.

## Impact

- `src/adapters/sources/git_source_adapter.py` (`GitSourceAdapter.materialize`)
- `tests/unit/adapters/sources/test_git_source_adapter.py` (new regression test + fixture helper to advance the bare remote)
- No config schema, CLI surface, or lock-file changes. No impact to tag/SHA-pinned sources.
