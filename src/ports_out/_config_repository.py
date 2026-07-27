from pathlib import Path
from typing import Protocol, TypeVar

from domain.ossify_config import ConfigSection

T = TypeVar("T")


class ConfigRepository(Protocol):
    """Section-keyed, round-trip-safe read/write of ossify-cogents.json.

    Writing one section preserves every other top-level key already present
    in the file, including sections this codebase doesn't model.
    """

    def exists(self, root: Path) -> bool: ...

    def delete(self, root: Path) -> None:
        """Remove the config file if present; a no-op when it does not exist."""
        ...

    def read_section(self, root: Path, section: ConfigSection, model: type[T]) -> T | None: ...

    def write_section(
        self, root: Path, section: ConfigSection, value: T, model: type[T]
    ) -> None: ...
