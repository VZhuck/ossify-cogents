from domain.discovery import ByPatternRule, DiscoveryDefinition, GlobRule, Mapping


def test_discovery_definition_parses_fixed_category_mapping() -> None:
    definition = DiscoveryDefinition(
        id="my-strategy",
        mappings=Mapping(rules=[GlobRule(type="folder", path="rules")]),
    )

    assert definition.mappings.rules == [GlobRule(type="folder", path="rules")]


def test_by_pattern_rule_declares_its_own_category() -> None:
    rule = ByPatternRule(type="folder", path="playbooks", category="playbooks")

    assert rule.category == "playbooks"


def test_mapping_by_pattern_field_dumps_as_kebab_alias() -> None:
    mapping = Mapping(by_pattern=[ByPatternRule(type="file", path="a.md", category="docs")])

    dumped = mapping.model_dump(mode="json", by_alias=True)

    assert "by-pattern" in dumped
    assert "by_pattern" not in dumped


def test_discovery_definition_type_defaults_to_custom() -> None:
    definition = DiscoveryDefinition(id="my-strategy", mappings=Mapping())

    assert definition.type == "custom"


def test_mapping_categories_default_to_empty_lists() -> None:
    mapping = Mapping()

    assert mapping.agents == []
    assert mapping.skills == []
    assert mapping.commands == []
    assert mapping.rules == []
    assert mapping.by_pattern == []
