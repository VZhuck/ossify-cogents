## Context

`ossify init` currently writes two sections (`ossify-skills-registry`, `discovery-definitions`) via `ConfigRepository.write_section` calls in `src/application/_init_config.py`, keyed by `ConfigSection` enum values that map to modeled pydantic types. The top-level config schema (`schema/v1.json`) already declares `additionalProperties: true`, so an extra top-level key needs no schema change. `schema/v1.json` itself is not currently published anywhere with a stable URL other than its path in the repo (`schema/v1.json` on `main`).

The project is not published to PyPI; `pyproject.toml` has no `[project.urls]` and the only working install path today is `uv sync` from a local clone. The git remote is `https://github.com/VZhuck/ossify-cogents.git`.

## Goals / Non-Goals

**Goals:**
- `ossify init` writes a `"$schema"` key so any config it scaffolds is autocompletable/validatable in editors that honor JSON Schema's `$schema` convention (VS Code, IntelliJ, etc.) without extra user setup.
- Document the actual, current `install` behavior (cache location, always-refetch, copy-from-cache, no lock file) so users aren't misled by the lock-file description in CLAUDE.md.
- Document a real path to a global install (`uv tool install git+...`) and flag PyPI as not yet available, without promising a timeline.
- Document the only way, today, to move a config past the empty default scaffold: hand-editing JSON plus `config verify`.

**Non-Goals:**
- Not implementing `registry set`/`edit` or any other granular config-mutation command — docs describe the current hand-edit workflow, not a new one.
- Not implementing the lock file — docs describe its absence as current-state fact.
- Not fixing the `target-platforms: ["*"]` gap (accepted by `config verify`, rejected at `install`) — docs call it out as a known limitation; the fix is left for a separate change.
- Not publishing to PyPI — the README/docs carry a "not yet available" disclaimer only.

## Decisions

**`$schema` value is a hardcoded raw GitHub URL pinned to `main`**: `https://raw.githubusercontent.com/VZhuck/ossify-cogents/main/schema/v1.json`. A relative path (e.g. `./schema/v1.json`) doesn't work because the config file lives in the *user's* project, not next to a copy of `schema/v1.json` — the tool is installed globally via `uv tool install`, and nothing ships `schema/v1.json` alongside the user's repo. A raw GitHub URL is resolvable by editors with zero extra setup. Pinning to `main` (rather than a release tag) is a deliberate simplification: the project has no release/tag convention yet, so version-pinning the schema reference is deferred until one exists. This is written once, in `_defaults.py` or directly in `_init_config.py`, as a literal constant — not derived from installed package version or git state at runtime.

**Global install is documented via `uv tool install git+https://...`, not PyPI**: this works today with the existing `[project.scripts]` entry point and requires no publishing step. The README's install section leads with this command and includes a short "PyPI package: under construction, not yet published" note rather than omitting PyPI entirely — the user asked for both.

**Getting-started content lives in README, reference/advanced content lives under `/docs`**: after drafting a separate `docs/getting-started.md`, the user asked to fold it back into README with explicit sections (Prerequisites, Install with install/verify/update/uninstall subsections, Getting Started with init/add-first-registry-item/install subsections) — this is the flow a brand-new user needs immediately, so it shouldn't require a click-through. `docs/configuration.md`, `docs/install-process.md`, `docs/development.md` stay separate as advanced/reference material, linked from an "Advanced Topics" section at the bottom of README with a one-line description each.

**Config-update guidance is a hand-editing walkthrough, not a new CLI feature**: confirmed via source reading that `registry add` only appends a whole `SkillSource`, `config verify` is read-only validation, and no command sets `install.*` or `discovery` on an existing entry. `docs/configuration.md` walks through editing the scaffolded JSON directly: adding `discovery` ids, setting `install.agents`/`skills`/`commands`/`rules` to specific globs or `"*"`, and adding `by-pattern` entries — then running `config verify`.

**The `target-platforms: ["*"]` gap gets a callout, not a fix**: `InstallResolver._validate_target_platforms` accepts `"*"` at verify time, but `TargetLayout.resolve` has no wildcard fan-out and raises `TargetLayoutUnavailableError` at install time. Docs state plainly that `"*"` only works for `agents`/`skills`/`commands`/`rules`, and `target-platforms` needs explicit platform names (`claude`, `copilot`, `codex` — noting `cursor`/`windsurf` are declared supported but have no target layout yet either).

## Risks / Trade-offs

- **Schema URL drift** → pinning `$schema` to `main` means a user's editor will validate against whatever the schema looks like on `main` at the time they open their editor, not the schema version that shipped with their installed CLI. Mitigation: acceptable for now given no release/tag convention exists; documented in `configuration.md` as a known limitation, revisit once versioned releases exist.
- **Raw GitHub URL requires network access for schema-based editor validation** → editors that can't reach `raw.githubusercontent.com` (offline, restrictive proxies) silently lose autocomplete, though `ossify-cogents.json` remains fully functional since the CLI parses it independently of `$schema`. No mitigation needed — same trade-off every `$schema`-via-URL config format makes (e.g. `package.json` schemas).
- **Documenting a real bug (`target-platforms: ["*"]`)** → risks reading as "known issue, not fixed" if the user expected this change to also patch it. Mitigation: explicitly scoped out in Non-Goals and called out to the user as a candidate for a follow-up change.

## Open Questions

None outstanding — sequencing, `$schema` value, and doc scope were confirmed with the user before this design was written.
