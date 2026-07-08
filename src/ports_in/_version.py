from typing import Protocol


class VersionPort(Protocol):
    """Reports the installed ossify-cogents version."""

    def get_version(self) -> str: ...
