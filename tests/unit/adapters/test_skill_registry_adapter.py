from pathlib import Path
from unittest.mock import MagicMock

import pytest

from adapters.skill_registry_adapter import SkillRegistryAdapter
from domain.errors import ConfigNotFoundError
from domain.ossify_config import ConfigSection
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
    repository.read_section.return_value = None
    return repository


@pytest.fixture
def adapter(config_repository: MagicMock) -> SkillRegistryAdapter:
    return SkillRegistryAdapter(config_repository=config_repository)


def test_get_all_raises_when_no_config_file(
    adapter: SkillRegistryAdapter, config_repository: MagicMock
) -> None:
    config_repository.exists.return_value = False

    with pytest.raises(ConfigNotFoundError):
        adapter.get_all(Path("/repo"))


def test_get_all_returns_empty_list_when_section_absent(
    adapter: SkillRegistryAdapter,
) -> None:
    result = adapter.get_all(Path("/repo"))

    assert result == []


def test_add_appends_to_existing_entries(
    adapter: SkillRegistryAdapter, config_repository: MagicMock
) -> None:
    config_repository.read_section.return_value = [_entry("a")]

    adapter.add(Path("/repo"), _entry("b"))

    config_repository.write_section.assert_called_once_with(
        Path("/repo"), ConfigSection.SKILL_REGISTRY, [_entry("a"), _entry("b")], list[SkillSource]
    )
