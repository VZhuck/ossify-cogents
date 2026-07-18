import json
from pathlib import Path

from adapters.ossify_config_adapter import OssifyConfigAdapter
from domain.ossify_config import ConfigSection
from domain.skill_registry import SkillSource


def _entry(entry_id: str) -> SkillSource:
    return SkillSource(
        id=entry_id,
        name=entry_id.title(),
        description="",
        source_type="git",
        source={"uri": f"https://github.com/acme-org/{entry_id}.git"},
    )


def test_exists_is_false_when_no_config_file(tmp_path: Path) -> None:
    adapter = OssifyConfigAdapter()

    assert adapter.exists(tmp_path) is False


def test_read_section_returns_none_when_section_absent(tmp_path: Path) -> None:
    (tmp_path / "ossify-cogents.json").write_text("{}")
    adapter = OssifyConfigAdapter()

    result = adapter.read_section(tmp_path, ConfigSection.SKILL_REGISTRY, list[SkillSource])

    assert result is None


def test_write_then_read_round_trips_entries(tmp_path: Path) -> None:
    adapter = OssifyConfigAdapter()
    entries = [_entry("agent-pack")]

    adapter.write_section(tmp_path, ConfigSection.SKILL_REGISTRY, entries, list[SkillSource])
    result = adapter.read_section(tmp_path, ConfigSection.SKILL_REGISTRY, list[SkillSource])

    assert result == entries
    assert adapter.exists(tmp_path) is True


def test_write_section_preserves_unrecognized_top_level_keys(tmp_path: Path) -> None:
    config_path = tmp_path / "ossify-cogents.json"
    config_path.write_text(json.dumps({"some-future-section": {"x": 1}}))
    adapter = OssifyConfigAdapter()

    adapter.write_section(tmp_path, ConfigSection.SKILL_REGISTRY, [_entry("a")], list[SkillSource])

    raw = json.loads(config_path.read_text())
    assert raw["some-future-section"] == {"x": 1}
    assert raw["ossify-skills-registry"][0]["id"] == "a"
