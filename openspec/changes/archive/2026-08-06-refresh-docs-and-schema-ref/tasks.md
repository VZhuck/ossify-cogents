## 1. `$schema` in scaffolded config

- [x] 1.1 Add the `$schema` constant (`https://raw.githubusercontent.com/VZhuck/ossify-cogents/main/schema/v1.json`) to `src/domain/_defaults.py` (or directly in `_init_config.py`)
- [x] 1.2 Update `InitConfig.init` (`src/application/_init_config.py`) to write the `$schema` key at the top level of the scaffolded `ossify-cogents.json`, for both the fresh-workspace and `--force` paths
- [x] 1.3 Confirm `schema/v1.json`'s `additionalProperties: true` accepts the extra top-level key (no schema-file change expected) by running `ossify-cogents config verify` against a freshly-init'd config
- [x] 1.4 Update/add unit tests covering `InitConfig.init` to assert the written config contains the `$schema` field, for both plain `init` and `init --force`
- [x] 1.5 Update e2e init test(s), if any, that snapshot/assert full scaffolded config contents

## 2. README rewrite (full getting-started flow, folded in from a standalone draft)

- [x] 2.1 H1 pitch/description, H2 Prerequisites (Python 3.12+, uv)
- [x] 2.2 H2 Install, with H3 subsections: Install (`uv tool install git+...` + PyPI "under construction" disclaimer), Verify (`--version`), Update (`uv tool upgrade` + reinstall fallback), Uninstall (`uv tool uninstall`)
- [x] 2.3 H2 Getting Started, with H3 subsections: Initialize a repo (`init` + `config verify`), Add your first registry item (`registry add` then a full worked `ossify-cogents.json` example with a second registry entry, multiple discovery strategies, `by-pattern`, re-running `config verify`), Install dependencies (`install`)
- [x] 2.4 H2 Advanced Topics linking to each `/docs` page with a one-line description
- [x] 2.5 Remove the now-redundant `uv sync`/plain-registry-example content that the old README had (superseded by the above)

## 4. `docs/configuration.md`

- [x] 4.1 Document `ossify-cogents.json` top-level shape (`$schema`, `ossify-skills-registry`, `discovery-definitions`) referencing `schema/v1.json`
- [x] 4.2 Document the `$schema` field and how it enables editor autocomplete/validation (VS Code et al.), noting it's pinned to `main` (no versioned releases yet)
- [x] 4.3 Document discovery definitions: built-in `ossify-open-standard` (folder-per-category under a source's root) vs. custom `discovery-definitions` entries, and how discovered ids are derived (folder child name / file stem)
- [x] 4.4 Document `install` selection semantics: `fnmatch` globs against discovered ids, `"*"` matches everything, empty/absent selects nothing — for `agents`/`skills`/`commands`/`rules`
- [x] 4.5 Add an explicit callout: `target-platforms: ["*"]` is NOT supported — passes `config verify` but fails at `install` time with `TargetLayoutUnavailableError`; use explicit platform names (`claude`, `copilot`, `codex`)
- [x] 4.6 Add a walkthrough taking the default `ossify init` scaffold (empty selections) to a working config: adding a `discovery` id, setting `install.agents`/`skills`/etc. to specific globs or `"*"`, adding a `by-pattern` entry, then re-running `config verify`
- [x] 4.7 Note there is currently no CLI command to edit `install.*`/`discovery` on an existing registry entry — hand-editing the JSON is the only path today

## 5. `docs/install-process.md`

- [x] 5.1 Document cache location: `platformdirs.user_cache_dir("ossify-cogents")`, override via `OSSIFY_CACHE_DIR`
- [x] 5.2 Document one cache directory per normalized source URI (`<cache_root>/repos/<slug>-<sha256[:8]>`), and that switching `ref` reuses the same cache dir
- [x] 5.3 Document that every `install` run does `git fetch --all --tags --prune` (or a full clone if uncached) before checkout — no staleness-skip optimization
- [x] 5.4 Document that files are copied from the local cache clone into the target repo (`read_bytes`/`walk` over the on-disk clone) — GitHub is never read from per-file
- [x] 5.5 State plainly that there is no lock file (`ossify-cogents.lock.json`) implemented yet, despite CLAUDE.md's description — every install re-fetches and re-writes; flag this as a documented future feature, not current behavior

## 6. `docs/development.md`

- [x] 6.1 Document cloning the repo and running from source via `uv sync` + `uv run ossify-cogents ...`
- [x] 6.2 Document running tests/lint/type-check (`uv run pytest`, `uv run ruff check`, `uv run mypy`) per existing dev tooling in `pyproject.toml`

## 7. Verification

- [x] 7.1 Run `uv run pytest` and `uv run mypy` after the `$schema` code change
- [x] 7.2 Manually run `ossify-cogents init` in a scratch directory and confirm the written config opens with schema-based autocomplete in an editor that supports `$schema` (e.g. VS Code)
- [x] 7.3 Proofread the three `/docs` reference pages and the expanded README for consistency (terminology, command names, cross-links)
