import pytest

from application.services import InstallResolver
from domain.dependencies import Dependencies
from domain.discovery import ByPatternRule, DiscoveryDefinition, Mapping
from domain.errors import (
    UnknownTargetPlatformError,
    UnmatchedInstallSelectionError,
    UnresolvableByPatternCategoryError,
)
from domain.skill_registry import SkillSource


def _entry(discovery: list[str] | None = None, install: Dependencies | None = None) -> SkillSource:
    return SkillSource(
        id="agent-pack",
        name="Agent Pack",
        description="",
        source_type="git",
        source={"uri": "https://github.com/acme-org/agent-pack.git"},
        discovery=discovery or [],
        install=install or Dependencies(),
    )


def _by_pattern_definition(definition_id: str, category: str) -> DiscoveryDefinition:
    return DiscoveryDefinition(
        id=definition_id,
        mappings=Mapping(
            by_pattern=[ByPatternRule(type="file", path=".vscode/settings.json", category=category)]
        ),
    )


@pytest.fixture
def resolver() -> InstallResolver:
    return InstallResolver(supported_platforms={"claude", "cursor"})


# --- static: target platforms -------------------------------------------------


def test_star_target_platform_is_allowed(resolver: InstallResolver) -> None:
    entry = _entry(install=Dependencies(target_platforms=["*"]))

    resolver.validate_static([entry], {})


def test_known_target_platform_is_allowed(resolver: InstallResolver) -> None:
    entry = _entry(install=Dependencies(target_platforms=["claude"]))

    resolver.validate_static([entry], {})


def test_unknown_target_platform_raises(resolver: InstallResolver) -> None:
    entry = _entry(install=Dependencies(target_platforms=["eclipse"]))

    with pytest.raises(UnknownTargetPlatformError):
        resolver.validate_static([entry], {})


# --- static: by-pattern categories -------------------------------------------


def test_resolvable_by_pattern_category_passes(resolver: InstallResolver) -> None:
    definition = _by_pattern_definition("custom-strat", "vs-code-settings")
    entry = _entry(
        discovery=["custom-strat"],
        install=Dependencies(by_pattern=[{"category": "vs-code-settings", "action": "json_merge"}]),
    )

    resolver.validate_static([entry], {"custom-strat": definition})


def test_unresolvable_by_pattern_category_raises(resolver: InstallResolver) -> None:
    definition = _by_pattern_definition("custom-strat", "vs-code-settings")
    entry = _entry(
        discovery=["custom-strat"],
        install=Dependencies(by_pattern=[{"category": "unknown", "action": "init"}]),
    )

    with pytest.raises(UnresolvableByPatternCategoryError):
        resolver.validate_static([entry], {"custom-strat": definition})


# --- dynamic: glob selection --------------------------------------------------


def test_star_selects_all_discovered_ids(resolver: InstallResolver) -> None:
    selected, warnings = resolver.select(["*"], ["a", "b", "c"])

    assert selected == ["a", "b", "c"]
    assert warnings == []


def test_glob_selects_matching_subset(resolver: InstallResolver) -> None:
    selected, warnings = resolver.select(["spec-*"], ["spec-writer", "planner"])

    assert selected == ["spec-writer"]
    assert warnings == []


def test_exact_literal_matching_nothing_raises(resolver: InstallResolver) -> None:
    with pytest.raises(UnmatchedInstallSelectionError):
        resolver.select(["code-review"], ["planner"])


def test_glob_matching_nothing_is_a_warning(resolver: InstallResolver) -> None:
    selected, warnings = resolver.select(["spec-*"], ["planner"])

    assert selected == []
    assert warnings == ["spec-*"]


def test_selection_deduplicates_overlapping_patterns(resolver: InstallResolver) -> None:
    selected, _ = resolver.select(["*", "planner"], ["planner", "writer"])

    assert selected == ["planner", "writer"]
