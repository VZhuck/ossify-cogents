## Why

ossify-cogents needs a durable, developer-editable record of which third-party skill/agent/rule sources (git repos or local folders) a project draws from, before any syncing or mapping logic can exist. Today there is no config file, no persistence layer, and no CLI surface beyond `--version` — this change introduces the first real capability (and, with it, the first config-file persistence pattern the project will reuse for the future lock file).

## What Changes

- Introduce `ossify-cogents.json` as a config file that is both hand-edited and CLI-mutated, holding a top-level `ossify-skills-registry` array of skill source entries.
- Each entry has `id`, `name`, `description`, `source-type` (`git` | `local`), and a nested `source` object — `{uri, ref}` for git, `{uri}` for local — validated as a discriminated union.
- Add `ossify-cogents registry get` — list all registered sources.
- Add `ossify-cogents registry add <uri>` — append a new source, inferring `id`/`name`/`description` from the URI/path when not explicitly overridden, with dotted `--source.*` flags mirroring the nested schema.
- Add `ossify-cogents config verify` — validate the config file against the schema (business-rule validation beyond duplicate-id checks is out of scope for this change).
- Add a global `--workspace`/`-ws` option: resolves the project root explicitly, or via a `.git`/`ossify-cogents.json` walk-up from cwd, falling back to cwd itself. This resolver never errors — "no config file found at the resolved root" is a per-command concern, not a resolver concern.
- Establish the config persistence pattern: reads/writes are section-keyed and round-trip safe (unrecognized top-level sections are preserved untouched on write).

## Capabilities

### New Capabilities
- `skill-registry`: Domain model, validation, and CRUD (get/add) behavior for the `ossify-skills-registry` section of the config file — id uniqueness, git/local source shape, inference of defaults from a URI on add.
- `config-persistence`: Workspace root resolution, and section-keyed, round-trip-safe read/write of `ossify-cogents.json` (the `ConfigRepository`/`WorkspaceLocator` abstractions other config sections, including the future lock file, will reuse).
- `config-verify`: The `config verify` CLI command and schema-validation behavior/output.

### Modified Capabilities
- (none — no existing spec's requirements change; `cli-version` and `project-skeleton` are unaffected)

## Impact

- New `src/domain` models (`GitSource`, `LocalSource`, `SkillSource`, `OssifyConfig`) and errors (`ConfigNotFoundError`, `DuplicateSourceIdError`, `InvalidRegistryEntryError`).
- New `ports_out` protocols (`WorkspaceLocator`, `ConfigRepository`, `RegistryRepository`) and adapters implementing them under `src/adapters/persistence/`.
- New `ports_in` protocols (`RegistryPort`, `ConfigVerifierPort`) and application use cases (`RegistryService`, `VerifyConfig`).
- New CLI sub-apps (`registry`, `config`) mounted in `src/cli/_app.py`, plus a new global `--workspace`/`-ws` option.
- `src/container.py` wiring for all of the above.
- No changes to existing `--version` behavior or files.
