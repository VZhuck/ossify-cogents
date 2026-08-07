## Why

The README only documents `uv sync` / `uv run` and a bare registry example — there's no path to installing the CLI globally, no explanation of how `install` actually works (cache location, copy-not-fetch, no lock file yet), and no guidance for hand-editing a config beyond the empty scaffold `ossify init` writes. Separately, `schema/v1.json` exists but is never wired to a written config, so editors can't offer autocomplete/validation on `ossify-cogents.json` today. Both gaps block a new user's first real session with the tool.

## What Changes

- `ossify init` writes a `"$schema"` key into the generated `ossify-cogents.json`, pointing at the raw GitHub URL for `schema/v1.json` on `main`, so editors (e.g. VS Code) get live autocomplete/validation out of the box.
- README expanded into the full getting-started experience: description, Prerequisites, Install (install/verify/update/uninstall), and Getting Started (init → add first registry item with a full worked config example → install), plus an Advanced Topics section linking to `/docs` with a one-line description per page.
- New `/docs` folder for advanced/reference material not needed for a first successful run:
  - `docs/configuration.md` — `ossify-cogents.json` anatomy, the `$schema` key and IDE autocomplete, discovery definitions, wildcard (`fnmatch`) semantics for `agents`/`skills`/`commands`/`rules`, and an explicit callout that `target-platforms: ["*"]` is **not** supported (passes `config verify` but fails at `install` time) — plus a walkthrough of updating a config past the default empty scaffold.
  - `docs/install-process.md` — cache location (`platformdirs.user_cache_dir("ossify-cogents")`, `OSSIFY_CACHE_DIR` override), one cache dir per normalized source URI, always-refetch-then-copy-from-cache behavior, and that there is no lock file yet (aspirational, contradicts current CLAUDE.md wording).
  - `docs/development.md` — clone + `uv sync` + `uv run` + tests/lint, for contributors who want to run from source instead of installing globally.

## Capabilities

### New Capabilities
(none — this change only adds documentation and a docs-worthy tweak to existing scaffold output; no new user-facing capability is introduced)

### Modified Capabilities
- `config-init`: `ossify init` additionally writes a `"$schema"` field (pointing at the raw GitHub URL for `schema/v1.json`) into the scaffolded `ossify-cogents.json`.

## Impact

- Code: `src/application/_init_config.py` (and/or `src/domain/_defaults.py`) gains the `$schema` field in the written config; `schema/v1.json` itself is unaffected.
- Docs: `README.md` rewritten to carry the full getting-started flow; new `docs/configuration.md`, `docs/install-process.md`, `docs/development.md`.
- No CLI flags, ports, or schema-file (`schema/v1.json`) shape changes — `additionalProperties: true` at the top level already tolerates an extra `$schema` key without a schema edit.
