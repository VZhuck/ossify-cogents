from pathlib import Path

from application.services import DiscoveryResolver, RegistryValidator
from domain.discovery import DiscoveryDefinition
from domain.errors import ConfigNotFoundError, UnresolvableDiscoveryIdError
from domain.ossify_config import ConfigSection
from domain.skill_registry import SkillSource
from ports_out import ConfigRepository


class VerifyConfig:
    """Implements `ports_in.OssifyConfigPort` — schema + duplicate-id + discovery-id validation."""

    def __init__(
        self,
        config_repository: ConfigRepository,
        validator: RegistryValidator,
        discovery_resolver: DiscoveryResolver,
    ) -> None:
        self._config_repository = config_repository
        self._validator = validator
        self._discovery_resolver = discovery_resolver

    def verify(self, root: Path) -> None:
        if not self._config_repository.exists(root):
            raise ConfigNotFoundError(f"no ossify-cogents.json found at {root}")

        entries = (
            self._config_repository.read_section(
                root, ConfigSection.SKILL_REGISTRY, list[SkillSource]
            )
            or []
        )
        self._validator.validate(entries)

        custom_definitions = (
            self._config_repository.read_section(
                root, ConfigSection.DISCOVERY_DEFINITIONS, list[DiscoveryDefinition]
            )
            or []
        )
        resolvable_ids = self._discovery_resolver.resolvable_ids(custom_definitions)

        for entry in entries:
            for discovery_id in entry.discovery:
                if discovery_id not in resolvable_ids:
                    raise UnresolvableDiscoveryIdError(
                        f"unresolvable discovery id {discovery_id!r} on registry entry {entry.id!r}"
                    )
