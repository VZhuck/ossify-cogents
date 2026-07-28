"""`InstallCapabilities` use case — the imperative fetch→discover→select→write spine.

Implements `ports_in.InstallPort`. Per registry entry it materializes the source
(via the `SourcePort` chosen by `source-type`), executes discovery, resolves the
`install` selections, and writes: fixed categories translate into each target
platform's layout with `replace` (remove-then-override) semantics; `by-pattern`
entries mirror verbatim to their discovery path with their declared action.

This is Fork A: it re-fetches and re-writes every run and keeps no lock file.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from application.services import (
    Destination,
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
    UnresolvableDiscoveryIdError,
    UnsupportedTargetActionError,
)
from domain.install_report import EntryInstallSummary, InstallReport
from domain.ossify_config import ConfigSection
from domain.skill_registry import SkillSource
from ports_out import ConfigRepository, SourcePort, TargetPort

# Skills are written before agents so a partially-supported platform (e.g. codex,
# which has a skills layout but no agents layout) installs its skill before an
# unsupported category raises `TargetLayoutUnavailableError`.
_FIXED_CATEGORIES = ("skills", "agents", "commands", "rules")
_ACTION_METHODS: dict[str, str] = {
    "init": "create_if_absent",
    "replace": "override",
    "json_merge": "merge",
}


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
    ) -> None:
        self._config_repository = config_repository
        self._sources = sources
        self._discovery_resolver = discovery_resolver
        self._discovery_execution = discovery_execution
        self._install_resolver = install_resolver
        self._target_layout = target_layout
        self._target_factory = target_factory

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

        summaries = [self._install_entry(entry, definitions_by_id, target) for entry in entries]
        return InstallReport(entries=summaries)

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
    ) -> EntryInstallSummary:
        source = self._sources[entry.source_type]
        tree_root = source.materialize(entry)
        entry_definitions = self._entry_definitions(entry, definitions_by_id)
        discovery = self._discovery_execution.enumerate(source, tree_root, entry_definitions)

        installed: list[str] = []
        warnings: list[str] = []
        self._install_fixed(entry, source, tree_root, discovery, target, installed, warnings)
        self._install_by_pattern(entry, source, tree_root, discovery, target, installed)
        return EntryInstallSummary(entry_id=entry.id, installed=installed, warnings=warnings)

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
        entry: SkillSource,
        source: SourcePort,
        tree_root: Path,
        discovery: DiscoveryResult,
        target: TargetPort,
        installed: list[str],
        warnings: list[str],
    ) -> None:
        for category in _FIXED_CATEGORIES:
            patterns: list[str] = getattr(entry.install, category)
            if not patterns:
                continue
            available = discovery.fixed.get(category, {})
            selected, glob_warnings = self._install_resolver.select(patterns, list(available))
            warnings.extend(f"{category}: {pattern} matched nothing" for pattern in glob_warnings)
            for item_id in selected:
                location = available[item_id]
                for platform in entry.install.target_platforms:
                    for destination in self._target_layout.resolve(platform, category, item_id):
                        self._write_item(source, tree_root, location, destination, target)
                        installed.append(f"{platform}:{category}:{item_id} -> {destination.path}")

    def _write_item(
        self,
        source: SourcePort,
        tree_root: Path,
        location: Path,
        destination: Destination,
        target: TargetPort,
    ) -> None:
        target.remove(destination.path)
        if destination.shape == "file":
            target.override(destination.path, source.read_bytes(tree_root, location))
            return
        for relative in source.walk(tree_root, location):
            sub_path = relative.relative_to(location)
            target.override(destination.path / sub_path, source.read_bytes(tree_root, relative))

    def _install_by_pattern(
        self,
        entry: SkillSource,
        source: SourcePort,
        tree_root: Path,
        discovery: DiscoveryResult,
        target: TargetPort,
        installed: list[str],
    ) -> None:
        for by_pattern in entry.install.by_pattern:
            items = discovery.by_pattern.get(by_pattern.category, {})
            for location in items.values():
                self._apply_action(
                    target, location, source.read_bytes(tree_root, location), by_pattern
                )
                installed.append(
                    f"by-pattern:{by_pattern.category}:{by_pattern.action} -> {location}"
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
