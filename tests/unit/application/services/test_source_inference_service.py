import pytest

from application.services import SourceInferenceService


@pytest.fixture
def service() -> SourceInferenceService:
    return SourceInferenceService()


def test_infer_id_from_git_url(service: SourceInferenceService) -> None:
    result = service.infer_id("https://github.com/acme-org/agent-pack.git")

    assert result == "agent-pack"


def test_infer_name_from_git_url(service: SourceInferenceService) -> None:
    result = service.infer_name("https://github.com/acme-org/agent-pack.git")

    assert result == "Agent Pack"


def test_infer_id_from_local_path(service: SourceInferenceService) -> None:
    result = service.infer_id("./experiments/my-skills")

    assert result == "my-skills"


def test_infer_description_is_always_empty(service: SourceInferenceService) -> None:
    result = service.infer_description("https://github.com/acme-org/agent-pack.git")

    assert result == ""
