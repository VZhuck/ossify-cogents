from pathlib import Path
from typing import Protocol


class InitPort(Protocol):
    """Scaffolds a default ossify-cogents.json at the workspace root.

    Without `force`, fast-fails (writes nothing) when a config file already
    exists. With `force`, overrides any existing file wholesale.
    """

    def init(self, root: Path, *, force: bool = False) -> None: ...
