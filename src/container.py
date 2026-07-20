"""Dependency-injector wiring.

The only module in this project allowed to import both `application/` and
`adapters/` at once, in order to construct concrete use cases and hand
already-wired instances to `cli/`/`tui/`.
"""

from dependency_injector import containers, providers

from adapters.ossify_config_adapter import OssifyConfigAdapter
from adapters.skill_registry_adapter import SkillRegistryAdapter
from adapters.workspace_adapter import WorkspaceAdapter
from application import GetVersion, RegistryService, VerifyConfig
from application.services import DiscoveryResolver, RegistryValidator, SourceInferenceService
from domain._builtins import BUILTIN_DISCOVERY_STRATEGIES


class Container(containers.DeclarativeContainer):
    get_version_use_case = providers.Factory(GetVersion)

    workspace_locator = providers.Factory(WorkspaceAdapter)
    ossify_config_adapter = providers.Factory(OssifyConfigAdapter)
    skill_registry_adapter = providers.Factory(
        SkillRegistryAdapter, config_repository=ossify_config_adapter
    )

    source_inference_service = providers.Factory(SourceInferenceService)
    registry_validator = providers.Factory(RegistryValidator)
    discovery_resolver = providers.Factory(DiscoveryResolver, builtins=BUILTIN_DISCOVERY_STRATEGIES)

    registry_use_case = providers.Factory(
        RegistryService,
        registry_repository=skill_registry_adapter,
        inference_service=source_inference_service,
        validator=registry_validator,
    )
    ossify_config_use_case = providers.Factory(
        VerifyConfig,
        config_repository=ossify_config_adapter,
        validator=registry_validator,
        discovery_resolver=discovery_resolver,
    )
