import pytest

from application.services import DiscoveryResolver
from domain.discovery import DiscoveryDefinition, Mapping
from domain.errors import DuplicateDiscoveryIdError


def _definition(definition_id: str) -> DiscoveryDefinition:
    return DiscoveryDefinition(id=definition_id, mappings=Mapping())


def test_resolves_builtin_id_with_no_custom_definitions() -> None:
    resolver = DiscoveryResolver(builtins=[_definition("ossify-open-standard")])

    resolvable = resolver.resolvable_ids([])

    assert "ossify-open-standard" in resolvable


def test_resolves_custom_definition_id() -> None:
    resolver = DiscoveryResolver(builtins=[])

    resolvable = resolver.resolvable_ids([_definition("my-strategy")])

    assert "my-strategy" in resolvable


def test_unknown_id_is_not_in_resolvable_set() -> None:
    resolver = DiscoveryResolver(builtins=[_definition("ossify-open-standard")])

    resolvable = resolver.resolvable_ids([])

    assert "unknown-id" not in resolvable


def test_two_custom_definitions_sharing_id_raises_duplicate_error() -> None:
    resolver = DiscoveryResolver(builtins=[])

    with pytest.raises(DuplicateDiscoveryIdError):
        resolver.resolvable_ids([_definition("my-strategy"), _definition("my-strategy")])


def test_custom_definition_colliding_with_builtin_id_raises_duplicate_error() -> None:
    resolver = DiscoveryResolver(builtins=[_definition("ossify-open-standard")])

    with pytest.raises(DuplicateDiscoveryIdError):
        resolver.resolvable_ids([_definition("ossify-open-standard")])
