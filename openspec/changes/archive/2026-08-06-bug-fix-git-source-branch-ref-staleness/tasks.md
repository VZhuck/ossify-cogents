## 1. Adapter fix

- [x] 1.1 In `GitSourceAdapter.materialize()`, after `git fetch --all --tags --prune`, check whether `origin/<ref>` exists (e.g. `git rev-parse --verify --quiet refs/remotes/origin/<ref>`).
- [x] 1.2 If `origin/<ref>` exists, run `git checkout -B <ref> origin/<ref>` instead of `git checkout <ref>`.
- [x] 1.3 If `origin/<ref>` does not exist (tag or commit SHA), keep the existing `git checkout <ref>` behavior unchanged.
- [x] 1.4 Confirm the clone path (no `.git` dir yet) is unaffected — the fresh clone's initial checkout already tracks the remote branch by default via `git clone`.

## 2. Regression tests

- [x] 2.1 Extend the `bare_remote` test fixture (or add a helper) so a test can push an additional commit to the bare remote after the first `materialize()` call.
- [x] 2.2 Add a test asserting that a second `materialize()` call on the same cache, after a new upstream commit lands on the tracked branch, produces a working tree matching the new commit (not the stale one).
- [x] 2.3 Add a test asserting a tag or commit-SHA `ref` continues to resolve to the exact pinned commit even after unrelated new commits land on the remote's default branch.
- [x] 2.4 Run `uv run pytest tests/unit/adapters/sources/test_git_source_adapter.py -v` and confirm all tests pass, including the pre-existing `test_existing_cache_is_reused_not_recloned`.

## 3. Verification

- [x] 3.1 Run the full unit suite (`uv run pytest`) to confirm no regressions elsewhere.
- [x] 3.2 Run `uv run mypy` / `uv run ruff check` on the touched file per project style rules.
- [x] 3.3 Manually verify against a real stale cache (e.g. the `architect-ai-toolkit` cache used to diagnose this bug): run `install`, then confirm `git branch -vv` in the cache shows the local branch matching `origin/<branch>` with no "behind" delta.
