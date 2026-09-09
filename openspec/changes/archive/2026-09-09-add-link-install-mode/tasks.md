## 1. Domain

- [x] 1.1 Add `mode: Literal["copy", "link"] = "copy"` to `Dependencies` in `src/domain/dependencies.py`; document that it is the sole control and that `link` requires a `local` source.
- [x] 1.2 In `src/domain/skill_registry.py`, extend `_apply_source_type_rules` to raise `InvalidRegistryEntryError` when `install.mode == "link"` and `source_type == "git"`, naming the entry id and the reason (git caches are hard-reset on fetch).
- [x] 1.3 Add `SeveredLinkError`, `LinkNotSupportedError`, and `ShapeMismatchError` to `src/domain/errors.py`.
- [x] 1.4 In `src/domain/install_report.py`, add a frozen `InstalledItem` model (`platform`, `category`, `item_id`, `destination`, `mode`, `link_target: Path | None`) and change `EntryInstallSummary.installed` to `list[InstalledItem]`. Add a `pruned: list[Path]` field.
- [x] 1.5 Regenerate `schema/v1.json` with `uv run python scripts/generate_schema.py` once `Dependencies` carries `mode`, and confirm the `schema-drift` hook is clean. Do not hand-edit the file.

## 2. Discovery records shape

- [x] 2.1 In `src/application/services/_discovery_execution.py`, add a frozen `DiscoveredItem` dataclass with `location: Path` and `shape: Literal["dir", "file"]`.
- [x] 2.2 Change `DiscoveryResult.fixed` and `.by_pattern` inner values from `Path` to `DiscoveredItem`; update the dataclass docstring.
- [x] 2.3 Rewrite `_enumerate_folder` so each walked file's `relative_to(folder)` path determines the child: `len(parts) > 1` -> directory (id = `parts[0]`, shape `dir`, location `folder / parts[0]`); `len(parts) == 1` -> file (id = `Path(parts[0]).stem`, shape `file`, location `folder / parts[0]`).
- [x] 2.4 Update `_enumerate_files` to return `DiscoveredItem(location=relative, shape="file")`, keeping the existing stem-id behavior.
- [x] 2.5 Update the module docstring's enumeration-semantics list to state the new id and shape rules.
- [x] 2.6 Export `DiscoveredItem` from `src/application/services/__init__.py`.
- [x] 2.7 In `src/application/services/_target_layout.py`, document `Destination.shape` as the layout's *expected* shape and record that discovery owns the observed shape.

## 3. Ports

- [x] 3.1 Add `link(self, path: Path, source: Path, *, is_directory: bool) -> None` to `ports_out.TargetPort`, documenting that `path` is root-relative while `source` is an already-resolved absolute or relative link target, that `is_directory` comes from the item's discovered shape, and that an adapter unable to link raises `UnsupportedTargetActionError`.
- [x] 3.2 Add `is_symlink(self, path: Path) -> bool` to `TargetPort` so the use case can detect links and severance without importing `pathlib` semantics into `application/`.
- [x] 3.3 Add the read side `TargetPort` needs to inspect what is already in the workspace: `read`, `walk` (for the adoption comparison), `children` and `link_target` (for stale-link pruning). None of them follow a symlink.
- [x] 3.4 Create `src/ports_out/_vcs_exclude_port.py` with `VcsExcludePort.set_excluded(root: Path, paths: list[Path]) -> bool`, returning whether exclusion was applied (false when the root is not a repository).
- [x] 3.5 Export `VcsExcludePort` from `src/ports_out/__init__.py`.

## 4. Target adapter

- [x] 4.1 Make `remove()` symlink-safe: test `is_symlink()` first and `unlink()` without following, then `is_dir()` -> `shutil.rmtree`, else `unlink(missing_ok=True)`. Comment *why* the ordering matters — `is_dir()` follows symlinks, so the current order raises `OSError` on a linked destination and a hand-rolled recursion would delete the link's target tree.
- [x] 4.2 Implement `link()`: remove any existing destination via the symlink-safe `remove()` (the use case has already decided the destination is replaceable), create parent directories, then `os.symlink` with `target_is_directory=is_directory`.
- [x] 4.3 On `OSError` for a directory destination, fall back to a platform directory-link equivalent (Windows junction) where one exists.
- [x] 4.4 On `OSError` for a file destination, raise `LinkNotSupportedError` naming the destination and the platform requirement. Do not copy bytes.
- [x] 4.5 Implement `is_symlink()` and the read side added in 3.3.

## 5. VCS exclude adapter

- [x] 5.1 Create the `src/adapters/persistence/` package with `__init__.py`.
- [x] 5.2 Implement `GitExcludeAdapter.set_excluded`: locate the git directory, handling `.git` as a directory and as a file containing a `gitdir:` pointer (worktrees, submodules); return `False` when neither resolves.
- [x] 5.3 Read `info/exclude`, replace the content between `# --- ossify-cogents linked capabilities ---` and its end marker with the supplied paths (creating the block when absent, removing it when the path list is empty), and preserve all content outside the markers.
- [x] 5.4 Write with a trailing newline and stable ordering so repeated runs produce byte-identical output.

## 6. Local source adapter

- [x] 6.1 In `LocalSourceAdapter.materialize`, raise `SourceFetchError` naming the entry id and path when the expanded path does not exist.

## 7. Install use case

- [x] 7.1 Update `_install_fixed` to pass the `DiscoveredItem` (not a bare `Path`) into `_write_item`, and raise `ShapeMismatchError` when `item.shape != destination.shape`, naming item id, platform, expected and observed shape; do not write the destination.
- [x] 7.2 Branch the copy-mode write on `item.shape`: `file` -> single `override` of the item's bytes; `dir` -> walk and `override` each file under the item location.
- [x] 7.3 Update `_install_by_pattern` for the `DiscoveredItem` value type; by-pattern items mirror verbatim and are not shape-checked.
- [x] 7.4 In `_install_entry`, resolve the entry's link geometry once: expand and resolve the source path, then decide relative-vs-absolute by whether it is inside the workspace root.
- [x] 7.5 In `_write_item`, branch on the entry's mode. Copy mode keeps today's behavior.
- [x] 7.6 Link mode: when the destination exists and is not a symlink, compare it against the source — identical content is adopted (replaced with the link), differing content raises `SeveredLinkError` naming the destination and the intended target and leaves the destination untouched.
- [x] 7.7 Link mode: compute the link target (relative to the destination's parent for in-workspace sources, absolute otherwise) and call `target.link` with `is_directory` from the discovered shape.
- [x] 7.8 In `_apply_action`, link `replace` by-pattern items under link mode (same adopt/sever rule); copy `init` and `json_merge` and append a warning naming the category and action.
- [x] 7.9 Collect every absolute-target linked destination across all entries and call `VcsExcludePort.set_excluded` once at the end of the run; append a warning when it returns `False`.
- [x] 7.10 Implement stale-link pruning: walk the destinations that the configured target layouts could own, unlink any symlink whose resolved target is inside a configured `local` source root but which no entry selected this run, and record it in `pruned`.
- [x] 7.11 Populate `InstalledItem` for every write, carrying mode and link target.

## 8. CLI

- [x] 8.1 In `src/cli/_install.py`, render copied items with `+` and linked items with `=>` including the link target; render pruned destinations and warnings distinctly.
- [x] 8.2 Confirm no new CLI options are added — mode is config-only.

## 9. Container

- [x] 9.1 Register `GitExcludeAdapter` in `src/container.py` and inject it into `InstallCapabilities`.

## 10. Tests — domain

- [x] 10.1 `test_dependencies.py`: `mode` defaults to `copy`; parses `link`; rejects an unknown value.
- [x] 10.2 `test_skill_registry.py`: `mode: link` with `source-type: local` is accepted; with `source-type: git` raises `InvalidRegistryEntryError`.
- [x] 10.3 `tests/e2e/test_registry_flow.py`: `ossify config verify` surfaces the git-plus-link rejection offline, without fetching. (E2E rather than `test_verify_config.py`, whose mocked repository hands back already-parsed models and so never exercises the validator.)

## 11. Tests — discovery and layout

- [x] 11.1 `test_discovery_execution.py`: folder rule over directory children yields name-ids with shape `dir`.
- [x] 11.2 `test_discovery_execution.py`: folder rule over file children yields stem-ids with shape `file` (regression for the doubled extension).
- [x] 11.3 `test_discovery_execution.py`: folder rule over mixed dir/file children records both shapes correctly.
- [x] 11.4 `test_discovery_execution.py`: file rule records shape `file`; missing path still yields nothing.
- [x] 11.5 `test_install_capabilities.py`: a `file`-shaped item installs to `<id>.md`, not `<id>.md.md`; a `dir`-shaped item installs its whole tree with relative paths preserved.
- [x] 11.6 `test_install_capabilities.py`: shape mismatch raises `ShapeMismatchError` and writes nothing.
- [x] 11.7 `test_install_capabilities.py`: a `file`-shaped item routed to two platforms picks up each platform's own rename (`.claude/rules/x.md` and `.github/instructions/x.instructions.md`).

## 12. Tests — adapters

- [x] 12.1 `test_filesystem_target_adapter.py`: `remove()` on a symlink-to-directory unlinks the link and leaves the target directory and its files intact; on a real directory still removes recursively; on an absent path is a no-op.
- [x] 12.2 `test_filesystem_target_adapter.py`: `link()` creates a directory symlink; a file symlink; and replaces an existing symlink idempotently.
- [x] 12.3 **Safety test (required):** re-running a link over an existing linked destination leaves the source tree and all its files intact. This pins the one destructive failure mode — a future `rmtree(ignore_errors=True)` or hand-rolled recursion in `remove()` would delete the link's target.
- [x] 12.4 New `tests/unit/adapters/persistence/test_git_exclude_adapter.py`: block is created; rewritten in full on a second call with different paths; removed when the path list is empty; content outside the markers is preserved; repeated identical calls are byte-stable.
- [x] 12.5 `test_git_exclude_adapter.py`: `.git` as a file containing a `gitdir:` pointer resolves; a non-repository root returns `False` without raising.
- [x] 12.6 `test_local_source_adapter.py`: a missing path raises `SourceFetchError` naming the entry.

## 13. Tests — install use case

- [x] 13.1 Link mode creates links; copy mode still copies; a `copy` entry and a `link` entry in one config each behave correctly.
- [x] 13.2 An in-workspace source produces a relative link that resolves after the workspace directory is renamed; an out-of-workspace source produces an absolute link.
- [x] 13.3 Only absolute-target destinations reach `set_excluded`; relative ones do not.
- [x] 13.4 A destination holding a byte-identical copy is adopted and reported as linked — file-shaped and directory-shaped both.
- [x] 13.5 A destination holding diverged content raises `SeveredLinkError` and leaves the content untouched.
- [x] 13.6 `replace` by-pattern links; `init` and `json_merge` copy and each produce a warning.
- [x] 13.7 A deselected linked capability is pruned and reported; the source is unchanged; a link outside any configured source root is left alone; a deselected copy is not pruned.
- [x] 13.8 One canonical file-shaped item linked to two platforms yields two links to the same source, and an edit through one is visible through the other.
- [x] 13.9 `InstalledItem` carries the correct mode and link target for each write.

## 14. Tests — e2e

- [x] 14.1 `tests/e2e/test_install_flow.py`: a source with file-shaped commands/rules installs to correctly-named destinations (no doubled extension).
- [x] 14.2 `tests/e2e/test_install_flow.py`: a full `install` against a local source with `mode: link` produces links, writes the exclude block, and renders linked items distinctly.
- [x] 14.3 A second `install` run over the same workspace is idempotent — same links, byte-identical exclude block, no errors.
- [x] 14.4 A `mode: copy` run followed by a `mode: link` run over the same workspace adopts every destination without error.

## 15. Docs

- [x] 15.1 `docs/configuration.md`: document `install.mode`, the `local`-only rule and why, the relative-vs-absolute geometry, and that discovered ids are extension-free canonical names for both rule types.
- [x] 15.2 `docs/install-process.md`: document link semantics, `.git/info/exclude` maintenance, `by-pattern` action linkability, adoption and severed links, stale-link pruning, and the Windows behavior; note the destination rename and that pre-existing `*.md.md` files are not pruned and must be deleted once by hand.
- [x] 15.3 `README.md`: add a short "Live-editing a local source" section under Advanced Topics.
- [x] 15.4 Document the shared-mutable-state caveat: two workspaces linking the same source see each other's edits.

## 16. Verification

- [x] 16.1 `uv run pytest` — full suite green.
- [x] 16.2 `uv run ruff check src tests` and `uv run ruff format --check`.
- [x] 16.3 `uv run mypy src`.
- [x] 16.4 `uv run lint-imports`.
- [x] 16.5 `uv run openspec validate add-link-install-mode --strict`.
- [x] 16.6 Manual: set `mode: link` on the real local toolkit entry, run `install`, edit a skill file through `.claude/skills/...`, and confirm the change appears in the toolkit repo's `git status`.
- [x] 16.7 Manual: confirm `.git/info/exclude` contains the linked destinations and that `git status` reports a clean tree.
