from pathlib import Path

from domain._defaults import DEFAULT_DISCOVERY_DEFINITION, DEFAULT_REGISTRY_ITEM
from domain.discovery import DiscoveryDefinition
from domain.errors import ConfigAlreadyExistsError
from domain.ossify_config import ConfigSection
from domain.skill_registry import SkillSource
from ports_out import ConfigRepository


class InitConfig:
    """Implements `ports_in.InitPort` — writes a default config, fast-failing unless forced."""

    def __init__(self, config_repository: ConfigRepository) -> None:
        self._config_repository = config_repository

    def init(self, root: Path, *, force: bool = False) -> None:
        if self._config_repository.exists(root):
            if not force:
                raise ConfigAlreadyExistsError(
                    f"ossify-cogents.json already exists at {root} — refusing to overwrite "
                    "(pass --force to override)"
                )
            # Override wholesale: clear the slate first so a possibly-malformed
            # existing file is not read-merged, and no stale sections survive.
            self._config_repository.delete(root)

        self._config_repository.write_section(
            root,
            ConfigSection.SKILL_REGISTRY,
            [DEFAULT_REGISTRY_ITEM],
            list[SkillSource],
        )
        self._config_repository.write_section(
            root,
            ConfigSection.DISCOVERY_DEFINITIONS,
            [DEFAULT_DISCOVERY_DEFINITION],
            list[DiscoveryDefinition],
        )
