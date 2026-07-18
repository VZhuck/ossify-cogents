from pathlib import Path
from typing import Literal, Protocol

from domain.skill_registry import SkillSource


class RegistryPort(Protocol):
    """Read and write access to the skill registry.

    Deliberately bundles get+add on one protocol rather than following the
    1-port-1-verb-phrase-use-case convention used elsewhere — see design.md.
    """

    def get_all(self, root: Path) -> list[SkillSource]: ...

    def add(
        self,
        root: Path,
        *,
        uri: str,
        source_type: Literal["git", "local"] = "git",
        ref: str | None = None,
        id: str | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> SkillSource: ...
