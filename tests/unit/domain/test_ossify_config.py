from domain.ossify_config import ConfigSection, OssifyConfig


def test_from_raw_and_to_raw_round_trip() -> None:
    raw = {"ossify-skills-registry": [{"id": "a"}], "some-future-section": {"x": 1}}

    config = OssifyConfig.from_raw(raw)

    assert config.to_raw() == raw


def test_section_value_returns_none_when_absent() -> None:
    config = OssifyConfig.from_raw({})

    assert config.section_value(ConfigSection.SKILL_REGISTRY) is None


def test_with_section_value_preserves_other_sections() -> None:
    config = OssifyConfig.from_raw({"some-future-section": {"x": 1}})

    updated = config.with_section_value(ConfigSection.SKILL_REGISTRY, [{"id": "a"}])

    assert updated.section_value(ConfigSection.SKILL_REGISTRY) == [{"id": "a"}]
    assert updated.to_raw()["some-future-section"] == {"x": 1}
