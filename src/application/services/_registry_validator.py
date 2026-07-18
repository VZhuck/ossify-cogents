"""Registry-wide business rules shared by `RegistryService.add` and `VerifyConfig.verify`."""

from domain.errors import DuplicateSourceIdError
from domain.skill_registry import SkillSource


class RegistryValidator:
    """Enforces `id` uniqueness across a set of registry entries."""

    def validate(self, entries: list[SkillSource]) -> None:
        seen: set[str] = set()
        for entry in entries:
            if entry.id in seen:
                raise DuplicateSourceIdError(f"duplicate registry id: {entry.id!r}")
            seen.add(entry.id)
