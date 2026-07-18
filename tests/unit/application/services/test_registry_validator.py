import pytest

from application.services import RegistryValidator
from domain.errors import DuplicateSourceIdError
from domain.skill_registry import SkillSource


def _entry(entry_id: str) -> SkillSource:
    return SkillSource(
        id=entry_id,
        name=entry_id.title(),
        description="",
        source_type="git",
        source={"uri": f"https://github.com/acme-org/{entry_id}.git"},
    )


def test_validate_passes_for_unique_ids() -> None:
    validator = RegistryValidator()

    validator.validate([_entry("a"), _entry("b")])


def test_validate_raises_on_duplicate_id() -> None:
    validator = RegistryValidator()

    with pytest.raises(DuplicateSourceIdError):
        validator.validate([_entry("a"), _entry("a")])
