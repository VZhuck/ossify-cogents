from pathlib import Path

from application.services import RegistryValidator
from domain.errors import ConfigNotFoundError
from domain.ossify_config import ConfigSection
from domain.skill_registry import SkillSource
from ports_out import ConfigRepository


class VerifyConfig:
    """Implements `ports_in.OssifyConfigPort` — schema + duplicate-id validation."""

    def __init__(self, config_repository: ConfigRepository, validator: RegistryValidator) -> None:
        self._config_repository = config_repository
        self._validator = validator

    def verify(self, root: Path) -> None:
        if not self._config_repository.exists(root):
            raise ConfigNotFoundError(f"no ossify-cogents.json found at {root}")

        entries = self._config_repository.read_section(
            root, ConfigSection.SKILL_REGISTRY, list[SkillSource]
        )
        self._validator.validate(entries or [])
