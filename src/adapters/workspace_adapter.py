"""Implements `ports_out.WorkspaceLocator` — represents the dev repo folder on disk."""

from pathlib import Path

CONFIG_FILENAME = "ossify-cogents.json"
GIT_DIR_NAME = ".git"


class WorkspaceAdapter:
    """Resolves the workspace root: explicit override, then `.git`/config walk-up, then cwd."""

    def resolve(self, explicit: Path | None) -> Path:
        if explicit is not None:
            return explicit

        for candidate in (Path.cwd(), *Path.cwd().parents):
            if (candidate / GIT_DIR_NAME).is_dir() or (candidate / CONFIG_FILENAME).is_file():
                return candidate

        return Path.cwd()
