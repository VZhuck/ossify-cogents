## Why

Registry entries currently declare *where* to fetch capabilities (`source`) and *how* to enumerate them (`discovery`), but there is no way to declare *which* of the discovered agents/skills/commands/rules should actually be installed into the repo, or *how* those files should be written to a target agent's layout. Discovery lists candidates; nothing selects and applies them. This change adds that selection/apply layer — the missing middle between discovery (enumeration) and the lock file (what got installed).

## What Changes

- Add an `install` block to each `ossify-skills-registry` (registry) item — always present, defaulting to an empty (installs-nothing) stub so every entry carries the field. Because it is embedded on the item, selection names are scoped to that item's own discovered set — no cross-source name collisions.
- `install` selects capabilities per fixed category (`agents`, `skills`, `commands`, `rules`) using `fnmatch` name-globs over discovered ids; absent or `[]` installs nothing, `["*"]` installs the matching set.
- `install.target-platforms` lists the target-adapter ids (or `["*"]` = all supported) to render the fixed-category selections into; it governs the fixed categories only.
- `install.by-pattern` handles pre-existing/foreign files: each entry is `{ category, action }`, where `category` matches a discovery by-pattern category, the destination is mirrored verbatim to the discovery `path` (ignoring `target-platforms`), and `action` is one of `init` | `replace` | `json_merge`.
- Fixed-category installs use an implicit `replace` (folder overwrite) and are translated into each target platform's layout.
- Introduce a dumb `TargetPort` (filesystem IO primitives only) as the first inhabitant of `adapters/targets/`; target layout maps and action semantics live in the application layer.
- Extend the offline config-verify pass with static install validation, and have the existing `SyncCapabilities` reconciler consume `install` at sync time (no new CLI verb).
- Guarantee registry add/update **patches** the existing item so a hand-authored `install` block is never clobbered.

## Capabilities

### New Capabilities
- `capability-install`: the `install` block on a registry item — schema, `fnmatch` selection semantics over discovered ids, `target-platforms` routing, `by-pattern` action semantics (`init`/`replace`/`json_merge`), fixed-category layout translation vs. by-pattern verbatim mirror, and the dynamic (post-discovery) resolution policy (exact-literal-matches-zero = error, glob-matches-zero = warning) consumed by sync.

### Modified Capabilities
- `skill-registry`: `SkillSource` gains an optional `install` field; registry add/update must patch (never reconstruct) so `install` survives an update.
- `config-verify`: adds static, offline install validation — `by-pattern.category` must resolve against the item's discovery strategies' by-pattern categories, and `target-platforms` must be registered target-adapter ids.

## Impact

- **Domain**: new `Dependencies` / `ByPatternDependency` models; a non-optional `install: Dependencies` field on `SkillSource` defaulting to an empty block.
- **Ports/adapters**: new `TargetPort` in `ports_out/`; first `adapters/targets/` implementation; registration in `container.py`.
- **Application**: new `_install_resolver` service (mirrors `_discovery_resolver`); verify gains static install checks; `SyncCapabilities` consumes `install` and orchestrates action semantics + layout translation.
- **Tooling**: `scripts/generate_schema.py` must include `install` in the skill-registry section model or the `schema-drift` pre-commit hook fails. No new `ConfigSection` (install rides inside the skill-registry section).
