# What `install` actually does

`ossify-cogents install` fetches every registered source and copies your selected files into the workspace. This page describes the current, real behavior — some of it differs from the aspirational description in the project README/CLAUDE.md (notably: there is no lock file yet).

## Cache location

Git sources are cloned into a local cache, not fetched fresh into your workspace each time:

```
platformdirs.user_cache_dir("ossify-cogents")
```

- macOS: `~/Library/Caches/ossify-cogents`
- Linux: `~/.cache/ossify-cogents`

Override the cache root with the `OSSIFY_CACHE_DIR` environment variable.

Each registered source gets its own subdirectory under `<cache_root>/repos/`, keyed by a hash of its *normalized* URI — so `https://github.com/acme/pack.git`, `git@github.com:acme/pack.git`, and other equivalent spellings of the same repo share one cache clone. Switching a source's `ref` in your config reuses that same cache directory; `ref` is deliberately not part of the cache identity.

## Every `install` re-fetches — there is no staleness check

On each `install` run, for every git source:

- If the cache dir already has a clone: `git fetch --all --tags --prune`, then checkout `ref`. If `ref` names a live remote branch, the local branch is hard-reset to `origin/<ref>` (`git checkout -B <ref> origin/<ref>`) — so branch refs always track the latest remote tip.
- If there's no cache dir yet: a full `git clone`, then checkout `ref`.

There's no skip-fetch optimization based on how recently you last ran `install` — every invocation talks to the remote at least once per registered source.

## Files are copied from the cache, not fetched per-file from GitHub

Once a source is fetched/cloned into its cache directory, `install` reads every selected file's bytes straight off that local clone on disk and writes them into your workspace's target locations. GitHub is contacted once per source (the fetch/clone above) — never again per individual file.

## No lock file yet

CLAUDE.md and the original design describe an `ossify-cogents.lock.json` that would pin the exact commit SHA installed for each source, for reproducible re-installs. **This does not exist in the codebase today.** Every `install` run re-fetches and re-writes from whatever `ref` currently resolves to — there's no way yet to pin and later reproduce an exact prior install. Treat this as a documented future feature, not current behavior.
