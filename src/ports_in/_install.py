from pathlib import Path
from typing import Protocol

from domain.install_report import InstallReport


class InstallPort(Protocol):
    """Runs the end-to-end install pipeline for every registry entry at the root.

    For each entry: materialize its source, execute its discovery strategies,
    resolve its `install` selections, and write the selected capabilities into
    the repo. Returns a per-entry summary the entrypoint renders.
    """

    def install(self, root: Path) -> InstallReport: ...
