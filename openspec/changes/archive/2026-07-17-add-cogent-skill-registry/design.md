## Context

`ossify-cogents` currently has no config file, no persistence layer, and a single vertical slice (`--version`). This change is the first to touch `domain/`, `ports_in/`, `ports_out/`, `application/`, and `adapters/` all at once, and its shape becomes the template the future lock-file feature will copy. `ossify-cogents.json` is not a pure config file — it is hand-edited by developers *and* mutated by the CLI (`registry add`), so persistence has to be safe for both.

## Goals / Non-Goals

**Goals:**
- Track third-party skill sources (git or local) in a registry section of `ossify-cogents.json`, with schema validation via pydantic.
- `registry get` / `registry add` / `config verify` CLI commands.
- A workspace-root resolution mechanism usable by every command, not just registry ones.
- A config persistence pattern (section-keyed, round-trip safe) that later features (lock file, target mappings) can reuse without rework.

**Non-Goals:**
- Capability/target mapping (how source files map into the project) — separate future change.
- Business-rule validation beyond schema shape + duplicate `id` — `config verify`'s deeper validation is deferred.
- The lock file itself.
- Any network calls (e.g. hitting GitHub for a real repo description) — `id`/`name`/`description` inference on `registry add` is pure string parsing of the given uri.

## Decisions

### Registry entry schema: one `Source` model + a validator, not a discriminated union
`domain/skill_registry.py` holds a single `Source {uri, ref: str | None = None}` model, used for both `git` and `local` entries, plus `SkillSource {id, name, description, source_type: Literal["git","local"], source: Source}`. A `model_validator` on `SkillSource` enforces the coupling that used to be structural: `ref` must be unset when `source_type == "local"`, and defaults to `"main"` when `source_type == "git"` and `ref` is omitted; violating this raises `InvalidRegistryEntryError`. Originally this was two separate frozen models (`GitSource`/`LocalSource`) discriminated on `source_type` specifically so a `local` entry couldn't structurally accept a `ref` — reconsidered in favor of one model because the codebase-wide preference is fewer types or single pillar responsibility, and the same guarantee is achievable with a validator instead of type structure; the behavioral contract (see `specs/skill-registry/spec.md`'s "Local entry has no ref concept" / "Mismatched source flag rejected" scenarios) is unchanged either way.

### `domain/ossify_config.py` centralizes section keys — `OssifyConfig` + `ConfigSection`
`OssifyConfig` is the whole-config domain entity: it knows how to convert to/from raw JSON and how to read/replace one named section without disturbing the others. `ConfigSection` (defined alongside it) is the single place that maps a use case to its on-disk section key — e.g. `ConfigSection.SKILL_REGISTRY = "ossify-skills-registry"` — rather than that constant living next to `SkillSource` in `skill_registry.py`. This keeps `OssifyConfig` the authority on "what sections exist and what they're called," which every future config-backed feature (lock file, target mappings) looks up rather than redefining.

### `ports_in.RegistryPort` bundles get+add — a deliberate exception
The existing pattern is 1 port : 1 verb-phrase use case (`VersionPort` ↔ `GetVersion`). Registry read and write don't split cleanly into two independent single-purpose use cases the way the codebase's convention prefers, so `RegistryPort` exposes both `get_all()` and `add(...)`, implemented by one application class, `RegistryService`. It is deliberately *not* named as a verb phrase (e.g. not `ManageRegistry`) to signal it's the one exception to the naming rule in `.claude/rules/python_style.md`, rather than a copy-paste template for future ports. `OssifyConfigPort` (renamed from the earlier working name `ConfigVerifierPort`) ↔ `VerifyConfig` keeps the normal 1:1 verb-phrase shape, and exposes only `verify()` for now — room is left for it to grow additional methods if `ossify-cogents config` gains more subcommands later, without renaming it again.

### `application/services/` for logic shared across use cases
Two application-level services, each a single pillar, sit under `application/services/` and are used by the top-level use cases rather than duplicating logic in both: `SourceInferenceService` (pure uri string-parsing → inferred `id`/`name`/`description`, no I/O) is used by `RegistryService.add`; `RegistryValidator` (duplicate-`id` + business-rule checks against `SkillSource` entries) is used by *both* `RegistryService.add` and `VerifyConfig.verify`, since both need the identical duplicate-id rule and it would otherwise be duplicated between them.

### Config persistence: generic `OssifyConfigAdapter` + thin `SkillRegistryAdapter` proxy
`ports_out.ConfigRepository` is generic and section-keyed (`read_section(key, model) -> T | None`, `write_section(key, value)`), implemented by `adapters/ossify_config_adapter.py` (`OssifyConfigAdapter`) — adapters live flat under `adapters/`, no `persistence/` subfolder, since one subfolder for a single concern added no clarity. It loads the raw JSON, reads/writes only the requested top-level key via `domain.OssifyConfig`'s section logic, and preserves every other key untouched via an atomic write (temp file + rename) — necessary because the file is hand-edited and may contain sections this codebase doesn't model yet. `ports_out.RegistryRepository` (`get_all`/`add`) is a separate, registry-specific port whose adapter, `adapters/skill_registry_adapter.py` (`SkillRegistryAdapter`), is a thin proxy composing an `OssifyConfigAdapter` instance (calls `read_section(ConfigSection.SKILL_REGISTRY, ...)`/`write_section(ConfigSection.SKILL_REGISTRY, ...)`). This keeps `RegistryService` decoupled from generic file mechanics, and gives the future lock-file feature the same two-layer pattern to copy (its own thin adapter proxying the same `OssifyConfigAdapter`). `adapters/workspace_adapter.py` (`WorkspaceAdapter`) implements `WorkspaceLocator` the same way — it represents the dev repo folder on disk (walk-up for `.git`/`ossify-cogents.json`, cwd fallback).

### Workspace root resolution: a locator that never errors
`ports_out.WorkspaceLocator.resolve(explicit: Path | None) -> Path`:
1. If `--workspace`/`-ws` was passed, return it.
2. Otherwise walk up from cwd looking for a `.git` directory or an `ossify-cogents.json` file, whichever is found first (closest directory wins); return that directory.
3. Otherwise return cwd (`./`).

The locator always returns *a* path — it never raises. Whether a usable config file exists there is left to each use case: `registry get` / `config verify` ask `ConfigRepository` for the file, and if it's absent raise `ConfigNotFoundError` ("no config found here"); `registry add` treats the same absence as "create a fresh config here" instead of erroring. Rejected alternative: a `--force` flag gating cwd fallback — rejected because it introduced an inconsistency between read and write commands for no benefit once the locator itself was made non-erroring; the "found or not" fact is uniform, only the reaction differs per use case.

### CLI: positional `uri` with `--source.uri` as an explicit alias, dotted `--source.*` flags
`registry add` takes `uri` as an optional positional argument and `--source.uri` as an equivalent named flag writing into the same value (usage error if both given and they disagree). All `source` fields use dotted flag names (`--source.uri`, `--source.ref`) to mirror the nested JSON schema path (`source.ref`), rather than flattened names. `--source-type` (defaulting to `git`) governs which dotted flags are valid; passing a `source.*` flag that doesn't apply to the given `source-type` (e.g. `--source.ref` with `--source-type local`) is a CLI-level usage error, not a domain validation error — it should never reach `RegistryService`.

## Risks / Trade-offs

- [Round-trip-safe JSON rewriting is more complex than a naive parse-and-dump] → Mitigated by scoping `ConfigRepository` to section-keyed reads/writes from the start, so the complexity is paid once here rather than reworked when a second config section (lock file, mappings) is added later.
- [`RegistryPort` bundling get+add breaks the established 1-port-1-verb convention] → Documented explicitly in this design doc and via naming (`RegistryService`, not a verb phrase) so it reads as a deliberate, isolated exception rather than setting a new precedent by accident.
- [Collapsing `GitSource`/`LocalSource` into one `Source` model moves the git/local coupling from "impossible by construction" to "enforced by a validator"] → Mitigated by `RegistryValidator` and `SkillSource`'s `model_validator` being the single place this rule lives, exercised directly by the "Local entry has no ref concept" and "Mismatched source flag rejected" spec scenarios — a missed validator branch fails a test, not silently accepted data.
- [Workspace walk-up finding an unrelated `.git` or `ossify-cogents.json` higher up the tree than intended, e.g. in a monorepo] → Mitigated by `--workspace`/`-ws` being available as an explicit override on every command.
- [Atomic write (temp file + rename) is platform-sensitive] → Standard `tempfile` + `os.replace` is atomic on both POSIX and Windows for same-volume renames; no cross-volume writes are expected for a project-local config file.

## Open Questions

- Exact rendering/output format for `config verify` (pass/fail summary vs. per-error detail) is left to implementation; not spec-critical for this change.
- Whether the future lock file reuses `RegistryRepository`'s proxy pattern verbatim or needs its own shape is deferred to that change.
