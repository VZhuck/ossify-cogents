## Context

`GitSourceAdapter.materialize()` (`src/adapters/sources/git_source_adapter.py:33-44`) is the sole place a git registry entry becomes a working tree on disk. Cache identity (which directory a URI maps to) is deliberately independent of `ref` — one shared clone per normalized URI, any `ref` checked out into it on demand (see module docstring). On a cache hit it currently runs:

```
git fetch --all --tags --prune
git checkout <ref>
```

`fetch` advances remote-tracking refs (`origin/<branch>`) but never touches local branches. `checkout <ref>` re-selects whatever local branch/tag/commit already exists at that name — for a branch, that's whatever it was pointing to since the last time it was created or fast-forwarded, which for this adapter is only at initial `clone` time. The result: every `install` after the first is a no-op with respect to picking up new commits on a tracked branch. This was confirmed against a live cache (`~/Library/Caches/ossify-cogents/repos/architect-ai-toolkit-c196f4e9`): `git branch -vv` reported `[origin/python_claude: behind 1]` right after an `install` run.

Tags and commit SHAs aren't affected — they're immutable, and `checkout <tag-or-sha>` always resolves to the same object regardless of fetch state.

## Goals / Non-Goals

**Goals:**
- Branch `ref`s always materialize the fetched remote-tracking tip.
- No change to cache layout, `_cache_name`, or `_normalize_uri` — identity model is unaffected.
- No change to tag/SHA ref behavior.

**Non-Goals:**
- No lock file / pinned-commit reconciliation (tracked separately as future work per the existing module docstring: "Fork A ... keeps no lock file").
- No new CLI verb (`update`) — `install` already re-fetches every run; this is a correctness fix to that existing behavior, not a new workflow step.
- No detection/handling of local modifications to the cached working tree (out of scope; the cache is an internal, ossify-managed directory, not user-editable).

## Decisions

**Force the local branch to the remote tip after fetch, rather than a plain checkout.**

Replace the unconditional `git checkout <ref>` with logic that, after `fetch`, checks whether `origin/<ref>` exists:
- If it does (branch case): `git checkout -B <ref> origin/<ref>` — creates or resets the local branch `<ref>` to point exactly at `origin/<ref>`, then checks it out. Idempotent across runs; always converges to the fetched tip regardless of local branch drift.
- If it doesn't (tag or SHA case): fall back to today's `git checkout <ref>` unchanged.

*Alternatives considered:*
- `git checkout <ref> && git reset --hard origin/<ref>` — works but requires the same existence check to avoid resetting a tag/SHA checkout against a nonexistent remote ref, and a hard reset on a non-branch HEAD is semantically murkier than `checkout -B`. `checkout -B` is the more direct primitive for "make local branch equal remote branch."
- Always `git pull` — rejected: pull assumes an existing branch checkout and merges, which can conflict with local drift or fail differently on first-time branch creation; `checkout -B ... origin/...` is a pure reset, matching the adapter's "the cache is fully owned by ossify" invariant (no local edits to preserve, unlike `test_existing_cache_is_reused_not_recloned`'s marker file — that test protects *unrelated* files in the tree, not divergent branch state).
- Detect branch-vs-tag by inspecting `entry.source.ref` syntactically — rejected: no naming convention reliably distinguishes tags from branches; asking git (`origin/<ref>` existence) after fetch is authoritative.

## Risks / Trade-offs

- **[Risk]** `checkout -B` discards any local commits on the cached branch that never existed upstream. → **Mitigation**: the cache directory is exclusively ossify-managed (never user-edited); this matches the adapter's existing ownership model, just extended from "don't reclone" to "don't preserve stray branch state either."
- **[Risk]** An extra `git for-each-ref`/`rev-parse` check per `materialize()` call to detect `origin/<ref>` existence adds a small amount of subprocess overhead. → **Mitigation**: negligible relative to the `fetch` that already runs every call.
- **[Trade-off]** This fixes the fetch-then-checkout gap but still performs a full `fetch --all --tags --prune` every install; no incremental/shallow-fetch optimization is in scope here.

## Migration Plan

No data migration. This changes adapter behavior only; existing caches self-correct on their next `install` (the next `fetch` + `checkout -B` naturally fast-forwards them). No rollback concerns beyond reverting the code change — no persistent state format changes.

## Open Questions

None outstanding — scope is intentionally narrow (adapter fix + regression test).
