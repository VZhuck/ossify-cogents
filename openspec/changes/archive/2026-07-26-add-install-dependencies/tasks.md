## 1. Domain models

- [x] 1.1 Add `ByPatternDependency` model (`category: str`, `action: Literal["init", "replace", "json_merge"]`) inheriting `ConfigModel`, in a new `domain/dependencies.py`
- [x] 1.2 Add `Dependencies` model in `domain/dependencies.py`: `target_platforms`, `agents`, `skills`, `commands`, `rules` (all `list[str] = []`) and `by_pattern: list[ByPatternDependency] = []`, inheriting `ConfigModel` (kebab aliases give `target-platforms`, `by-pattern`)
- [x] 1.3 Add a non-optional `install: Dependencies = Field(default_factory=Dependencies)` field to `SkillSource` in `domain/skill_registry.py` (on-disk key stays `install`; domain type is `Dependencies`). It is never `None`; an omitted `install` deserializes to an empty `Dependencies` block (a stub that installs nothing)
- [x] 1.4 Unit tests: `Dependencies`/`ByPatternDependency` parse from kebab-case JSON; invalid `action` rejected; a `SkillSource` parsed without `install` yields an empty `Dependencies` block (not `None`); a populated `install` round-trips

## 2. Target port + adapter

- [x] 2.1 Define `TargetPort` `Protocol` in `ports_out/` with action-aware write operations — `create_if_absent(path, data)`, `override(path, data)`, `merge(path, data)` (plus `exists(path) -> bool` if needed by the application) — where an adapter MAY raise `UnsupportedTargetActionError` for an operation it cannot perform; re-export from `ports_out/__init__.py`
- [x] 2.2 Add `UnsupportedTargetActionError` to `domain/errors.py` (subclass of `OssifyError`)
- [x] 2.3 Implement a filesystem/JSON-capable target adapter under `adapters/targets/`, rooted at a configurable target folder (workspace root), using `pathlib.Path`: `create_if_absent`, `override`, and `merge` (parse both sides as JSON and deep-merge — recurse on object/object, source wins on scalar conflict — via an internal pure merge helper)
- [x] 2.4 Register the target adapter in `container.py`, rooted at the resolved workspace
- [x] 2.5 Unit tests for the adapter (tmp_path): each action; `merge` deep-merge cases (nested objects, scalar override, non-object conflict); unsupported action raises `UnsupportedTargetActionError`

## 3. Install resolver (application)

- [x] 3.1 Add `_install_resolver` service in `application/services/` mirroring `_discovery_resolver`
- [x] 3.2 Implement static validation: `by-pattern.category` resolves against the entry's discovery strategies' by-pattern categories; `target-platforms` are supported platform ids or `"*"` (platform id set injected from container via `domain._builtins.SUPPORTED_TARGET_PLATFORMS`)
- [x] 3.3 Implement dynamic fixed-category glob matching against discovered ids using `fnmatchcase` (case-sensitive, deterministic); `"*"` matches all
- [x] 3.4 Implement empty-match policy: exact-literal-matching-zero raises an install error; glob-matching-zero yields a warning (surface warnings without failing)
- [x] 3.5 Define/extend domain errors for unresolvable install by-pattern category, unknown target platform, and unmatched exact selection
- [x] 3.6 Unit tests for static and dynamic resolution, including the exact-vs-glob empty-match policy and `"*"` expansion

## 4. Config verify integration (static checks)

- [x] 4.1 Wire the resolver's static install validation into the existing verify use case (`application/_verify_config.py`)
- [x] 4.2 Inject the supported target-platform id set into verify via `container.py`, analogous to built-in discovery strategies
- [x] 4.3 Ensure verify stays offline (no fetch) and reports unresolvable by-pattern category / unknown target-platform with non-zero exit
- [x] 4.4 Tests: valid install passes; unresolvable by-pattern category fails; unknown target-platform fails; `"*"` target-platform passes

## 5. Sync consumption + apply — DEFERRED (blocked on the unbuilt `SyncCapabilities` feature)

> `SyncCapabilities` and the lock flow do not exist yet. These tasks apply the
> resolved `install` selections during sync and cannot be built until that
> feature lands. The pieces they will consume (the `TargetPort` + adapter, the
> `InstallResolver.select` matching, the action→operation mapping) are all
> implemented and unit-tested above.

- [ ] 5.1 Have `SyncCapabilities` consume each entry's `install`: run discovery, resolve fixed-category selections (section 3), collect selected items
- [ ] 5.2 Application-layer layout map: translate each selected fixed-category item into every target-platform layout (`"*"` = all registered adapters); apply implicit `replace` via `TargetPort`
- [ ] 5.3 Application-layer by-pattern apply: compute destination = discovery `path`, map the entry's `action` to a `TargetPort` operation (`init`→`create_if_absent`, `replace`→`override`, `json_merge`→`merge`) and invoke it; the adapter performs the merge internally
- [ ] 5.4 Feed the resolved installed items into the existing lock flow
- [ ] 5.5 Tests: end-to-end fixed-category install into multiple platform layouts; by-pattern `init`/`replace`/`json_merge` behavior against pre-existing files

## 6. Registry update invariant

- [x] 6.1 Ensure the registry add/update use case patches the stored entry (overlay identity/source/discovery), never reconstructs it, so `install` is carried through — holds because `install` is a model field: `add` reads existing entries as full `SkillSource` models and rewrites them, so their `install` survives (verified by the sibling-preservation e2e test)
- [x] 6.2 Dedicated test: updating an entry's source metadata (via `model_copy`) preserves the `install` block; e2e: adding an entry preserves a hand-authored `install` on a sibling (round-trip normalizes omitted empty categories to `[]` but drops nothing)

## 7. Schema + wiring

- [x] 7.1 `install` is a field on `SkillSource`, already composed via `list[SkillSource]` in `scripts/generate_schema.py` — no section-map change needed
- [x] 7.2 Regenerate `schema/v1.json` (idempotent; `schema-drift` hook passes)
- [x] 7.3 Run the full quality gate: `ruff` (lint+format), `mypy --strict`, `uv run lint-imports`, `pytest` — all green (95 tests)
