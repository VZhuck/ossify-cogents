"""Validates and resolves registry `install` blocks.

Two responsibilities, split by timing:

- `validate_static` — offline checks callable from `config verify`: every
  `by-pattern` category resolves against the entry's discovery strategies'
  by-pattern categories, and every `target-platforms` value is a supported
  platform (or the `"*"` wildcard).
- `select` — dynamic (sync-time) fixed-category glob matching against
  actually-discovered ids: an exact literal matching nothing is an error, a
  glob matching nothing is a warning.
"""

from fnmatch import fnmatchcase

from domain.discovery import DiscoveryDefinition
from domain.errors import (
    UnknownTargetPlatformError,
    UnmatchedInstallSelectionError,
    UnresolvableByPatternCategoryError,
)
from domain.skill_registry import SkillSource

_GLOB_METACHARACTERS = frozenset("*?[")


def _is_glob(pattern: str) -> bool:
    return any(char in _GLOB_METACHARACTERS for char in pattern)


class InstallResolver:
    """Static (offline) validation plus dynamic glob selection for `install` blocks."""

    def __init__(self, supported_platforms: set[str]) -> None:
        self._supported_platforms = set(supported_platforms)

    def validate_static(
        self,
        entries: list[SkillSource],
        definitions_by_id: dict[str, DiscoveryDefinition],
    ) -> None:
        for entry in entries:
            self._validate_target_platforms(entry)
            self._validate_by_pattern_categories(entry, definitions_by_id)

    def select(self, patterns: list[str], discovered_ids: list[str]) -> tuple[list[str], list[str]]:
        selected: list[str] = []
        warnings: list[str] = []
        for pattern in patterns:
            matches = [item for item in discovered_ids if fnmatchcase(item, pattern)]
            if matches:
                selected.extend(match for match in matches if match not in selected)
            elif _is_glob(pattern):
                warnings.append(pattern)
            else:
                raise UnmatchedInstallSelectionError(
                    f"no discovered item matches required selection {pattern!r}"
                )
        return selected, warnings

    def _validate_target_platforms(self, entry: SkillSource) -> None:
        for platform in entry.install.target_platforms:
            if platform != "*" and platform not in self._supported_platforms:
                raise UnknownTargetPlatformError(
                    f"unknown target platform {platform!r} on registry entry {entry.id!r}"
                )

    def _validate_by_pattern_categories(
        self, entry: SkillSource, definitions_by_id: dict[str, DiscoveryDefinition]
    ) -> None:
        if not entry.install.by_pattern:
            return
        available = self._available_categories(entry, definitions_by_id)
        for by_pattern in entry.install.by_pattern:
            if by_pattern.category not in available:
                raise UnresolvableByPatternCategoryError(
                    f"unresolvable install by-pattern category {by_pattern.category!r} "
                    f"on registry entry {entry.id!r}"
                )

    def _available_categories(
        self, entry: SkillSource, definitions_by_id: dict[str, DiscoveryDefinition]
    ) -> set[str]:
        categories: set[str] = set()
        for discovery_id in entry.discovery:
            definition = definitions_by_id.get(discovery_id)
            if definition is None:
                continue
            for rule in definition.mappings.by_pattern:
                categories.add(rule.category)
        return categories
