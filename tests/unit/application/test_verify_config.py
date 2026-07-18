from pathlib import Path
from unittest.mock import MagicMock

import pytest

from application import VerifyConfig
from application.services import RegistryValidator
from domain.errors import ConfigNotFoundError, DuplicateSourceIdError
from domain.skill_registry import SkillSource


def _entry(entry_id: str) -> SkillSource:
    return SkillSource(
        id=entry_id,
        name=entry_id.title(),
        description="",
        source_type="git",
        source={"uri": f"https://github.com/acme-org/{entry_id}.git"},
    )


@pytest.fixture
def config_repository() -> MagicMock:
    repository = MagicMock()
    repository.exists.return_value = True
    repository.read_section.return_value = []
    return repository


@pytest.fixture
def verify_config(config_repository: MagicMock) -> VerifyConfig:
    return VerifyConfig(config_repository=config_repository, validator=RegistryValidator())


def test_verify_passes_for_valid_unique_registry(
    verify_config: VerifyConfig, config_repository: MagicMock
) -> None:
    config_repository.read_section.return_value = [_entry("a"), _entry("b")]

    verify_config.verify(Path("/repo"))


def test_verify_raises_on_duplicate_id(
    verify_config: VerifyConfig, config_repository: MagicMock
) -> None:
    config_repository.read_section.return_value = [_entry("a"), _entry("a")]

    with pytest.raises(DuplicateSourceIdError):
        verify_config.verify(Path("/repo"))


def test_verify_raises_config_not_found_when_no_file(
    verify_config: VerifyConfig, config_repository: MagicMock
) -> None:
    config_repository.exists.return_value = False

    with pytest.raises(ConfigNotFoundError):
        verify_config.verify(Path("/repo"))
