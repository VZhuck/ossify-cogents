from domain.config_model import to_kebab
from domain.skill_registry import SkillSource


def test_to_kebab_replaces_underscores_with_hyphens() -> None:
    assert to_kebab("source_type") == "source-type"
    assert to_kebab("by_pattern") == "by-pattern"


def test_skill_source_dumps_source_type_as_kebab_alias() -> None:
    entry = SkillSource(
        id="agent-pack",
        name="Agent Pack",
        description="",
        source_type="git",
        source={"uri": "https://github.com/acme-org/agent-pack.git"},
    )

    dumped = entry.model_dump(mode="json", by_alias=True)

    assert "source-type" in dumped
    assert "source_type" not in dumped
    assert dumped["source-type"] == "git"


def test_skill_source_still_constructs_by_snake_case_keyword() -> None:
    entry = SkillSource(
        id="agent-pack",
        name="Agent Pack",
        description="",
        source_type="git",
        source={"uri": "https://github.com/acme-org/agent-pack.git"},
    )

    assert entry.source_type == "git"
