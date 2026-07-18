from pathlib import Path
from typing import Protocol


class OssifyConfigPort(Protocol):
    """Validates the ossify-cogents.json config file.

    Only `verify()` for now — room to grow if `ossify-cogents config` gains
    further subcommands later.
    """

    def verify(self, root: Path) -> None: ...
