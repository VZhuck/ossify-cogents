from pydantic import TypeAdapter

from domain._builtins import BUILTIN_DISCOVERY_STRATEGIES, OSSIFY_OPEN_STANDARD
from domain._defaults import DEFAULT_DISCOVERY_DEFINITION, DEFAULT_REGISTRY_ITEM
from domain.discovery import DiscoveryDefinition
from domain.skill_registry import SkillSource


def test_default_item_is_a_valid_skill_source() -> None:
    assert isinstance(DEFAULT_REGISTRY_ITEM, SkillSource)
    assert DEFAULT_REGISTRY_ITEM.source_type == "git"
    assert DEFAULT_REGISTRY_ITEM.source.uri == "https://github.com/anthropics/skills"
    assert DEFAULT_REGISTRY_ITEM.source.ref == "main"
    assert DEFAULT_REGISTRY_ITEM.discovery == ["ossify-open-standard"]


def test_default_install_is_an_explicit_empty_skeleton() -> None:
    install = DEFAULT_REGISTRY_ITEM.install

    assert install.target_platforms == ["claude"]
    assert install.agents == []
    assert install.skills == []
    assert install.commands == []
    assert install.rules == []
    assert install.by_pattern == []


def test_default_item_dumps_kebab_skeleton_on_disk() -> None:
    raw = TypeAdapter(SkillSource).dump_python(
        DEFAULT_REGISTRY_ITEM, mode="json", exclude_none=True, by_alias=True
    )

    assert raw["source-type"] == "git"
    assert raw["discovery"] == ["ossify-open-standard"]
    # every install field is present (empty lists are not elided) so the
    # written file documents the block's shape
    assert raw["install"] == {
        "target-platforms": ["claude"],
        "agents": [],
        "skills": [],
        "commands": [],
        "rules": [],
        "by-pattern": [],
    }


def test_default_item_round_trips_through_disk_shape() -> None:
    raw = TypeAdapter(SkillSource).dump_python(
        DEFAULT_REGISTRY_ITEM, mode="json", exclude_none=True, by_alias=True
    )
    reloaded = TypeAdapter(SkillSource).validate_python(raw)

    assert reloaded == DEFAULT_REGISTRY_ITEM


def test_default_discovery_definition_mirrors_open_standard_mappings() -> None:
    assert isinstance(DEFAULT_DISCOVERY_DEFINITION, DiscoveryDefinition)
    assert DEFAULT_DISCOVERY_DEFINITION.type == "custom"
    assert DEFAULT_DISCOVERY_DEFINITION.mappings == OSSIFY_OPEN_STANDARD.mappings


def test_default_discovery_definition_id_does_not_collide_with_builtins() -> None:
    builtin_ids = {strategy.id for strategy in BUILTIN_DISCOVERY_STRATEGIES}

    assert DEFAULT_DISCOVERY_DEFINITION.id not in builtin_ids
    assert not DEFAULT_DISCOVERY_DEFINITION.id.startswith("ossify-")
