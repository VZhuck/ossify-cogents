"""Use cases: implement `ports_in/`, depend on `ports_out/`.

Never imported directly by `adapters/`, `cli/`, or `tui/` — only `container.py`
constructs these and hands wired instances to entrypoints.
"""

from application._get_version import GetVersion
from application._init_config import InitConfig
from application._install_capabilities import InstallCapabilities
from application._registry_service import RegistryService
from application._verify_config import VerifyConfig

__all__ = [
    "GetVersion",
    "InitConfig",
    "InstallCapabilities",
    "RegistryService",
    "VerifyConfig",
]
