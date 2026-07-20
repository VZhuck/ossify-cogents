## Context

`skill-registry` (implemented) lets a workspace declare *where* a skill source lives (`id`, `source-type`, `source`). Nothing yet says *how* to find agents/skills/commands/rules once that source is fetched — different upstreams lay files out differently (a plain open-standard folder convention vs. a Claude marketplace convention). This change adds the configuration vocabulary for declaring discovery strategies per registry entry, plus a place to define custom ones, without yet building the machinery that walks a real source tree (that requires source materialization — git clone / local read — which doesn't exist in this codebase yet, and is deliberately deferred to a future "resolve/sync" change per the proposal's Non-Goals).

An earlier design memory (from a prior, never-implemented planning session) sketched a similar idea under the names `discovery-conventions`/`agent-skills-registry`/`target-layouts`. That design was never built and this change does not treat it as prior art — it independently settled on `discovery`/`discovery-definitions` naming instead, chosen to pair cleanly (per-entry field vs. root section) and to avoid the "skill-" prefix undsersell (definitions cover agents/commands/rules too, not just skills).

## Goals / Non-Goals

**Goals:**
- Add `discovery: list[str]` to `SkillSource`, defaulting to `[]` (a source with no declared strategy is valid, just inert).
- Add a `discovery-definitions` root config section for custom strategy definitions: `{ id, type: "custom", mappings: { agents, skills, commands, rules, by-pattern } }`.
- Ship built-in strategies as packaged code data (starting with `ossify-open-standard`), resolvable by id, never written into the config file. `ossify-` is the reserved id prefix for these built-ins **by convention/documentation only** — see the Decisions entry below for why there's no dedicated enforcement.
- Extend `config verify` to check every `discovery` id (on every registry entry) resolves against built-ins ∪ `discovery-definitions`, and reject duplicate `id`s across that same combined pool — a custom `discovery-definitions` entry re-using a built-in's id (e.g. `ossify-open-standard`) is rejected as a duplicate, not via a separate prefix check (mirroring the existing registry duplicate-`id` rule).
- Establish and apply a project-wide **kebab-case** convention for all on-disk config field names, migrating the already-shipped `source_type` field to `source-type` as part of the same convention pass.
- Generate a JSON Schema (`schema/v1.json`) describing the known config sections, so editors/CI can validate `ossify-cogents.json` independently of the CLI.

**Non-Goals:**
- Materializing a source's file tree (git clone / local folder read) — no such adapter exists yet.
- Running strategy globs against real files, union-merging matches across multiple strategies for one entry, and detecting file-level category clashes (e.g. the same path claimed under two different categories by two strategies). These were explored and decided in principle (merge = union; clash = verify error; `by-pattern` = free-form 5th-category escape hatch) but require source materialization to actually execute, so implementation is deferred to the future resolve/sync change. This change only validates *configuration shape and id-resolvability*, not source contents.
- Overriding/extending one glob of a built-in from a custom definition (`extends`-style inheritance) — custom definitions are fully independent/standalone in v1.
- Any new CLI commands — `config verify`'s existing output gains new failure cases, no new command surface.

## Decisions

### `discovery` is a plain `list[str]` of ids on `SkillSource`, not a nested object
Mirrors the simplicity of `source_type`/`source`: the entry only *references* strategies by id, it doesn't embed strategy definitions inline (those live centrally in `discovery-definitions` + built-ins so they can be reused across entries). Default `[]` — validated as legal, not required-non-empty, since the proposal's own built-in-shipped-but-declared-nowhere pattern means a freshly `registry add`-ed entry naturally starts with no discovery strategy until the user opts in.

### `domain/discovery.py`: `DiscoveryDefinition` + `Mapping`/`GlobRule`, same modeling style as `skill_registry.py`
- `GlobRule { type: Literal["file", "folder"], path: str }` — one glob rule.
- `Mapping { agents: list[GlobRule], skills: list[GlobRule], commands: list[GlobRule], rules: list[GlobRule], by_pattern: list[ByPatternRule] }`, all defaulting to `[]`.
- `ByPatternRule` extends `GlobRule` with a required `category: str` — the free-form 5th-category escape hatch, since unlike the four fixed buckets its target category isn't implied by the field name.
- `DiscoveryDefinition { id: str, type: Literal["custom"] = "custom", mappings: Mapping }`. `type` defaults to `"custom"` (see the dedicated decision below); kept as an explicit field rather than dropped — the built-in vs. custom distinction is real even though only one value is legal *within this section*, and it keeps the model self-describing if a future change ever allows a built-in override to be recorded here.
- No model-level reserved-prefix validator on `DiscoveryDefinition` — see the dedicated decision below for why that check was dropped in favor of duplicate-id detection.

**NOTE:** the `ossify-` prefix is reserved for built-in discovery strategies. This is a documented convention, not a structurally-enforced rule — see below for why, and how a collision still gets caught.

### Reserved-prefix is enforced via duplicate-id detection, not a dedicated validator
An earlier pass of this design put a `model_validator(mode="after")` on `DiscoveryDefinition` rejecting `id.startswith("ossify-")`. That doesn't actually work: pydantic validators fire on *every* construction of a model, not just when parsing config-sourced data — so `DiscoveryDefinition(id="ossify-open-standard", ...)` in `domain/_builtins.py` would trip the same validator a hand-authored config entry would, making it impossible to construct the built-ins as `DiscoveryDefinition` instances at all.

Rather than route around that (raw dicts, `model_construct()`, or moving the check to a specific code path — see the prior Open Question this replaces), this change drops the dedicated reserved-prefix check entirely. Instead:
- `domain/_builtins.py` constructs built-ins as plain `DiscoveryDefinition` instances, no exemption needed, because there's no validator to trip.
- The resolver pool is built-ins ∪ parsed `discovery-definitions` entries. A custom entry whose `id` happens to start with `ossify-` (e.g. re-using `ossify-open-standard`) collides with a built-in already in that pool and is rejected by the existing duplicate-`id` check (below) — same error path as two custom entries sharing an `id`, just phrased generically: **"discovery strategy 'ossify-open-standard' is already defined"** rather than a prefix-specific message. It doesn't matter whether the collision is against another custom entry or a built-in; either way, the id is taken.
- This does mean a custom id that *doesn't* collide with any current built-in (e.g. `ossify-something-not-yet-shipped`) is **not** rejected today — the `ossify-` prefix is a naming convention users are asked to respect, not a structurally-guaranteed reservation. Moved to Risks/Trade-offs below.

### Built-ins are packaged code, not schema instances
`domain/_builtins.py` holds a plain dict/list of `DiscoveryDefinition`-shaped built-in strategies (e.g. `ossify-open-standard`), constructed in code. This is pure `domain/`-level data — no adapter, no I/O — consistent with `domain/` having no dependencies on the rest of the app.

### `ConfigSection.DISCOVERY_DEFINITIONS = "discovery-definitions"`
Follows the existing `ConfigSection` enum pattern in `domain/ossify_config.py` — one more section key, same section-keyed round-trip persistence `OssifyConfigAdapter` already provides generically. No new persistence mechanism needed.

### All config field names are kebab-case, via a shared model config (not per-field aliases)
Today there is no aliasing: `SkillSource.source_type` serializes as `source_type` on disk (`tests/e2e/test_registry_flow.py` asserts this), while the spec prose calls it `source-type` — a latent inconsistency. Rather than introducing the new `by_pattern`/`discovery-definitions` fields under a *third* naming style, this change makes kebab-case the single on-disk convention for all config fields:

- Introduce one shared frozen base model in `domain/` (e.g. `ConfigModel(BaseModel)`) with `model_config = ConfigDict(frozen=True, alias_generator=to_kebab, populate_by_name=True)`, and have every config-serialized model (`Source`, `SkillSource`, `DiscoveryDefinition`, `Mapping`, `GlobRule`, `ByPatternRule`) inherit it. Python fields stay snake_case; the alias generator maps `source_type` → `source-type`, `by_pattern` → `by-pattern` automatically, so no per-field `alias=` boilerplate.
- `populate_by_name=True` keeps in-code construction (`SkillSource(source_type=...)` in services/tests) working unchanged.
- `OssifyConfigAdapter.read_section`/`write_section` must round-trip by alias: `TypeAdapter(...).dump_python(..., by_alias=True)` on write and validation already accepts aliases on read. This is the only adapter change.
- **Migration**: `source_type` → `source-type` is a breaking on-disk rename. Since there are no released versions or persisted user configs to migrate (pre-1.0, single archived change), we rename outright rather than dual-read both keys. `tests/e2e/test_registry_flow.py:46` (`entry["source_type"]`) and any config fixtures update to the kebab key.
- Record the convention in `.claude/rules/python_style.md` under "Domain models" so future config fields follow it by default.

`ConfigSection` values (`ossify-skills-registry`, `discovery-definitions`) are already kebab — they're explicit enum strings, unaffected by the alias generator, which only governs *field* names within a section.

### Duplicate-`id` validation for `discovery-definitions` — checked against built-ins too, not just other custom entries
`discovery-definitions` entries carry an `id` and share the same collision risk as registry entries, which `RegistryValidator` already guards. A resolver backed by a dict/set would silently dedupe and hide a genuine conflict. So `config verify` rejects a `discovery-definitions` entry whose `id` collides with **either** another `discovery-definitions` entry **or** a built-in id, reusing the same `DuplicateSourceIdError`-style reporting path (`DuplicateDiscoveryIdError`, subclassing `OssifyError`). This is enforced in the discovery resolver / `VerifyConfig`, parallel to the registry rule — not left implicit in the resolution map. This check is also what makes the `ossify-` reserved-prefix convention effective in practice (see above): a custom entry can't be authored under an id a built-in already occupies, it just fails as "already defined" rather than "reserved prefix."

### JSON Schema is generated from the known section models, not from `OssifyConfig`
`OssifyConfig` holds sections as opaque `dict[str, Any]` (deliberately, to preserve sections this codebase doesn't model), so it can't produce a useful schema by itself. Instead, a small generator script (e.g. `scripts/generate_schema.py`, runnable via a `pyproject.toml` script or `uv run`) composes the *known* section models — `list[SkillSource]` under `ossify-skills-registry`, `list[DiscoveryDefinition]` under `discovery-definitions` — into a single `schema/v1.json` with `additionalProperties: true` at the root (unknown sections stay legal). `by_alias=True` when emitting so the schema keys match the kebab on-disk names. The quality gate regenerates and diffs it so it can't drift from the models.

### `DiscoveryDefinition.type` defaults to `"custom"`
`type: Literal["custom"] = "custom"` rather than a required field: it's the only legal value in this section, so requiring it in every hand-written entry is pure boilerplate. The field stays present for schema self-description and forward compatibility (see the trade-off note below).

### Id-resolution validation lives in a new `application/services/` piece, reused by `VerifyConfig`
A `DiscoveryResolver` (or similarly named) service, parallel to the existing `RegistryValidator`/`SourceInferenceService`, takes the full set of built-ins ∪ parsed `discovery-definitions` entries and exposes "does this id resolve?". `VerifyConfig` (existing use case, `application/_verify_config.py`) calls it once per registry entry's `discovery` list, reporting unresolvable ids the same way it already reports duplicate-`id` violations. This keeps `VerifyConfig` the single place `config verify`'s checks are orchestrated, rather than splitting verification logic across two use cases.

### No new adapter, no new port
Reading `discovery-definitions` is just another `ConfigRepository.read_section` call (generic, already exists) — no new `ports_out` interface needed. This change touches `domain/`, `application/` (one new service + `VerifyConfig` extension), and wiring in `container.py` to hand `VerifyConfig` the built-in strategy list; it does not touch `adapters/*/sources` or `adapters/*/targets` at all, since no source materialization happens here.

## Risks / Trade-offs

- [Deferring real glob execution means `config verify` can say "this id is valid" while the actual source has zero matching files, or hides a clash that would only surface later] → Accepted for this change: the proposal explicitly scopes clash detection to the future resolve/sync change, once source materialization exists to make it meaningful. Documented here so it isn't mistaken for an oversight.
- [`type: "custom"` on every `discovery-definitions` entry is currently redundant information] → Accepted; kept for schema self-description and forward compatibility (see Decisions), not for validation ROI in this change.
- [The `ossify-` reserved prefix is a naming convention, not a structurally-enforced rule: a custom id starting with `ossify-` that does *not* collide with any built-in shipped *today* is accepted, and only becomes a conflict retroactively if a future built-in is later added under that same id] → Accepted; built-in ids are a fixed, code-reviewed set, so the practical collision risk is low. This replaces the earlier (broken) plan to enforce the prefix via a dedicated model validator — see the Decisions entry above for why that approach didn't work.

## Open Questions

- Exact list/shape of built-in strategies beyond `ossify-open-standard` (e.g. `ossify-claude-marketplace`) is deferred to implementation — not spec-critical for this change, which only needs at least one built-in to exercise the resolution path.
- Whether `DiscoveryResolver` should be its own `application/services/` file or a method added to the existing `RegistryValidator` is left to implementation; both keep the same layer boundaries.
