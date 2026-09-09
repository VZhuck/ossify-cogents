"""`InstallCapabilities` use case — the imperative fetch→discover→select→write spine.

Implements `ports_in.InstallPort`. Per registry entry it materializes the source
(via the `SourcePort` chosen by `source-type`), executes discovery, resolves the
`install` selections, and writes: fixed categories translate into each target
platform's layout, `by-pattern` entries mirror verbatim to their discovery path
with their declared action.

How a destination is written depends on the entry's `install.mode`:

- `copy` removes the destination and writes bytes, exactly as before;
- `link` points the destination at the source with a symbolic link, so edits
  propagate both ways with no sync step. A non-link destination is *adopted* when
  its content already matches the source, and reported as *severed* when it does
  not — the diverged case is the one that would lose an edit.

This is Fork A: it re-fetches and re-writes every run and keeps no lock file. The
one piece of cross-run state it needs — which destinations this tool owns — a
symlink carries in its own target path, which is what makes stale-link pruning
possible here and copy pruning still impossible.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from application.services import (
    Destination,
    DiscoveredItem,
    DiscoveryExecution,
    DiscoveryResolver,
    DiscoveryResult,
    InstallResolver,
    TargetLayout,
)
from domain.dependencies import ByPatternDependency
from domain.discovery import DiscoveryDefinition
from domain.errors import (
    ConfigNotFoundError,
    SeveredLinkError,
    ShapeMismatchError,
    UnresolvableDiscoveryIdError,
    UnsupportedTargetActionError,
)
from domain.install_report import EntryInstallSummary, InstalledItem, InstallReport
from domain.ossify_config import ConfigSection
from domain.skill_registry import SkillSource
from ports_out import ConfigRepository, SourcePort, TargetPort, VcsExcludePort

# Skills are written before agents so a partially-supported platform (e.g. codex,
# which has a skills layout but no agents layout) installs its skill before an
# unsupported category raises `TargetLayoutUnavailableError`.
_FIXED_CATEGORIES = ("skills", "agents", "commands", "rules")
_ACTION_METHODS: dict[str, str] = {
    "init": "create_if_absent",
    "replace": "override",
    "json_merge": "merge",
}
_BY_PATTERN_PLATFORM = "by-pattern"


@dataclass
class _RunState:
    """Cross-entry state a single `install` run accumulates."""

    linked: set[Path] = field(default_factory=set)
    excluded: list[Path] = field(default_factory=list)
    local_source_roots: list[Path] = field(default_factory=list)


@dataclass(frozen=True)
class _EntryContext:
    """Everything writing one entry's items needs, resolved once per entry."""

    entry: SkillSource
    source: SourcePort
    tree_root: Path
    target: TargetPort
    workspace_root: Path
    source_root: Path
    links_relative: bool

    @property
    def mode(self) -> str:
        return self.entry.install.mode


class InstallCapabilities:
    """Fetches, discovers, selects, and writes selected capabilities into the repo."""

    def __init__(
        self,
        config_repository: ConfigRepository,
        sources: dict[str, SourcePort],
        discovery_resolver: DiscoveryResolver,
        discovery_execution: DiscoveryExecution,
        install_resolver: InstallResolver,
        target_layout: TargetLayout,
        target_factory: Callable[..., TargetPort],
        vcs_exclude: VcsExcludePort,
    ) -> None:
        self._config_repository = config_repository
        self._sources = sources
        self._discovery_resolver = discovery_resolver
        self._discovery_execution = discovery_execution
        self._install_resolver = install_resolver
        self._target_layout = target_layout
        self._target_factory = target_factory
        self._vcs_exclude = vcs_exclude

    def install(self, root: Path) -> InstallReport:
        if not self._config_repository.exists(root):
            raise ConfigNotFoundError(f"no ossify-cogents.json found at {root}")

        entries = (
            self._config_repository.read_section(
                root, ConfigSection.SKILL_REGISTRY, list[SkillSource]
            )
            or []
        )
        definitions_by_id = self._resolve_definitions(root)
        target = self._target_factory(root=root)
        state = _RunState()

        summaries = [
            self._install_entry(entry, definitions_by_id, target, root, state) for entry in entries
        ]
        pruned = self._prune_stale_links(target, state)
        warnings = self._maintain_excludes(root, state)
        return InstallReport(entries=summaries, pruned=pruned, warnings=warnings)

    def _resolve_definitions(self, root: Path) -> dict[str, DiscoveryDefinition]:
        custom = (
            self._config_repository.read_section(
                root, ConfigSection.DISCOVERY_DEFINITIONS, list[DiscoveryDefinition]
            )
            or []
        )
        return self._discovery_resolver.resolvable_definitions(custom)

    def _install_entry(
        self,
        entry: SkillSource,
        definitions_by_id: dict[str, DiscoveryDefinition],
        target: TargetPort,
        root: Path,
        state: _RunState,
    ) -> EntryInstallSummary:
        source = self._sources[entry.source_type]
        tree_root = source.materialize(entry)
        entry_definitions = self._entry_definitions(entry, definitions_by_id)
        discovery = self._discovery_execution.enumerate(source, tree_root, entry_definitions)
        context = self._entry_context(entry, source, tree_root, target, root)
        if entry.source_type == "local":
            state.local_source_roots.append(context.source_root)

        installed: list[InstalledItem] = []
        warnings: list[str] = []
        self._install_fixed(context, discovery, state, installed, warnings)
        self._install_by_pattern(context, discovery, state, installed, warnings)
        return EntryInstallSummary(entry_id=entry.id, installed=installed, warnings=warnings)

    def _entry_context(
        self,
        entry: SkillSource,
        source: SourcePort,
        tree_root: Path,
        target: TargetPort,
        root: Path,
    ) -> _EntryContext:
        """Resolve the entry's link geometry once.

        A source inside the workspace links relatively — portable and committable,
        it survives a clone to another path. Anything outside is machine-specific
        either way, so it links absolutely and is excluded from version control.
        """
        workspace_root = root.resolve()
        source_root = tree_root.resolve()
        return _EntryContext(
            entry=entry,
            source=source,
            tree_root=tree_root,
            target=target,
            workspace_root=workspace_root,
            source_root=source_root,
            links_relative=source_root.is_relative_to(workspace_root),
        )

    def _entry_definitions(
        self, entry: SkillSource, definitions_by_id: dict[str, DiscoveryDefinition]
    ) -> list[DiscoveryDefinition]:
        resolved: list[DiscoveryDefinition] = []
        for discovery_id in entry.discovery:
            definition = definitions_by_id.get(discovery_id)
            if definition is None:
                raise UnresolvableDiscoveryIdError(
                    f"unresolvable discovery id {discovery_id!r} on registry entry {entry.id!r}"
                )
            resolved.append(definition)
        return resolved

    def _install_fixed(
        self,
        context: _EntryContext,
        discovery: DiscoveryResult,
        state: _RunState,
        installed: list[InstalledItem],
        warnings: list[str],
    ) -> None:
        for category in _FIXED_CATEGORIES:
            patterns: list[str] = getattr(context.entry.install, category)
            if not patterns:
                continue
            available = discovery.fixed.get(category, {})
            selected, glob_warnings = self._install_resolver.select(patterns, list(available))
            warnings.extend(f"{category}: {pattern} matched nothing" for pattern in glob_warnings)
            for item_id in selected:
                item = available[item_id]
                for platform in context.entry.install.target_platforms:
                    for destination in self._target_layout.resolve(platform, category, item_id):
                        self._check_shape(item, destination, platform, item_id)
                        installed.append(
                            self._write_item(
                                context, item, destination.path, platform, category, item_id, state
                            )
                        )

    def _check_shape(
        self, item: DiscoveredItem, destination: Destination, platform: str, item_id: str
    ) -> None:
        if item.shape == destination.shape:
            return
        raise ShapeMismatchError(
            f"{item_id!r} is a {item.shape} in the source but the {platform!r} layout expects a "
            f"{destination.shape} at {destination.path}"
        )

    def _write_item(
        self,
        context: _EntryContext,
        item: DiscoveredItem,
        destination: Path,
        platform: str,
        category: str,
        item_id: str,
        state: _RunState,
    ) -> InstalledItem:
        if context.mode == "link":
            return self._link_item(context, item, destination, platform, category, item_id, state)
        self._copy_item(context, item, destination)
        return InstalledItem(
            platform=platform,
            category=category,
            item_id=item_id,
            destination=destination,
            mode="copy",
        )

    def _copy_item(self, context: _EntryContext, item: DiscoveredItem, destination: Path) -> None:
        context.target.remove(destination)
        if item.shape == "file":
            context.target.override(
                destination, context.source.read_bytes(context.tree_root, item.location)
            )
            return
        for relative in context.source.walk(context.tree_root, item.location):
            sub_path = relative.relative_to(item.location)
            context.target.override(
                destination / sub_path, context.source.read_bytes(context.tree_root, relative)
            )

    def _link_item(
        self,
        context: _EntryContext,
        item: DiscoveredItem,
        destination: Path,
        platform: str,
        category: str,
        item_id: str,
        state: _RunState,
    ) -> InstalledItem:
        link_target = self._link_target(context, item.location, destination)
        self._guard_severance(context, item, destination, link_target)
        context.target.link(destination, link_target, is_directory=item.shape == "dir")

        state.linked.add(destination)
        if link_target.is_absolute():
            state.excluded.append(destination)
        return InstalledItem(
            platform=platform,
            category=category,
            item_id=item_id,
            destination=destination,
            mode="link",
            link_target=link_target,
        )

    def _link_target(self, context: _EntryContext, location: Path, destination: Path) -> Path:
        absolute = context.source_root / location
        if not context.links_relative:
            return absolute
        return Path(os.path.relpath(absolute, (context.workspace_root / destination).parent))

    def _guard_severance(
        self,
        context: _EntryContext,
        item: DiscoveredItem,
        destination: Path,
        link_target: Path,
    ) -> None:
        """Refuse a destination whose content the link would silently discard.

        A regular file where a link belongs is either a copy-mode install of the
        same capability — identical bytes, nothing to lose, adopt it — or an edit
        that never reached the source, which is precisely what an atomic-saving
        editor produces when it replaces a file symlink. Only the second blocks.
        """
        target = context.target
        if not target.exists(destination) or target.is_symlink(destination):
            return
        if self._matches_source(context, item, destination):
            return
        raise SeveredLinkError(
            f"{destination} exists and differs from {link_target}; it is not a link, so an edit "
            "made there never reached the source. Refusing to overwrite it — inspect and merge "
            "it, then re-run install."
        )

    def _matches_source(
        self, context: _EntryContext, item: DiscoveredItem, destination: Path
    ) -> bool:
        target = context.target
        if item.shape == "file":
            return target.read(destination) == context.source.read_bytes(
                context.tree_root, item.location
            )
        expected = {
            relative.relative_to(item.location): context.source.read_bytes(
                context.tree_root, relative
            )
            for relative in context.source.walk(context.tree_root, item.location)
        }
        found = {
            relative: target.read(destination / relative) for relative in target.walk(destination)
        }
        return expected == found

    def _install_by_pattern(
        self,
        context: _EntryContext,
        discovery: DiscoveryResult,
        state: _RunState,
        installed: list[InstalledItem],
        warnings: list[str],
    ) -> None:
        for by_pattern in context.entry.install.by_pattern:
            items = discovery.by_pattern.get(by_pattern.category, {})
            for item_id, item in items.items():
                installed.append(
                    self._apply_by_pattern(context, by_pattern, item_id, item, state, warnings)
                )

    def _apply_by_pattern(
        self,
        context: _EntryContext,
        by_pattern: ByPatternDependency,
        item_id: str,
        item: DiscoveredItem,
        state: _RunState,
        warnings: list[str],
    ) -> InstalledItem:
        """Mirror one by-pattern item to its discovery path, verbatim.

        Only `replace` can be linked: it already means the source owns the file.
        `init` seeds a file the repo owns afterwards, and `json_merge` writes a
        blend of both — through a link, that would write back into the source.
        """
        if context.mode == "link" and by_pattern.action == "replace":
            return self._link_item(
                context,
                item,
                item.location,
                _BY_PATTERN_PLATFORM,
                by_pattern.category,
                item_id,
                state,
            )

        if context.mode == "link":
            warnings.append(
                f"by-pattern {by_pattern.category}: action {by_pattern.action!r} cannot be "
                "linked (the workspace owns the destination); copied instead"
            )
        self._apply_action(
            context.target,
            item.location,
            context.source.read_bytes(context.tree_root, item.location),
            by_pattern,
        )
        return InstalledItem(
            platform=_BY_PATTERN_PLATFORM,
            category=by_pattern.category,
            item_id=item_id,
            destination=item.location,
            mode="copy",
        )

    def _apply_action(
        self,
        target: TargetPort,
        path: Path,
        data: bytes,
        by_pattern: ByPatternDependency,
    ) -> None:
        method_name = _ACTION_METHODS.get(by_pattern.action)
        if method_name is None:  # pragma: no cover - actions are constrained by the model
            raise UnsupportedTargetActionError(
                f"unsupported by-pattern action {by_pattern.action!r}"
            )
        getattr(target, method_name)(path, data)

    def _prune_stale_links(self, target: TargetPort, state: _RunState) -> list[Path]:
        """Unlink destinations that point into a configured source but nothing selected.

        A symlink carries its own provenance — its target proves this tool wrote it
        — so no lock file is needed. Unlinking destroys nothing: the source it
        pointed at is untouched. Copies have no such provenance and stay put.
        """
        if not state.local_source_roots:
            return []

        pruned: list[Path] = []
        for owned_root in self._target_layout.owned_roots():
            for child in target.children(owned_root):
                if child in state.linked:
                    continue
                link_target = target.link_target(child)
                if link_target is None:
                    continue
                if any(link_target.is_relative_to(root) for root in state.local_source_roots):
                    target.remove(child)
                    pruned.append(child)
        return pruned

    def _maintain_excludes(self, root: Path, state: _RunState) -> list[str]:
        if not state.excluded:
            return []
        if self._vcs_exclude.set_excluded(root, state.excluded):
            return []
        return [
            f"{root} is not a git repository: linked destinations were created but not added to "
            "a local exclude file, so they may show up as untracked changes"
        ]
