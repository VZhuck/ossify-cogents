"""Resolves discovery-strategy ids against built-ins ∪ custom `discovery-definitions` entries."""

from domain.discovery import DiscoveryDefinition
from domain.errors import DuplicateDiscoveryIdError


class DiscoveryResolver:
    """Builds the resolvable-id set, enforcing id uniqueness across built-ins and custom entries."""

    def __init__(self, builtins: list[DiscoveryDefinition]) -> None:
        self._builtins = builtins

    def resolvable_ids(self, custom_definitions: list[DiscoveryDefinition]) -> set[str]:
        seen: set[str] = set()
        for definition in [*self._builtins, *custom_definitions]:
            if definition.id in seen:
                raise DuplicateDiscoveryIdError(
                    f"discovery strategy {definition.id!r} is already defined"
                )
            seen.add(definition.id)
        return seen
