## Why

There is no way to bootstrap a repo for `ossify-cogents`. A user must hand-author
`ossify-cogents.json` from scratch, guessing the section keys, the registry-entry
shape, and the (kebab-cased) `install` block layout. Every other command
(`registry`, `config verify`, and the future install/sync flow) reads this file
but nothing writes a first one. `init` is the missing entry point: it scaffolds a
valid, self-documenting default config so the user has a working, inspectable
starting point.

## What Changes

- Add a top-level `ossify init` command that writes a default `ossify-cogents.json`
  at the workspace root.
- The default config contains a single curated registry item pointing at
  `https://github.com/anthropics/skills` (`source-type: git`, `ref: main`),
  with `discovery: ["ossify-open-standard"]`.
- The item's `install` block is written as an **explicit empty skeleton** —
  `target-platforms: ["claude"]` and every selection list (`agents`, `skills`,
  `commands`, `rules`, `by-pattern`) present but empty — so the file teaches the
  install-block shape while installing nothing.
- The default config also writes a `discovery-definitions` section containing one
  **example custom definition** that mirrors the built-in `ossify-open-standard`
  mappings (distinct, non-colliding id) — so the file documents what a custom
  strategy looks like, which is otherwise invisible (built-ins are packaged code
  data and never appear in the config).
- **Fast-fail by default**: without `--force`, if `ossify-cogents.json` already
  exists at the workspace root, `init` prints an error, exits non-zero, and writes
  nothing (no overwrite, no merge, no partial write).
- **`--force` overrides**: `ossify init --force` writes the default config even
  when one exists, replacing the modeled sections wholesale. It does **not** merge,
  and does not require the existing file to be valid or parseable.
- The curated default registry item and example discovery definition are packaged
  code data (like the built-in discovery strategies), not derived from user input.

## Capabilities

### New Capabilities
- `config-init`: the `ossify init` command — scaffolds a default
  `ossify-cogents.json` with one curated registry item and an explicit empty
  `install` skeleton, and fast-fails when a config file already exists.

## Impact

- **Domain**: packaged `DEFAULT_REGISTRY_ITEM` (a `SkillSource`) and
  `DEFAULT_DISCOVERY_DEFINITION` (a `DiscoveryDefinition`) constants; a new
  `ConfigAlreadyExistsError` in `domain/errors.py`.
- **Ports**: new `InitPort` in `ports_in/` (`init(root, *, force)`); a new
  `delete(root)` method on the `ConfigRepository` out-port (used by `--force` to
  clear a possibly-malformed file before writing a clean default).
- **Application**: new `InitConfig` use case implementing `InitPort`, depending on
  the existing `ConfigRepository` (`exists` + `delete` + `write_section`).
- **Adapters**: reuses `OssifyConfigAdapter`; adds `delete`. The empty-list
  skeleton falls out of its existing `exclude_none` dump behavior.
- **CLI**: new top-level `init` command (with `--force`) on the root Typer app.
- **Container**: wire `InitConfig` as a use-case provider.
- **Tooling**: no schema change — `init` writes the already-modeled
  skill-registry and discovery-definitions sections.
