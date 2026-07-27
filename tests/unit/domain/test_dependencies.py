import pytest
from pydantic import TypeAdapter, ValidationError

from domain.dependencies import ByPatternDependency, Dependencies


def test_parses_kebab_case_fields_from_disk() -> None:
    raw = {
        "target-platforms": ["claude", "cursor"],
        "skills": ["code-review", "spec-*"],
        "by-pattern": [{"category": "vs-code-settings", "action": "json_merge"}],
    }

    dependencies = TypeAdapter(Dependencies).validate_python(raw)

    assert dependencies.target_platforms == ["claude", "cursor"]
    assert dependencies.skills == ["code-review", "spec-*"]
    assert dependencies.by_pattern == [
        ByPatternDependency(category="vs-code-settings", action="json_merge")
    ]


def test_empty_block_defaults_all_categories_to_empty() -> None:
    dependencies = Dependencies()

    assert dependencies.target_platforms == []
    assert dependencies.agents == []
    assert dependencies.skills == []
    assert dependencies.commands == []
    assert dependencies.rules == []
    assert dependencies.by_pattern == []


def test_round_trips_through_kebab_aliases() -> None:
    dependencies = Dependencies(
        target_platforms=["claude"],
        by_pattern=[ByPatternDependency(category="vs-code-settings", action="init")],
    )

    dumped = dependencies.model_dump(by_alias=True)

    assert "target-platforms" in dumped
    assert dumped["by-pattern"][0]["category"] == "vs-code-settings"


def test_invalid_by_pattern_action_rejected() -> None:
    with pytest.raises(ValidationError):
        ByPatternDependency(category="vs-code-settings", action="overwrite")
