from pathlib import Path
from typing import Protocol


class WorkspaceLocator(Protocol):
    """Resolves the workspace root for a CLI invocation.

    Never raises: an explicit path is returned as-is, otherwise the locator
    walks up from cwd for a `.git` directory or an `ossify-cogents.json`
    file, falling back to cwd itself. Whether a usable config file actually
    exists at the resolved root is a fact for each use case to react to.
    """

    def resolve(self, explicit: Path | None) -> Path: ...
