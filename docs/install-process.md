# What `install` actually does

`ossify-cogents install` fetches every registered source and copies — or links — your selected files into the workspace. This page describes the current, real behavior — some of it differs from the aspirational description in the project README/CLAUDE.md (notably: there is no lock file yet).

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

## Local sources are read in place, and must exist

A `local` source is not copied into the cache — `install` reads it straight from its `uri`, with `~` expanded. If that path does not exist, the run fails with a source-fetch error naming the entry and the missing path. It is not treated as an empty source: reporting "0 items installed" with a zero exit code would hide a broken config, and under `mode: link` it would additionally prune every link the missing source used to own.

## Files are copied from the cache, not fetched per-file from GitHub

Once a source is fetched/cloned into its cache directory, `install` reads every selected file's bytes straight off that local clone on disk and writes them into your workspace's target locations. GitHub is contacted once per source (the fetch/clone above) — never again per individual file.

## No lock file yet

CLAUDE.md and the original design describe an `ossify-cogents.lock.json` that would pin the exact commit SHA installed for each source, for reproducible re-installs. **This does not exist in the codebase today.** Every `install` run re-fetches and re-writes from whatever `ref` currently resolves to — there's no way yet to pin and later reproduce an exact prior install. Treat this as a documented future feature, not current behavior.

## Destination names

A discovered id is an extension-free canonical name, and the target layout supplies the destination name for each platform: `md-to-word` becomes `.claude/commands/md-to-word.md` and `.github/instructions/md-to-word.instructions.md`.

Each layout also declares the *shape* it expects — a directory for `skills`, a single file for `agents`/`commands`/`rules`. Discovery records the shape the source actually has. When the two disagree (a `skills/` entry that is a lone `.md` file, say), `install` fails with a shape-mismatch error naming the item, the platform, and both shapes, and writes nothing for that destination.

> **Upgrading from an earlier version:** file-shaped items used to install with a doubled extension (`md-to-word.md.md`), because the discovered id carried its own `.md` and the layout appended another. Those files are now written correctly, but `install` never prunes *copies* — the old `*.md.md` files are left where they are and have to be deleted once by hand.

## `mode: link` — installing a local source by reference

An entry with `"mode": "link"` and `source-type: "local"` gets symbolic links instead of copies: the installed capability and the toolkit file are the same file, so an edit through either path is immediately visible from the other with no sync step. Directory-shaped items (skills) link as one directory symlink, so a file added to the source afterwards appears in the workspace without re-running install.

**Link geometry.** A source inside the workspace root links relatively and is meant to be committed; a source outside links absolutely and is machine-specific.

**`.git/info/exclude`.** Absolute-target destinations are written into a marker-delimited block in the repository's local, never-committed exclude file — not `.gitignore`, which would also ignore those paths for a teammate who legitimately *copies* the same capabilities. The block is rewritten in full on every run, so it self-corrects when an entry stops linking, and everything outside the markers is preserved. If the workspace is not a git repository, the links are still created and the run warns that exclusion was skipped.

**`by-pattern` under link mode.** Only `replace` is linked — it already means the source owns the destination file. `init` (seed a file the repo owns afterwards) and `json_merge` (the repo owns it, the source contributes) are copied instead, each with a warning: through a link, a merge would write back into the source.

**Adopted and severed destinations.** A destination that is a regular file where a link belongs is compared against its source. Identical content is a copy-mode install of the same capability, so it is *adopted* — replaced with the link, losing nothing, which makes switching an entry from `copy` to `link` a no-op. Content that *differs* is reported as **severed** and never overwritten: an editor that saves atomically replaces a file symlink rather than writing through it, so a diverged destination is an edit that never reached the source. Inspect and merge it by hand, then re-run install.

**Stale links are pruned.** A destination that is a symlink resolving into a configured `local` source root but which no entry selected this run is unlinked, and reported. Unlinking destroys nothing — the source it pointed at is untouched. A symlink carries this provenance in its own target path, which is why links can be pruned with no lock file and copies still cannot.

**Windows.** A directory link falls back to a junction when symlink creation is denied (a junction needs no elevation). A file link has no such equivalent and fails with an error naming the destination and pointing at Developer Mode. Link mode never silently falls back to copying: under bidirectional authoring, a silent copy means edits stop propagating while appearing to succeed, and the next install overwrites them.

> **A linked toolkit is shared mutable state.** Two workspaces linking the same source see each other's edits — that is the point, and it is the `npm link` footgun. The install report always prints each link's target so the sharing stays visible.

## `install` never needs `sudo`

Everything `install` writes lives under the workspace, the git cache, and
`.git/info/exclude` — all of which a normal user account owns. A permission
failure means something in the workspace is owned by, or locked down for,
someone else; it is never a signal to re-run with elevation. `install` names the
offending path and the `chmod`/`chown` that unblocks it instead of raising a
traceback, because a `sudo` install leaves root-owned skills and links that the
developer can no longer edit — a worse problem than the one it appears to solve.

If a workspace has already been installed into under `sudo`, take it back with:

```bash
sudo chown -R "$(id -un):$(id -gn)" .claude .vscode
```

Running `install` under `sudo` still works and now hands every path it creates
back to `$SUDO_USER`, but it prints a warning saying the elevation was
unnecessary.
