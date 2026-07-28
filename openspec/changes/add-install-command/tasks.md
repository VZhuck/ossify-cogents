## 1. Source port + adapters (fetch)

- [x] 1.1 Define `SourcePort` `Protocol` in `ports_out/`: `materialize(entry) -> Path`
  plus a read side (`walk(root, subpath) -> Iterable[Path]`, `read_bytes(root, path)
  -> bytes`); re-export from `ports_out/__init__.py`
- [x] 1.2 Add `SourceFetchError(OssifyError)` to `domain/errors.py`
- [x] 1.3 Implement `adapters/sources/local_source_adapter.py`: `materialize` returns
  the `source.uri` path as-is; shared walk/read over a root
- [x] 1.4 Implement `adapters/sources/git_source_adapter.py`: resolve cache root
  (`$OSSIFY_CACHE_DIR` → else `platformdirs.user_cache_dir("ossify-cogents")`),
  per-source dir = `repos/<short-slug>-<sha256[:8]>` over the normalized uri (git
  normalization per the `source-fetch` spec); clone if absent else fetch;
  checkout `ref`; shell out to the `git` binary; wrap failures in `SourceFetchError`
- [x] 1.5 Add `platformdirs` dependency (`uv add platformdirs`)
- [x] 1.6 Unit tests: local passthrough; git clone-then-reuse (fetch+checkout) using a
  local bare repo as the "remote" (no network); `OSSIFY_CACHE_DIR` override honored;
  distinct uris → distinct cache dirs; fetch failure → `SourceFetchError`

## 2. Discovery execution

- [x] 2.1 Add a discovery-execution service in `application/services/` that, given a
  working-tree root + a resolved `DiscoveryDefinition`, enumerates ids and locations
  per fixed category and per by-pattern category (folder rule → immediate children;
  file rule → matching files by stem; missing path → no ids)
- [x] 2.2 Reuse `DiscoveryResolver.resolvable_definitions` to resolve the entry's
  `discovery` ids to `Mapping`s before execution
- [x] 2.3 Unit tests (tmp tree): folder rule enumerates children; file rule enumerates
  by stem; missing path yields empty (no error); by-pattern category recorded

## 3. Target layout + `TargetPort.remove`

- [x] 3.1 Add `remove(path)` to `TargetPort` (`ports_out/`) and implement it on
  `FilesystemTargetAdapter` (recursive delete of a path under the target root; no-op
  if absent)
- [x] 3.2 Add an application-layer target-layout **const registry** keyed
  `(platform, category) -> [(destination template, shape)]`, selected dynamically by
  the platform key (structured so it can later be config-overridden). Populate the
  verbatim-portable v1 set per the `install-apply` spec: `claude`
  (skills/agents/commands/rules), `copilot` (skills/agents/rules), `codex` (skills).
  A missing `(platform, category)` is an error (`TargetLayoutUnavailableError` in
  `domain/errors.py`)
- [x] 3.3 Unit tests: each populated `(platform, category)` resolves to its expected
  destination + shape (incl. `copilot` `.agent.md` / `.instructions.md` extensions,
  `codex` `.agents/skills/`); a populated platform but absent category (`codex`
  agents) raises; an unknown platform raises; `FilesystemTargetAdapter.remove`
  deletes trees and no-ops on absent paths

## 4. Install use case (orchestration)

- [x] 4.1 Add `InstallPort` to `ports_in/` (`install(root) -> InstallReport`) and an
  `InstallCapabilities` use case implementing it
- [x] 4.2 Pipeline per entry: `SourcePort.materialize` → discovery execution →
  `InstallResolver.select` per fixed category (collect warnings, propagate unmatched-
  literal errors) → translate via the layout map → write
- [x] 4.3 Fixed-category write: for each selected item, `TargetPort.remove(dest_root)`
  then walk the item subtree (via `SourcePort` read side) writing each file with
  `override` (implicit `replace`)
- [x] 4.4 by-pattern write: destination = discovery rule `path`; map `action` →
  `TargetPort` op (`init`→`create_if_absent`, `replace`→`override`,
  `json_merge`→`merge`); surface `UnsupportedTargetActionError`
- [x] 4.5 Return/report a summary (installed items per entry, warnings) for the CLI
- [x] 4.6 Unit tests with fakes: select→translate→write for a fixed-category skill into
  Claude; the same agent into `copilot` (`.github/agents/<id>.agent.md`); a `codex`
  install where a skill writes but a selected agent raises
  `TargetLayoutUnavailableError`; by-pattern `init`/`replace`/`json_merge`;
  unmatched-literal error; empty selection installs nothing

## 5. CLI + wiring

- [x] 5.1 Add a top-level `install` command (`cli/_install.py`), resolve workspace via
  `resolve_root(ctx)`, call `Container().install_use_case()`, print the summary; map
  `OssifyError` → non-zero exit
- [x] 5.2 Wire in `container.py`: source adapters as a `{source_type: SourcePort}` map,
  the layout map, discovery-execution service, and `InstallCapabilities`
- [x] 5.3 Source-type dispatch: the use case (or a small resolver) picks the adapter by
  `entry.source_type`

## 6. End-to-end + quality gate

- [x] 6.1 E2E (`tests/e2e/`): a `local` source fixture with an `ossify-open-standard`
  layout → `ossify install` writes the selected skill into `.claude/…`; re-run
  replaces (stale file removed); by-pattern `json_merge` into an existing JSON file;
  a `target-platforms: ["copilot"]` install lands under `.github/…` with the
  `copilot` extensions
- [x] 6.2 E2E: a `git` source backed by a local bare repo (no network), driven through
  `OSSIFY_CACHE_DIR`, installs and reuses the cache on a second run
- [x] 6.3 Sync-time note: update `capability-install`'s Purpose scope note to point at
  `install-apply` as the imperative apply (lock/`sync` reconciler still future)
- [x] 6.4 Run the full quality gate: `ruff` (lint+format), `mypy --strict`,
  `uv run lint-imports`, `pytest` — all green
