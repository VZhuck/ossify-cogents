## 1. Kebab-case config convention

- [x] 1.1 Add a shared frozen config base model in `domain/` (e.g. `ConfigModel(BaseModel)` with `model_config = ConfigDict(frozen=True, alias_generator=to_kebab, populate_by_name=True)`); implement/choose the kebab alias generator
- [x] 1.2 Make `Source` and `SkillSource` inherit `ConfigModel`; confirm `source_type` now serializes as `source-type` and in-code construction (`source_type=...`) still works via `populate_by_name`
- [x] 1.3 Update `OssifyConfigAdapter.read_section`/`write_section` to round-trip by alias (`dump_python(..., by_alias=True)`; validation already accepts aliases)
- [x] 1.4 Update `tests/e2e/test_registry_flow.py` (and any fixtures) asserting `source_type` → `source-type` on disk
- [x] 1.5 Record the kebab-case config-field convention in `.claude/rules/python_style.md` under "Domain models"

## 2. Domain models

- [x] 2.1 Add `discovery: list[str] = []` field to `SkillSource` in `domain/skill_registry.py`
- [x] 2.2 Create `domain/discovery.py` (models inherit `ConfigModel`) with `GlobRule { type: Literal["file", "folder"], path: str }`, `ByPatternRule(GlobRule)` adding required `category: str`, `Mapping { agents, skills, commands, rules, by_pattern }` (all `list[...] = []`; `by_pattern` serializes as `by-pattern`), and `DiscoveryDefinition { id: str, type: Literal["custom"] = "custom", mappings: Mapping }` — no reserved-prefix `model_validator`; see 3.1 for how an `ossify-`-prefixed custom id is actually caught
- [x] 2.3 Add `UnresolvableDiscoveryIdError` and `DuplicateDiscoveryIdError` to `domain/errors.py`, subclassing `OssifyError`
- [x] 2.4 Add `ConfigSection.DISCOVERY_DEFINITIONS = "discovery-definitions"` to `domain/ossify_config.py`
- [x] 2.5 Create `domain/_builtins.py` with at least one built-in `DiscoveryDefinition` instance (`ossify-open-standard`), constructed directly in code — add a NOTE there that `ossify-` is the reserved prefix for built-ins by convention (enforced via the duplicate-id check in 3.1, not a model validator)

## 3. Discovery resolution service

- [x] 3.1 Create an `application/services/` piece (e.g. `_discovery_resolver.py`) that takes built-ins ∪ parsed `discovery-definitions` entries, rejects duplicate `id`s across that whole combined pool — i.e. a custom entry colliding with either another custom entry or a built-in (`DuplicateDiscoveryIdError`; this is also what catches an `ossify-`-prefixed custom id, reported as already-defined) — and exposes an id-resolution check
- [x] 3.2 Export it from `application/services/__init__.py`

## 4. `config verify` integration

- [x] 4.1 Extend `application/_verify_config.py` to read the `discovery-definitions` section (via existing generic `ConfigRepository.read_section`) alongside the registry section
- [x] 4.2 For each registry entry, validate every `discovery` id resolves via the new resolver service; collect unresolvable ids as violations
- [x] 4.3 Validate no `discovery-definitions` entry's `id` collides with a built-in's `id`, reporting `DuplicateDiscoveryIdError` (this is how the `ossify-` reserved prefix is actually enforced — see design.md)
- [x] 4.4 Validate no two `discovery-definitions` entries share an `id`, reporting `DuplicateDiscoveryIdError`
- [x] 4.5 Update CLI output in `cli/_config.py` (or wherever `config verify` renders results) to display the new violation types

## 5. Wiring

- [x] 5.1 Update `container.py` to supply the built-in strategy list to `VerifyConfig`/the resolver service

## 6. Tests

- [x] 6.1 Unit tests for the kebab-case round-trip: `source_type` reads/writes as `source-type`; construction by snake_case name still works
- [x] 6.2 Unit tests for `SkillSource.discovery` default-empty-list behavior
- [x] 6.3 Unit tests for `DiscoveryDefinition`/`Mapping`/`GlobRule`/`ByPatternRule` parsing, including the `by-pattern` (kebab) category field and `type` defaulting to `"custom"`
- [x] 6.4 Unit tests for the discovery resolver's duplicate-id rejection: two custom entries sharing an `id`, and a custom entry colliding with a built-in `id` (e.g. `ossify-open-standard`) — both rejected as already-defined, reported via `DuplicateDiscoveryIdError`
- [x] 6.5 Unit tests for the discovery-id resolution service (resolves to built-in, resolves to custom, unresolvable, duplicate-id rejected)
- [x] 6.6 Unit tests for `VerifyConfig` covering: valid config with resolvable discovery ids passes; unresolvable id fails; custom definition colliding with a built-in id fails; duplicate discovery id among custom entries fails
- [x] 6.7 Update/add CLI-level tests for `config verify`'s new failure output

## 7. Quality gate

- [x] 7.1 Create `scripts/generate_schema.py` composing the known section models (`list[SkillSource]` under `ossify-skills-registry`, `list[DiscoveryDefinition]` under `discovery-definitions`) into `schema/v1.json` with kebab keys (`by_alias=True`) and `additionalProperties: true` at the root; wire it as a runnable script (`pyproject.toml`/`uv run`)
- [x] 7.2 Generate `schema/v1.json` and commit it; the quality gate regenerates and diffs it to catch drift
- [x] 7.3 Run `uv run ruff check src tests`, `uv run mypy src`, `uv run lint-imports`, `uv run pytest` and fix any failures
