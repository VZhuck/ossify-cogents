## Why

`ossify-cogents install` always copies. For a `local` source that you are actively authoring — a shared toolkit repo consumed by several projects — copying means every edit needs a re-install to reach the consuming repo, and an edit made *in* the consuming repo has no way back to the toolkit. The authoring loop is: edit toolkit, run install, test in project, discover a problem, edit toolkit, run install, again.

Symlinking a `local` source's capabilities into the workspace removes the loop entirely. The installed capability and the toolkit file are the same file, so edits propagate in both directions with no sync step.

Copy mode is also silently wrong for multi-platform fan-out: `target-platforms: ["claude", "copilot"]` produces two independent copies of one canonical item that diverge on first edit. Link mode produces two *names* for one file, which is what the fan-out always meant.

## What Changes

- Add `mode` to the `install` block: `"copy"` (default, current behavior) or `"link"`. `mode: "link"` requires `source-type: "local"` — a `git` source rejects it as an invalid registry entry, because ossify hard-resets its git cache on every fetch and would silently destroy edits made through a link into it.
- Configuration is the only control. There is no CLI flag: a flag would apply uniformly to every registry entry, which is too blunt for a per-entry decision, and per-entry config is already how `target-platforms`, selections, and actions are expressed.
- `TargetPort` gains `link(path, source, *, is_directory)`. Directory-shaped items link as directories, file-shaped items as files, using the shape recorded by discovery.
- Discovery starts recording each item's **shape** (`dir` | `file`) alongside its location, and a `folder` rule's id becomes the child *stem* when the child is a file. Link mode needs the shape to choose between a directory and a file symlink, and today's name-based ids carry their extension — so `commands/x.md` would link to `.claude/commands/x.md.md`. Absorbed here rather than split out, because link mode cannot be correct without it.
- Link target geometry is decided by position, not configuration: a source resolving **inside** the workspace root produces a **relative** symlink, which is portable and committable; a source **outside** produces an **absolute** symlink, which is machine-specific.
- Absolute (machine-specific) link destinations are recorded in `.git/info/exclude` under a rewritten marker block — the per-developer, never-committed ignore file. Relative in-repo links are deliberately left committable.
- `by-pattern` under link mode: `replace` links (it already means "the source owns this file"); `init` and `json_merge` copy and emit a warning, because both mean the repo owns the destination and neither can be expressed as a link.
- A destination that should be a link but is a regular file is **adopted** when its content is byte-identical to the source — that is a copy-mode install of the same capability, so replacing it with a link loses nothing and makes `mode: copy` -> `mode: link` migration a no-op. When the content **differs**, the destination is reported as **severed** and not overwritten: an atomic-saving editor replaces a file symlink rather than writing through it, and a diverged destination is exactly the edit that silently overwriting would destroy.
- Stale links are pruned: a destination that is a symlink into a configured local source root but is no longer selected is unlinked. Unlinking destroys nothing — the source file is untouched. Copies remain unpruned, exactly as today.
- Windows: directory links fall back to a junction when symlink creation is denied; file links fail with actionable guidance. Link mode never silently degrades to a copy, because under bidirectional authoring a silent copy means edits stop propagating and the next install overwrites them.
- `LocalSourceAdapter.materialize` raises `SourceFetchError` when its path does not exist. Today a missing local path yields no discovered files, so `install` reports zero items and exits zero — a silent no-op that link mode makes more consequential.
- `InstallReport.installed` becomes a list of structured `InstalledItem`s carrying the mode, so the CLI can render linked and copied items distinctly instead of parsing formatted strings.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `capability-install`: the `install` block SHALL carry a `mode` field (`copy` | `link`, defaulting to `copy`).
- `skill-registry`: a registry entry SHALL be invalid when `install.mode` is `link` and `source-type` is not `local`.
- `install-apply`: link-mode write semantics, link target geometry, VCS exclude maintenance, `by-pattern` behavior under link mode, adoption and severed-link detection, stale-link pruning, and mode-aware reporting; fixed-category writes take their shape from discovery, and destination removal becomes symlink-safe.
- `skill-discovery`: discovery SHALL record each discovered item's shape, and `folder`-rule ids SHALL be stems for file children.
- `source-fetch`: materializing a `local` source SHALL fail when its path does not exist.

## Impact

- `src/domain/dependencies.py` — `mode` field on `Dependencies`.
- `src/domain/skill_registry.py` — the `mode`/`source-type` rule in `_apply_source_type_rules`.
- `src/domain/errors.py` — `SeveredLinkError`, `LinkNotSupportedError`, `ShapeMismatchError`.
- `src/domain/install_report.py` — `InstalledItem` model; `installed` becomes `list[InstalledItem]`.
- `src/ports_out/_target_port.py` — `link`.
- `src/ports_out/_vcs_exclude_port.py` — **new** port.
- `src/adapters/targets/filesystem_target_adapter.py` — `link` implementation, Windows fallback, symlink-safe `remove()`.
- `src/adapters/persistence/git_exclude_adapter.py` — **new** adapter (new `adapters/persistence/` package).
- `src/adapters/sources/local_source_adapter.py` — missing-path error.
- `src/application/services/_discovery_execution.py` — `DiscoveredItem(location, shape)`; stem ids for file children.
- `src/application/_install_capabilities.py` — mode branch, adoption/severance check, prune, exclude collection; writes branch on the discovered shape.
- `src/cli/_install.py` — mode-aware rendering.
- `src/container.py` — wire the exclude adapter.
- `schema/v1.json` — regenerated via `scripts/generate_schema.py` once `Dependencies` carries `mode` (the `schema-drift` hook diffs it).
- No lock file. No CLI flags. No `config verify` change — the `mode`/`source-type` rule is enforced by the `SkillSource` model validator, which `config verify` already exercises when it validates the registry section against the schema.

**Behavior change (intended).** Destinations for file-shaped fixed-category items change from `<id>.md.md` to `<id>.md`. Consequences:

- Previously-installed `*.md.md` files are **not** removed — `install` does not prune copies. Users delete them once by hand.
- An `install` selection naming an exact literal *with* its extension (e.g. `"md-to-word.md"`) now matches nothing and raises `UnmatchedInstallSelectionError`; it must be rewritten as `"md-to-word"`. Glob selections such as `"*"` are unaffected.
