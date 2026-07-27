## 1. Domain

- [x] 1.1 Add `DEFAULT_REGISTRY_ITEM` — a fully-specified `SkillSource` constant —
  as packaged code data (in `domain/_builtins.py`, or a sibling `domain/_defaults.py`):
  curated `id`/`name`/`description`, `source_type="git"`,
  `source=Source(uri="https://github.com/anthropics/skills", ref="main")`,
  `discovery=["ossify-open-standard"]`,
  `install=Dependencies(target_platforms=["claude"])` (all other lists default `[]`)
- [x] 1.2 Add `ConfigAlreadyExistsError(OssifyError)` to `domain/errors.py`
- [x] 1.3 Unit test: `DEFAULT_REGISTRY_ITEM` is a valid `SkillSource`; its `install`
  block round-trips (dump→load) to `target-platforms: ["claude"]` with all empty
  selection lists present; kebab-case keys (`source-type`, `target-platforms`,
  `by-pattern`) appear on dump

## 2. Inbound port + use case

- [x] 2.1 Define `InitPort` `Protocol` in `ports_in/` with `init(root: Path) -> None`;
  re-export from `ports_in/__init__.py`
- [x] 2.2 Implement `InitConfig` use case in `application/` (implements `InitPort`),
  depending on `ports_out.ConfigRepository`: if `config_repo.exists(root)` → raise
  `ConfigAlreadyExistsError`; else `write_section(root, ConfigSection.SKILL_REGISTRY,
  [DEFAULT_REGISTRY_ITEM], list[SkillSource])`
- [x] 2.3 Unit tests (fake/tmp `ConfigRepository`): empty workspace writes the
  default registry section; existing config raises `ConfigAlreadyExistsError` and
  performs no write

## 3. CLI

- [x] 3.1 Add a top-level `init` command on the root Typer app (`cli/_app.py` or a
  new `cli/_init.py`), resolving the workspace via the existing `resolve_root(ctx)`
  helper and calling `Container().init_use_case()`
- [x] 3.2 On `ConfigAlreadyExistsError` (and any `OssifyError`): print the message
  and exit non-zero; on success print a confirmation and exit zero

## 4. Wiring

- [x] 4.1 Register `InitConfig` as `init_use_case` in `container.py`, wired to the
  existing `ossify_config_adapter`

## 5. End-to-end + quality gate

- [x] 5.1 E2E test (`tests/e2e/`): `ossify init` in a tmp workspace creates
  `ossify-cogents.json`; the written file passes `config verify`; a second `init`
  exits non-zero and leaves the file byte-for-byte unchanged
- [x] 5.2 Run the full quality gate: `ruff` (lint+format), `mypy --strict`,
  `uv run lint-imports`, `pytest` — all green

## 6. Enhancement: example discovery definition + `--force`

- [x] 6.1 Add `DEFAULT_DISCOVERY_DEFINITION` (a `DiscoveryDefinition`) to
  `domain/_defaults.py`, id `example-standard` (no `ossify-` prefix, no built-in
  collision), `mappings` mirroring `ossify-open-standard` (a `folder` rule per
  fixed category)
- [x] 6.2 Add `delete(root: Path) -> None` to the `ConfigRepository` out-port and
  implement it on `OssifyConfigAdapter` (`unlink(missing_ok=True)`)
- [x] 6.3 Change `InitPort.init` to `init(root: Path, *, force: bool = False)`;
  update `InitConfig`: if exists and not force → raise; if exists and force →
  `delete(root)`; then write `SKILL_REGISTRY` (`[DEFAULT_REGISTRY_ITEM]`) and
  `DISCOVERY_DEFINITIONS` (`[DEFAULT_DISCOVERY_DEFINITION]`)
- [x] 6.4 Add a `--force`/`-f` option to the `init` CLI command, passed through to
  the use case
- [x] 6.5 Unit tests: default writes both sections; `example-standard` mirrors
  open-standard mappings and does not collide; force deletes-then-writes; force
  succeeds when the existing file is malformed; without force still raises
- [x] 6.6 Update the e2e flow: default config now includes the
  `discovery-definitions` section and still passes `config verify`; `init --force`
  overwrites hand-edited entries; `init --force` succeeds over a malformed file
- [x] 6.7 Re-run the full quality gate — all green
