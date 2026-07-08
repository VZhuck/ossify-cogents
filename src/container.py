"""Dependency-injector wiring.

The only module in this project allowed to import both `application/` and
`adapters/` at once, in order to construct concrete use cases and hand
already-wired instances to `cli/`/`tui/`.
"""

from dependency_injector import containers, providers

from application import GetVersion


class Container(containers.DeclarativeContainer):
    get_version_use_case = providers.Factory(GetVersion)
