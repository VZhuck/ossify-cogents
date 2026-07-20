## Why

Registry entries currently only say *where* a skill source lives (`source-type`, `source`); nothing says *how* to find agents/skills/commands/rules inside it once it's fetched. Different upstreams lay their files out differently (a plain open-standard folder layout vs. a Claude marketplace layout), so each registry entry needs to declare which discovery strategy/strategies apply to it, and the tool needs a place to define custom strategies alongside a set of built-in ones.

## What Changes

- Add a `discovery` field (list of strategy ids) to `SkillSource` registry entries. Empty list is valid (a source with no declared strategy is inert, not an error).
- Add a new root config section, `discovery-definitions`, holding user-defined custom discovery-strategy definitions (`id`, `mappings` for `agents`/`skills`/`commands`/`rules`/`by-pattern`). This section is custom-only — built-in strategies are not written here.
- Ship a small set of built-in discovery strategies in code (starting with `ossify-open-standard`), each with an `ossify-`-prefixed id, resolvable by id without appearing in the config file. **NOTE:** the `ossify-` prefix is reserved for built-in discovery strategies by convention/documentation only — see below.
- Extend `config verify` to check that every id in every entry's `discovery` list resolves to either a built-in or a `discovery-definitions` entry, and to reject duplicate `id`s across the combined built-in ∪ `discovery-definitions` pool (mirroring the existing registry duplicate-`id` rule). A custom entry re-using a built-in's id (e.g. `ossify-open-standard`) fails this same duplicate check — reported as "already defined," not as a dedicated reserved-prefix violation.
- Adopt **kebab-case** as the single on-disk convention for all config field names (via a shared model base with an alias generator), and migrate the already-shipped `source_type` field to `source-type` in the same pass — closing the existing prose-vs-serialization mismatch.
- Generate a JSON Schema (`schema/v1.json`) from the known config-section models so `ossify-cogents.json` can be validated by editors/CI outside the CLI.
- **Non-goal / explicitly deferred**: materializing a source's actual file tree, running strategy globs against real files, union-merging matches across multiple strategies, and detecting file-level category clashes. Those require source materialization (git clone / local read) that doesn't exist in this codebase yet, and belong to a future "resolve/sync" change. This change only validates the *configuration*, not the *source contents*.

## Capabilities

### New Capabilities
- `skill-discovery`: the `discovery-definitions` config section, its schema (custom strategy definitions with per-category glob mappings plus a free-form `by-pattern` bucket), the built-in strategy registry, and the reserved-`ossify-`-prefix rule.

### Modified Capabilities
- `skill-registry`: `SkillSource` gains a `discovery: list[str]` field (default `[]`); its `source_type` field is renamed to `source-type` on disk under the new kebab-case convention.
- `config-verify`: adds validation that every `discovery` id on every registry entry resolves to a known strategy (built-in or custom), and that no `discovery-definitions` entry shares an `id` with another `discovery-definitions` entry or with a built-in (the latter is how an `ossify-`-prefixed custom id gets caught).

## Impact

- New shared kebab-case config base model in `domain/` (e.g. `ConfigModel` with `alias_generator` + `populate_by_name`); `Source`/`SkillSource` (and the new discovery models) inherit it. `source_type` → `source-type` on disk.
- `domain/skill_registry.py`: `SkillSource` gains `discovery: list[str] = []` and inherits the kebab base.
- New `domain/discovery.py` (or similar): `DiscoveryDefinition`, `Mapping`/`GlobRule`/`ByPatternRule` models. No reserved-prefix validator — see design.md for why.
- New packaged built-in strategy data (e.g. `domain/_builtins.py`), mirroring the existing pattern of code-defined, non-persisted data.
- `domain/ossify_config.py`: new `ConfigSection.DISCOVERY_DEFINITIONS` entry.
- `domain/errors.py`: new `UnresolvableDiscoveryIdError` and `DuplicateDiscoveryIdError` (subclassing `OssifyError`).
- `adapters/ossify_config_adapter.py`: `read_section`/`write_section` round-trip by alias (`by_alias=True` on dump) so kebab keys are emitted/accepted.
- `application/_verify_config.py` plus a new service under `application/services/`: id-resolution, reserved-prefix, and discovery duplicate-`id` checks, following the existing `RegistryValidator` pattern.
- `cli/_config.py`: `config verify` output gains the new failure cases; no new commands.
- New `scripts/generate_schema.py` + `schema/v1.json` composing the known section models; the quality gate regenerates and diffs it.
- `.claude/rules/python_style.md`: record the kebab-case config-field convention.
- `tests/e2e/test_registry_flow.py`: update the `source_type` on-disk assertion to `source-type`.
- No source materialization, glob execution, or adapters for reading actual source trees — out of scope for this change.
