## 1. Domain

- [x] 1.1 Create `src/domain/skill_registry.py`: `Source {uri, ref: str | None = None}` and `SkillSource {id, name, description, source_type: Literal["git","local"], source: Source}` (frozen pydantic models), with a `model_validator` on `SkillSource` enforcing `ref` unset when `source_type == "local"` and defaulted to `"main"` when `source_type == "git"` and omitted
- [x] 1.2 Create `src/domain/ossify_config.py`: `ConfigSection` (maps use case -> section key, e.g. `SKILL_REGISTRY = "ossify-skills-registry"`) and `OssifyConfig` (whole-config entity: to/from raw JSON, read/replace one section by `ConfigSection` + model, preserving other sections)
- [x] 1.3 Remove the now-empty placeholder comment in `src/domain/models.py` (models moved to `skill_registry.py`/`ossify_config.py`, so this file is no longer needed — delete it, updating `pyproject.toml`/imports if anything referenced it)
- [x] 1.4 Add `ConfigNotFoundError`, `DuplicateSourceIdError`, `InvalidRegistryEntryError` to `src/domain/errors.py`, subclassing `OssifyError`

## 2. Outbound ports (ports_out)

- [x] 2.1 Add `WorkspaceLocator` protocol (`ports_out/_workspace_locator.py`): `resolve(explicit: Path | None) -> Path`
- [x] 2.2 Add `ConfigRepository` protocol (`ports_out/_config_repository.py`): `read_section(section: ConfigSection, model) -> T | None`, `write_section(section: ConfigSection, value)`
- [x] 2.3 Add `RegistryRepository` protocol (`ports_out/_registry_repository.py`): `get_all() -> list[SkillSource]`, `add(entry: SkillSource) -> None`
- [x] 2.4 Re-export all three from `ports_out/__init__.py`

## 3. Adapters (flat under adapters/, no persistence/ subfolder)

- [x] 3.1 Implement `WorkspaceAdapter` in `adapters/workspace_adapter.py` (implements `WorkspaceLocator`): `.git`/`ossify-cogents.json` walk-up, cwd fallback, never raises
- [x] 3.2 Implement `OssifyConfigAdapter` in `adapters/ossify_config_adapter.py` (implements `ConfigRepository`): section-keyed read/write via `domain.OssifyConfig`, preserves unrecognized top-level keys, atomic write (temp file + `os.replace`)
- [x] 3.3 Implement `SkillRegistryAdapter` in `adapters/skill_registry_adapter.py` (implements `RegistryRepository`), composing an `OssifyConfigAdapter` instance and using `ConfigSection.SKILL_REGISTRY` (no inheritance)

## 4. Inbound ports (ports_in) and application

- [x] 4.1 Add `RegistryPort` protocol (`ports_in/_registry.py`): `get_all()` + `add(...)`
- [x] 4.2 Add `OssifyConfigPort` protocol (`ports_in/_ossify_config.py`): `verify()`
- [x] 4.3 Implement `SourceInferenceService` (`application/services/_source_inference_service.py`): pure uri string-parsing -> inferred `id`/`name`/`description`, no I/O
- [x] 4.4 Implement `RegistryValidator` (`application/services/_registry_validator.py`): duplicate-`id` + business-rule checks against a list of `SkillSource`, raising `DuplicateSourceIdError`/`InvalidRegistryEntryError`
- [x] 4.5 Implement `RegistryService` (`application/_registry_service.py`): implements `RegistryPort`, depends on `RegistryRepository`; delegates inference to `SourceInferenceService` and validation to `RegistryValidator`
- [x] 4.6 Implement `VerifyConfig` (`application/_verify_config.py`): implements `OssifyConfigPort`, depends on `ConfigRepository`; delegates business-rule validation to `RegistryValidator`
- [x] 4.7 Re-export from `ports_in/__init__.py` and `application/__init__.py`

## 5. CLI

- [x] 5.1 Add global `--workspace`/`-ws` option to `cli/_app.py`, resolved once per invocation via the container's `WorkspaceLocator`
- [x] 5.2 Add `registry` Typer sub-app (`cli/_registry.py`) with `get` (Rich table output) and `add` (positional `uri` + `--source.uri` alias with conflict check, `--source-type` default `git`, dotted `--source.ref`, `--id`/`--name`/`--description` overrides, usage-error guard for mismatched `source.*` flags vs. `source-type`)
- [x] 5.3 Add `config` Typer sub-app (`cli/_config.py`) with `verify`
- [x] 5.4 Mount `registry` and `config` sub-apps on the root `app` in `cli/_app.py`
- [x] 5.5 Translate domain errors (`ConfigNotFoundError`, `DuplicateSourceIdError`, `InvalidRegistryEntryError`) to clean CLI error output + non-zero exit codes at the command boundary

## 6. Wiring

- [x] 6.1 Register `WorkspaceAdapter`, `OssifyConfigAdapter`, `SkillRegistryAdapter` in `container.py`
- [x] 6.2 Register `RegistryService` and `VerifyConfig` use cases in `container.py`, wired to their adapters (and `SourceInferenceService`/`RegistryValidator` where needed)
- [x] 6.3 Update `pyproject.toml` hatch wheel `packages`/`force-include` if any new top-level modules were introduced (none needed — all new files live inside existing top-level packages, verified via `uv run lint-imports` and `uv run pytest`)

## 7. Tests

- [x] 7.1 Unit tests for `Source`/`SkillSource`/`OssifyConfig`/`ConfigSection` validation (`ref` default on git, local entry rejects `ref`)
- [x] 7.2 Unit tests for `WorkspaceAdapter`: explicit override, `.git` walk-up, config-file walk-up, cwd fallback
- [x] 7.3 Unit tests for `OssifyConfigAdapter`: round-trip preservation of unrecognized sections, atomic write behavior
- [x] 7.4 Unit tests for `RegistryService`/`SourceInferenceService`/`RegistryValidator`: duplicate-id rejection, inference from uri, explicit overrides win
- [x] 7.5 Unit tests for `VerifyConfig`: valid config, schema violation, duplicate id, missing config file
- [x] 7.6 CLI tests (Typer `CliRunner`) for `registry get`, `registry add` (including positional/`--source.uri` conflict and mismatched `source.*`/`source-type` usage errors), `config verify`, and `--workspace` override
- [x] 7.7 Run `uv run lint-imports` to confirm no architecture-boundary violations were introduced

## 8. Documentation

- [x] 8.1 Update `CLAUDE.md`/README (if present) with the new CLI commands and `ossify-cogents.json` registry schema example
