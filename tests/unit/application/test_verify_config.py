from pathlib import Path
from unittest.mock import MagicMock

import pytest

from application import VerifyConfig
from application.services import DiscoveryResolver, RegistryValidator
from domain.discovery import DiscoveryDefinition, Mapping
from domain.errors import (
    ConfigNotFoundError,
    DuplicateDiscoveryIdError,
    DuplicateSourceIdError,
    UnresolvableDiscoveryIdError,
)
from domain.ossify_config import ConfigSection
from domain.skill_registry import SkillSource


def _entry(entry_id: str, discovery: list[str] | None = None) -> SkillSource:
    return SkillSource(
        id=entry_id,
        name=entry_id.title(),
        description="",
        source_type="git",
        source={"uri": f"https://github.com/acme-org/{entry_id}.git"},
        discovery=discovery or [],
    )


def _definition(definition_id: str) -> DiscoveryDefinition:
    return DiscoveryDefinition(id=definition_id, mappings=Mapping())


def _read_section_by_config_section(
    registry_entries: list[SkillSource], custom_definitions: list[DiscoveryDefinition]
):
    def _read_section(root: Path, section: ConfigSection, model: type) -> object:
        if section == ConfigSection.SKILL_REGISTRY:
            return registry_entries
        if section == ConfigSection.DISCOVERY_DEFINITIONS:
            return custom_definitions
        return None

    return _read_section


@pytest.fixture
def config_repository() -> MagicMock:
    repository = MagicMock()
    repository.exists.return_value = True
    repository.read_section.side_effect = _read_section_by_config_section([], [])
    return repository


@pytest.fixture
def verify_config(config_repository: MagicMock) -> VerifyConfig:
    return VerifyConfig(
        config_repository=config_repository,
        validator=RegistryValidator(),
        discovery_resolver=DiscoveryResolver(builtins=[_definition("ossify-open-standard")]),
    )


def test_verify_passes_for_valid_unique_registry(
    verify_config: VerifyConfig, config_repository: MagicMock
) -> None:
    config_repository.read_section.side_effect = _read_section_by_config_section(
        [_entry("a"), _entry("b")], []
    )

    verify_config.verify(Path("/repo"))


def test_verify_raises_on_duplicate_id(
    verify_config: VerifyConfig, config_repository: MagicMock
) -> None:
    config_repository.read_section.side_effect = _read_section_by_config_section(
        [_entry("a"), _entry("a")], []
    )

    with pytest.raises(DuplicateSourceIdError):
        verify_config.verify(Path("/repo"))


def test_verify_raises_config_not_found_when_no_file(
    verify_config: VerifyConfig, config_repository: MagicMock
) -> None:
    config_repository.exists.return_value = False

    with pytest.raises(ConfigNotFoundError):
        verify_config.verify(Path("/repo"))


def test_verify_passes_when_discovery_id_resolves_to_builtin(
    verify_config: VerifyConfig, config_repository: MagicMock
) -> None:
    config_repository.read_section.side_effect = _read_section_by_config_section(
        [_entry("a", discovery=["ossify-open-standard"])], []
    )

    verify_config.verify(Path("/repo"))


def test_verify_raises_on_unresolvable_discovery_id(
    verify_config: VerifyConfig, config_repository: MagicMock
) -> None:
    config_repository.read_section.side_effect = _read_section_by_config_section(
        [_entry("a", discovery=["unknown-strategy"])], []
    )

    with pytest.raises(UnresolvableDiscoveryIdError):
        verify_config.verify(Path("/repo"))


def test_verify_raises_when_custom_definition_collides_with_builtin_id(
    verify_config: VerifyConfig, config_repository: MagicMock
) -> None:
    config_repository.read_section.side_effect = _read_section_by_config_section(
        [_entry("a")], [_definition("ossify-open-standard")]
    )

    with pytest.raises(DuplicateDiscoveryIdError):
        verify_config.verify(Path("/repo"))


def test_verify_raises_on_duplicate_discovery_definition_id(
    verify_config: VerifyConfig, config_repository: MagicMock
) -> None:
    config_repository.read_section.side_effect = _read_section_by_config_section(
        [_entry("a")], [_definition("custom-1"), _definition("custom-1")]
    )

    with pytest.raises(DuplicateDiscoveryIdError):
        verify_config.verify(Path("/repo"))
