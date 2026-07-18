from pathlib import Path
from typing import Protocol

from domain.skill_registry import SkillSource


class RegistryRepository(Protocol):
    """CRUD over the skill-registry config section specifically."""

    def get_all(self, root: Path) -> list[SkillSource]: ...

    def add(self, root: Path, entry: SkillSource) -> None: ...
