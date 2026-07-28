"""Executes resolved discovery strategies against a materialized working tree.

`DiscoveryResolver` answers *which* strategies are resolvable; this service is the
runtime half of `skill-discovery` — it walks a materialized tree with a strategy's
`Mapping` globs to enumerate the ids actually present and each id's location.

Enumeration semantics (per the `skill-discovery` spec):
- a `folder` rule yields the folder's immediate children, id = child name;
- a `file` rule yields matching files, id = file stem;
- a rule whose path is absent contributes no ids (no error).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path

from domain.discovery import DiscoveryDefinition, GlobRule
from ports_out import SourcePort

_FIXED_CATEGORIES = ("agents", "skills", "commands", "rules")
_GLOB_METACHARACTERS = frozenset("*?[")


@dataclass(frozen=True)
class DiscoveryResult:
    """Discovered ids and their working-tree locations, split by category kind.

    `fixed` is keyed by the four fixed categories; `by_pattern` by each rule's
    free-form `category`. Each inner map is `id -> location` (relative to root).
    """

    fixed: dict[str, dict[str, Path]] = field(default_factory=dict)
    by_pattern: dict[str, dict[str, Path]] = field(default_factory=dict)


class DiscoveryExecution:
    """Walks a materialized tree with resolved strategies to enumerate discovered ids."""

    def enumerate(
        self, source: SourcePort, root: Path, definitions: list[DiscoveryDefinition]
    ) -> DiscoveryResult:
        result = DiscoveryResult()
        for definition in definitions:
            mappings = definition.mappings
            for category in _FIXED_CATEGORIES:
                for rule in getattr(mappings, category):
                    self._merge(result.fixed, category, self._enumerate(source, root, rule))
            for rule in mappings.by_pattern:
                self._merge(result.by_pattern, rule.category, self._enumerate(source, root, rule))
        return result

    def _merge(
        self, target: dict[str, dict[str, Path]], category: str, found: dict[str, Path]
    ) -> None:
        target.setdefault(category, {}).update(found)

    def _enumerate(self, source: SourcePort, root: Path, rule: GlobRule) -> dict[str, Path]:
        if rule.type == "folder":
            return self._enumerate_folder(source, root, rule.path)
        return self._enumerate_files(source, root, rule.path)

    def _enumerate_folder(self, source: SourcePort, root: Path, path: str) -> dict[str, Path]:
        folder = Path(path)
        found: dict[str, Path] = {}
        for relative in source.walk(root, folder):
            child = relative.relative_to(folder).parts[0]
            found[child] = folder / child
        return found

    def _enumerate_files(self, source: SourcePort, root: Path, pattern: str) -> dict[str, Path]:
        found: dict[str, Path] = {}
        for relative in source.walk(root, _glob_prefix(pattern)):
            if fnmatchcase(relative.as_posix(), pattern):
                found[relative.stem] = relative
        return found


def _glob_prefix(pattern: str) -> Path:
    """The leading glob-free segments of `pattern` — the deepest fixed directory to walk."""
    prefix_parts: list[str] = []
    for part in pattern.split("/"):
        if any(char in part for char in _GLOB_METACHARACTERS):
            break
        prefix_parts.append(part)
    return Path(*prefix_parts) if prefix_parts else Path(".")
