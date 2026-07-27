"""Dependency-injector wiring.

The only module in this project allowed to import both `application/` and
`adapters/` at once, in order to construct concrete use cases and hand
already-wired instances to `cli/`/`tui/`.
"""

from dependency_injector import containers, providers

from adapters.ossify_config_adapter import OssifyConfigAdapter
from adapters.skill_registry_adapter import SkillRegistryAdapter
from adapters.targets import FilesystemTargetAdapter
from adapters.workspace_adapter import WorkspaceAdapter
from application import GetVersion, RegistryService, VerifyConfig
from application.services import (
    DiscoveryResolver,
    InstallResolver,
    RegistryValidator,
    SourceInferenceService,
)
from domain._builtins import BUILTIN_DISCOVERY_STRATEGIES, SUPPORTED_TARGET_PLATFORMS


class Container(containers.DeclarativeContainer):
    get_version_use_case = providers.Factory(GetVersion)

    workspace_locator = providers.Factory(WorkspaceAdapter)
    ossify_config_adapter = providers.Factory(OssifyConfigAdapter)
    skill_registry_adapter = providers.Factory(
        SkillRegistryAdapter, config_repository=ossify_config_adapter
    )

    # Target adapter is rooted at the workspace by its consumer (the future sync
    # use case) at call time; registered here so no other module constructs it.
    target_adapter = providers.Factory(FilesystemTargetAdapter)

    source_inference_service = providers.Factory(SourceInferenceService)
    registry_validator = providers.Factory(RegistryValidator)
    discovery_resolver = providers.Factory(DiscoveryResolver, builtins=BUILTIN_DISCOVERY_STRATEGIES)
    install_resolver = providers.Factory(
        InstallResolver, supported_platforms=SUPPORTED_TARGET_PLATFORMS
    )

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
        install_resolver=install_resolver,
    )
