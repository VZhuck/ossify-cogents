## Context

`ossify-cogents` reads `ossify-cogents.json` everywhere (`registry`, `config
verify`, and the deferred install/sync flow) but has no command that creates a
first one. `init` fills that gap. It is deliberately small: a config-writer with
a precondition check. It must respect the hexagonal layout in
`.claude/rules/architecture.md` — domain has no outward dependencies, ports are
`Protocol`s, adapters are wired only in `container.py`, config-serialized models
inherit `ConfigModel` for kebab-case aliases.

## Goals / Non-Goals

**Goals:**
- One command that writes a valid, self-documenting default `ossify-cogents.json`.
- Fast-fail (write nothing) when a config file already exists.
- Reuse existing config I/O (`ConfigRepository`) and existing models — no new
  serialization logic, no schema change.

**Non-Goals:**
- No fetching, discovery, or installing — `init` never touches the network and
  never reads the remote it points at.
- No overwrite/merge/`--force` behavior — conflict is a hard error.
- No lock file — `init` predates and is independent of any install/sync/lock flow.
- No interactive prompting — the default item is fixed, curated data.

## Decisions

### The default registry item is packaged code data, not inferred
The curated default (`anthropics/skills`) is a fully-specified `SkillSource`
constant (`id`, `name`, `description`, `source`, `discovery`, `install`), living
beside the built-in discovery strategies as packaged data. `init` writes it
verbatim.
- *Alternative considered:* run the uri through `SourceInferenceService` like
  `registry add` does. Rejected: `infer_id("…/anthropics/skills")` yields the bare
  slug `skills` — a poor, ambiguous id — and the default is curated, not
  user-supplied, so inference adds indirection without value.
- *Consequence:* the default `id`/`name`/`description` are chosen once in code and
  are stable across runs.

### `discovery: ["ossify-open-standard"]`, install skeleton empty
The default references the built-in `ossify-open-standard` strategy and ships an
explicit empty `install` skeleton (`target-platforms: ["claude"]`; all selection
lists `[]`). The skeleton installs nothing, so the fact that `anthropics/skills`
does not use the `agents/skills/commands/rules` folder layout is inert — it only
matters once a user populates a selection list. The empty lists are written
explicitly (not elided) purely to teach the block's shape.
- *Consequence:* the default item is intentionally *not* install-ready out of the
  box; it is a scaffold to edit, not a one-command install.

### Explicit empty skeleton falls out of existing dump behavior
`OssifyConfigAdapter.write_section` dumps with `exclude_none=True, by_alias=True`
(not `exclude_defaults`). Empty lists are not `None`, so a `Dependencies` block
with default `[]` fields already serializes every field explicitly in kebab-case.
`init` therefore only needs to set `target-platforms=["claude"]`; the rest of the
skeleton is automatic. No custom serialization.

### Fast-fail is a precondition check, not a write-action semantic
Without `--force`, `init` calls `ConfigRepository.exists(root)` first; if `True`,
it raises `ConfigAlreadyExistsError` and returns before any write. This is distinct
from the `TargetPort.create_if_absent` primitive (that's about install-time
writes). `init` does not route through `TargetPort` at all — it writes the default
sections via `ConfigRepository.write_section`.
- *Alternative considered:* `create_if_absent`-style silent skip. Rejected: the
  user asked for a hard, visible failure so an accidental re-init can't quietly
  no-op over an existing, hand-edited config.

### `--force` overrides wholesale (not merge); implemented via delete-then-write
`--force` skips the existence guard and writes the default config even when one
exists. It **overrides** (replaces the modeled sections with the default),
deliberately not **merging**.
- *Why not merge:* merge must read and parse the existing config first, but the
  primary reason to reach for `--force` is a broken/invalid config — so merge would
  fail exactly when it is most needed. Merge semantics are also ambiguous (append
  the default item? dedupe by id? union discovery-definitions?), reintroducing the
  very ambiguity `init` exists to remove. Override is deterministic: `init --force`
  equals `init` on a clean directory.
- *Implementation:* because `ConfigRepository.write_section` read-merges the
  existing file (and would choke on malformed JSON), `--force` first calls a new
  `ConfigRepository.delete(root)` to clear the slate, then writes the default
  sections onto the now-absent file. This satisfies "must work on an unparseable
  existing file" and guarantees no stale/unknown sections survive.

### Example custom discovery definition in the default config
The default config writes a `discovery-definitions` section with one example
custom definition mirroring the built-in `ossify-open-standard` mappings. Built-in
strategies are packaged code data that never appear in the file, so a user has no
in-file example of a custom strategy's shape; this scaffolds one (same rationale
as the explicit `install` skeleton).
- *Constraint:* the example id must not collide with a built-in id (the discovery
  resolver rejects duplicates) and must avoid the reserved `ossify-` prefix, or the
  written config would fail `config verify`. It uses a distinct id (e.g.
  `example-standard`).
- *Consequence:* the example definition is intentionally *unused* by the default
  registry entry (which references the built-in `ossify-open-standard`); it exists
  purely as editable documentation, and an unused-but-valid definition passes
  verify.

### Dedicated `InitPort` / `InitConfig`, not an `OssifyConfigPort.init`
`init` is a distinct top-level command with a distinct responsibility
(scaffolding vs. validating), so it gets its own inbound port and use case rather
than growing `OssifyConfigPort` (which is `config verify`'s port).
- *Alternative considered:* add `init()` to `OssifyConfigPort`. Rejected: couples
  a top-level command to the `config` sub-app's port and mixes create-vs-validate
  responsibilities.

## Risks / Trade-offs

- **Default item is not install-ready** (layout mismatch with
  `ossify-open-standard`) → accepted and documented; `init` scaffolds, it does not
  install. A follow-up could add an anthropic-layout built-in strategy and point
  the default at it.
- **Only the skill-registry section is written** → the default config has no
  `discovery-definitions` section because the referenced strategy is a built-in
  (never serialized). Correct by design; noted so it isn't mistaken for a bug.
- **Curated id/name chosen in code** → if the desired default id changes, it's a
  code edit plus a test update; acceptable for a single curated constant.
