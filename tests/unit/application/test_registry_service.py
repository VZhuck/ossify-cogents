from pathlib import Path
from unittest.mock import MagicMock

import pytest

from application import RegistryService
from application.services import RegistryValidator, SourceInferenceService
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


@pytest.fixture
def registry_repository() -> MagicMock:
    repository = MagicMock()
    repository.get_all.return_value = []
    return repository


@pytest.fixture
def service(registry_repository: MagicMock) -> RegistryService:
    return RegistryService(
        registry_repository=registry_repository,
        inference_service=SourceInferenceService(),
        validator=RegistryValidator(),
    )


def test_get_all_delegates_to_repository(
    service: RegistryService, registry_repository: MagicMock
) -> None:
    registry_repository.get_all.return_value = [_entry("a")]

    result = service.get_all(Path("/repo"))

    assert result == [_entry("a")]
    registry_repository.get_all.assert_called_once_with(Path("/repo"))


def test_add_infers_id_and_name_when_not_supplied(
    service: RegistryService, registry_repository: MagicMock
) -> None:
    entry = service.add(Path("/repo"), uri="https://github.com/acme-org/agent-pack.git")

    assert entry.id == "agent-pack"
    assert entry.name == "Agent Pack"
    assert entry.source.ref == "main"
    registry_repository.add.assert_called_once_with(Path("/repo"), entry)


def test_add_explicit_overrides_win_over_inference(
    service: RegistryService, registry_repository: MagicMock
) -> None:
    entry = service.add(
        Path("/repo"),
        uri="https://github.com/acme-org/agent-pack.git",
        id="custom-id",
        name="Custom Name",
    )

    assert entry.id == "custom-id"
    assert entry.name == "Custom Name"


def test_add_rejects_duplicate_id(
    service: RegistryService, registry_repository: MagicMock
) -> None:
    registry_repository.get_all.return_value = [_entry("agent-pack")]

    with pytest.raises(DuplicateSourceIdError):
        service.add(Path("/repo"), uri="https://github.com/acme-org/agent-pack.git")

    registry_repository.add.assert_not_called()


def test_add_local_source_has_no_ref(
    service: RegistryService, registry_repository: MagicMock
) -> None:
    entry = service.add(Path("/repo"), uri="./experiments/my-skills", source_type="local")

    assert entry.source.ref is None
