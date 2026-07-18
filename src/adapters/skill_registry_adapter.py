"""Implements `ports_out.RegistryRepository` — a thin proxy over `ConfigRepository`."""

from pathlib import Path

from domain.errors import ConfigNotFoundError
from domain.ossify_config import ConfigSection
from domain.skill_registry import SkillSource
from ports_out import ConfigRepository

_SECTION_MODEL = list[SkillSource]


class SkillRegistryAdapter:
    """CRUD over the skill-registry section, composing a `ConfigRepository`."""

    def __init__(self, config_repository: ConfigRepository) -> None:
        self._config_repository = config_repository

    def get_all(self, root: Path) -> list[SkillSource]:
        if not self._config_repository.exists(root):
            raise ConfigNotFoundError(f"no ossify-cogents.json found at {root}")
        entries = self._config_repository.read_section(
            root, ConfigSection.SKILL_REGISTRY, _SECTION_MODEL
        )
        return entries or []

    def add(self, root: Path, entry: SkillSource) -> None:
        existing = self._config_repository.read_section(
            root, ConfigSection.SKILL_REGISTRY, _SECTION_MODEL
        )
        updated = [*(existing or []), entry]
        self._config_repository.write_section(
            root, ConfigSection.SKILL_REGISTRY, updated, _SECTION_MODEL
        )
