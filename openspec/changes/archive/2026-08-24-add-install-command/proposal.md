## Why

Every layer between "a source is registered" and "files land in my repo" is
missing. `registry` records *where* to fetch and `install` blocks declare *which*
capabilities to select, but nothing fetches a remote source, walks it, or writes
the selected files anywhere. The selection logic (`InstallResolver.select`) and
the target-writing adapter (`FilesystemTargetAdapter`) already exist and are
unit-tested — they are just never invoked, because there is no fetch, no
discovery execution, and no orchestrating command. This change adds the
imperative `ossify install` command that closes that gap end to end.

This is **Fork A** (imperative): fetch → enumerate → select → translate → write.
It deliberately does **not** build the declarative `sync` reconciler or a lock
file (Fork B) — `install` re-fetches and re-writes every run.

## What Changes

- Add an `ossify install` command that, for each registry entry, materializes its
  source, executes its discovery strategies, resolves its `install` selections,
  and writes the selected capabilities into the repo.
- Introduce a `SourcePort` (`ports_out/`) with two adapters: a **git** adapter
  that clones/fetches into a persistent OS cache and checks out the entry's `ref`,
  and a **local** adapter that reads the source folder in place. Both expose a
  common read side (walk + read bytes) over the materialized working tree.
- Cache location resolves as `$OSSIFY_CACHE_DIR` → else the platform user-cache dir
  (`platformdirs.user_cache_dir("ossify-cogents")`), keyed per source by
  `sha256(normalized uri)`, reused across runs via `git fetch` + checkout.
- Add **discovery execution** to `skill-discovery`: walk a materialized tree with a
  resolved strategy's `Mapping` globs to produce discovered ids (and their
  locations) per fixed category and per `by-pattern` category.
- Add the **apply** layer as a new `install-apply` capability: drive
  `InstallResolver.select` per fixed category, translate each selected item into a
  target-platform layout (a const registry selected by platform key — **Claude,
  plus the verbatim-portable Copilot and Codex-skills subset in v1**), write it
  with implicit `replace`
  semantics, and mirror each `by-pattern` entry verbatim to its discovery `path`
  with its declared `init`/`replace`/`json_merge` action.
- Extend `TargetPort` with a `remove(path)` operation so fixed-category `replace`
  can overwrite an existing item tree wholesale (delete-then-write).

## Capabilities

### New Capabilities
- `source-fetch`: materialize a registry source into a local working tree — git
  sources into a durable per-repo OS cache (clone or fetch+checkout at `ref`),
  local sources read in place — and expose a uniform read side (walk + read bytes).
- `install-apply`: the `ossify install` command and the apply pipeline —
  fixed-category translation into a target-platform layout with `replace`
  semantics, and `by-pattern` verbatim mirroring with per-entry action semantics.

### Modified Capabilities
- `skill-discovery`: adds discovery *execution* — resolving a strategy to a
  `Mapping` was already covered; this adds walking a materialized tree with those
  globs to enumerate discovered ids and their source locations per category.

## Impact

- **Domain**: no new config models (install/discovery models already exist). A
  `TargetPort.remove` addition and possibly small error types
  (`SourceFetchError`, `TargetLayoutUnavailableError`).
- **Ports**: new `SourcePort` in `ports_out/`; `remove` added to `TargetPort`.
- **Adapters**: new `adapters/sources/` (git + local); `platformdirs` dependency
  used only inside the git adapter (edge of the hexagon); `remove` implemented on
  `FilesystemTargetAdapter`.
- **Application**: a discovery-execution service; a target-layout const registry
  keyed by platform, selected dynamically by the platform key (Claude full +
  Copilot skills/agents/rules + Codex skills);
  an `InstallCapabilities` use case wiring fetch → discover → select → translate →
  write; reuses `InstallResolver`, `DiscoveryResolver`.
- **CLI**: new top-level `install` command.
- **Container**: wire the source adapters (keyed by `source_type`), the layout map,
  and the new use case.
- **Dependencies**: add `platformdirs`; requires a `git` binary on PATH at runtime.
- **Deferred (Fork B)**: no lock file, no drift detection, no `sync` reconciler; the
  resolved git SHA is available at fetch time but is not persisted yet.
