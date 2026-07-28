"""Dependency-injector wiring.

The only module in this project allowed to import both `application/` and
`adapters/` at once, in order to construct concrete use cases and hand
already-wired instances to `cli/`/`tui/`.
"""

from dependency_injector import containers, providers

from adapters.ossify_config_adapter import OssifyConfigAdapter
from adapters.skill_registry_adapter import SkillRegistryAdapter
from adapters.sources import GitSourceAdapter, LocalSourceAdapter
from adapters.targets import FilesystemTargetAdapter
from adapters.workspace_adapter import WorkspaceAdapter
from application import GetVersion, InitConfig, InstallCapabilities, RegistryService, VerifyConfig
from application.services import (
    DiscoveryExecution,
    DiscoveryResolver,
    InstallResolver,
    RegistryValidator,
    SourceInferenceService,
    TargetLayout,
)
from domain._builtins import BUILTIN_DISCOVERY_STRATEGIES, SUPPORTED_TARGET_PLATFORMS


class Container(containers.DeclarativeContainer):
    get_version_use_case = providers.Factory(GetVersion)

    workspace_locator = providers.Factory(WorkspaceAdapter)
    ossify_config_adapter = providers.Factory(OssifyConfigAdapter)
    skill_registry_adapter = providers.Factory(
        SkillRegistryAdapter, config_repository=ossify_config_adapter
    )

    # Target adapter is rooted at the workspace by its consumer (the install use
    # case) at call time; registered here so no other module constructs it.
    target_adapter = providers.Factory(FilesystemTargetAdapter)

    # Source adapters keyed by `source-type`; the install use case dispatches by key.
    git_source_adapter = providers.Factory(GitSourceAdapter)
    local_source_adapter = providers.Factory(LocalSourceAdapter)
    source_adapters = providers.Dict(git=git_source_adapter, local=local_source_adapter)

    source_inference_service = providers.Factory(SourceInferenceService)
    registry_validator = providers.Factory(RegistryValidator)
    discovery_resolver = providers.Factory(DiscoveryResolver, builtins=BUILTIN_DISCOVERY_STRATEGIES)
    discovery_execution = providers.Factory(DiscoveryExecution)
    install_resolver = providers.Factory(
        InstallResolver, supported_platforms=SUPPORTED_TARGET_PLATFORMS
    )
    target_layout = providers.Factory(TargetLayout)

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
    init_use_case = providers.Factory(InitConfig, config_repository=ossify_config_adapter)
    install_use_case = providers.Factory(
        InstallCapabilities,
        config_repository=ossify_config_adapter,
        sources=source_adapters,
        discovery_resolver=discovery_resolver,
        discovery_execution=discovery_execution,
        install_resolver=install_resolver,
        target_layout=target_layout,
        target_factory=target_adapter.provider,
    )
