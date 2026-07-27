## Context

`ossify-cogents` already models *where* to fetch capabilities (`ossify-skills-registry` → `SkillSource`) and *how* to enumerate them (`discovery` list → built-in/custom strategies producing per-category `Mapping`s). What is missing is the selection/apply layer: given a fetched source and its discovered items, *which* items land in the repo, and *how* they are written. This change adds an `install` block to close that gap. It sits between discovery (enumeration) and the lock file (what got installed), and is consumed by the existing `SyncCapabilities` reconciler — not by a new verb.

The design must respect the hexagonal layout in `.claude/rules/architecture.md`: domain has no outward dependencies, ports are `Protocol`s, adapters are wired only in `container.py`, and config-serialized models inherit `ConfigModel` for kebab-case aliases.

## Goals / Non-Goals

**Goals:**
- Add an optional, per-item `install` block so selection names are scoped to that item's discovered set (no global namespace, no cross-source collisions).
- Keep target-layout knowledge in the application layer; let the target-writing port expose action-aware write operations that each adapter implements according to its capabilities.
- Split install validation by timing: static offline checks fold into the existing `config verify`; dynamic glob resolution runs at sync time.
- Reuse `SyncCapabilities` as the consumer; add a resolver service mirroring the existing `_discovery_resolver`.
- Guarantee a hand-authored `install` block survives registry add/update.

**Non-Goals:**
- No new CLI verb for installing (sync remains the verb).
- No lock-file format redesign — install is declarative input to the existing sync/lock flow.
- No per-item target-platform routing within a fixed category (single `install` block; `target-platforms` applies uniformly to fixed categories).
- No network access during `config verify`.

## Decisions

### `install` embedded on `SkillSource` (not a separate config section)
Placing `install` as a field on the registry item scopes selection names to that item's own discovered ids, eliminating the ambiguity a flat global block would reintroduce. It also means **no new `ConfigSection`** — install rides inside the existing skill-registry section, so read-modify-write of unmodeled sections is unaffected.
- *Alternative considered:* a top-level `install` section keyed by source id. Rejected: decouples management from intent but re-introduces id-linkage and a new section to wire.
- *Consequence:* registry add/update must **patch** the item, never reconstruct it, or it silently drops `install` (see the update-preserves-install requirement and its dedicated test).

### Action-aware `TargetPort`; layout in application, action execution in adapters
`TargetPort` (`ports_out/`) exposes action-aware write operations — `create_if_absent`, `override`, `merge` — rooted at a configurable target folder (the workspace). It knows nothing about Claude/Cursor layouts. The application layer owns the layout map (canonical item → per-platform path) and, per item, computes the destination path and picks the action; the port *executes* it (`init`→`create_if_absent`, `replace`→`override`, `json_merge`→`merge`). Because action *support* is a per-target capability — a JSON-file target can merge, a folder/markdown target cannot — an adapter MAY raise `UnsupportedTargetActionError` for an operation it cannot perform.
- *Alternative considered (and initially chosen, then reversed):* a dumb port of pure IO primitives (`exists`/`read`/`write`) with the application orchestrating `read`+merge+`write`. Rejected on review: there is no domain model for arbitrary JSON, so the merge was never domain logic, and merge is not a universal capability — modeling it as a port operation lets each adapter declare what it supports instead of assuming every target can be read-merged-written.

### JSON merge lives in the JSON-capable target adapter
`json_merge` needs a deterministic deep-merge of parsed JSON (recurse on object/object, source wins on scalar conflict). It is implemented inside the target adapter that supports it, as an internal pure helper (unit-tested directly against the adapter), not as a domain function — there is no pydantic model for the arbitrary JSON files being merged, and merge capability is adapter-specific.
- *Alternative considered:* a pure `deep_merge` in `domain/`. Rejected: `domain/` would grow a generic dict operation it otherwise has no reason to own, and it wrongly implies every target can merge.

### Validation split by timing
Static checks (by-pattern.category resolvable against the item's discovery strategies; target-platforms are registered adapter ids or `"*"`) are network-free and fold into the existing `config verify` pass, alongside discovery-id resolution. Dynamic glob matching against actually-discovered ids can only happen after fetch+discovery, so it lives in the sync pipeline via a new `_install_resolver` service (mirrors `_discovery_resolver`). The container injects the registered target-adapter id set into verify, the same way built-in strategies are injected.

### Selection = `fnmatch` name-globs; empty-match policy
Every fixed category is a list of `fnmatch` patterns over discovered ids; `"*"` is just a pattern that matches all, so no special "all" keyword is needed. Absent or `[]` selects nothing. At resolution: an **exact literal** matching zero ids is an error (catches typos in hand-picked names); a **glob** matching zero ids is a warning (a pattern may legitimately be empty).

### Fixed categories translated; by-pattern mirrored verbatim
Fixed-category items are translated into each `target-platform`'s layout (so `target-platforms` is meaningful there). A `by-pattern` entry's destination is fixed by its discovery `path`, mirrored verbatim into the target repo, so `by-pattern` ignores `target-platforms` entirely.

## Risks / Trade-offs

- **Embedding couples source-management with install intent** → mitigated by the patch-not-reconstruct update requirement plus a dedicated regression test.
- **`json_merge` semantics on non-object / conflicting JSON shapes are ambiguous** → the adapter's merge helper must define precedence (source wins on scalar conflict; recurse only on object/object) and be unit-tested for these cases.
- **A `json_merge` (or other) action requested against a target that cannot support it** → the adapter raises `UnsupportedTargetActionError`, surfaced at apply time; a future enhancement could pre-check action support during `config verify` if adapters expose their capabilities.
- **`fnmatch` case-sensitivity differs by platform** → pin behavior explicitly (use `fnmatchcase` for deterministic, case-sensitive matching) so results don't vary by OS.
- **Schema drift** → adding `install` to `SkillSource` changes the skill-registry section model; `scripts/generate_schema.py` must include it or the `schema-drift` pre-commit hook fails. Regenerate `schema/v1.json` as part of the change.
- **Static verify needs the target-adapter id set** → the container must supply it; verify stays offline and must not attempt to instantiate/fetch anything to learn the ids.
