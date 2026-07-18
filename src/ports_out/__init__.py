"""Outbound ports: interfaces `application/` depends on, implemented by `adapters/`."""

from ports_out._config_repository import ConfigRepository
from ports_out._registry_repository import RegistryRepository
from ports_out._workspace_locator import WorkspaceLocator

__all__ = ["ConfigRepository", "RegistryRepository", "WorkspaceLocator"]
