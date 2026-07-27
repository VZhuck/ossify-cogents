from pathlib import Path

import pytest

from application import InitConfig
from domain._defaults import DEFAULT_DISCOVERY_DEFINITION, DEFAULT_REGISTRY_ITEM
from domain.errors import ConfigAlreadyExistsError
from domain.ossify_config import ConfigSection
from domain.skill_registry import SkillSource


class _FakeConfigRepository:
    """Records write_section/delete calls and answers exists() from a flag."""

    def __init__(self, exists: bool) -> None:
        self._exists = exists
        self.writes: list[tuple[ConfigSection, object]] = []
        self.deleted = False

    def exists(self, root: Path) -> bool:
        return self._exists

    def delete(self, root: Path) -> None:
        self.deleted = True

    def read_section(self, root: Path, section: ConfigSection, model: type) -> object | None:
        return None

    def write_section(self, root: Path, section: ConfigSection, value: object, model: type) -> None:
        self.writes.append((section, value))


def test_writes_both_default_sections_in_empty_workspace(tmp_path: Path) -> None:
    repo = _FakeConfigRepository(exists=False)

    InitConfig(repo).init(tmp_path)

    written = {section: value for section, value in repo.writes}
    assert written[ConfigSection.SKILL_REGISTRY] == [DEFAULT_REGISTRY_ITEM]
    assert written[ConfigSection.DISCOVERY_DEFINITIONS] == [DEFAULT_DISCOVERY_DEFINITION]
    assert repo.deleted is False


def test_raises_and_writes_nothing_when_config_exists_without_force(tmp_path: Path) -> None:
    repo = _FakeConfigRepository(exists=True)

    with pytest.raises(ConfigAlreadyExistsError):
        InitConfig(repo).init(tmp_path)

    assert repo.writes == []
    assert repo.deleted is False


def test_force_deletes_then_writes_when_config_exists(tmp_path: Path) -> None:
    repo = _FakeConfigRepository(exists=True)

    InitConfig(repo).init(tmp_path, force=True)

    assert repo.deleted is True
    written = {section for section, _ in repo.writes}
    assert written == {ConfigSection.SKILL_REGISTRY, ConfigSection.DISCOVERY_DEFINITIONS}


def test_registry_section_value_is_a_single_skill_source(tmp_path: Path) -> None:
    repo = _FakeConfigRepository(exists=False)

    InitConfig(repo).init(tmp_path)

    written = {section: value for section, value in repo.writes}
    registry = written[ConfigSection.SKILL_REGISTRY]
    assert isinstance(registry, list)
    assert len(registry) == 1
    assert isinstance(registry[0], SkillSource)
