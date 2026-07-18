import pytest

from domain.errors import InvalidRegistryEntryError
from domain.skill_registry import SkillSource


def test_git_entry_defaults_ref_to_main_when_omitted() -> None:
    entry = SkillSource(
        id="agent-pack",
        name="Agent Pack",
        description="",
        source_type="git",
        source={"uri": "https://github.com/acme-org/agent-pack.git"},
    )

    assert entry.source.ref == "main"


def test_git_entry_keeps_explicit_ref() -> None:
    entry = SkillSource(
        id="agent-pack",
        name="Agent Pack",
        description="",
        source_type="git",
        source={"uri": "https://github.com/acme-org/agent-pack.git", "ref": "develop"},
    )

    assert entry.source.ref == "develop"


def test_local_entry_has_no_ref() -> None:
    entry = SkillSource(
        id="my-experiment",
        name="My Experiment",
        description="",
        source_type="local",
        source={"uri": "./experiments/my-skills"},
    )

    assert entry.source.ref is None


def test_local_entry_rejects_explicit_ref() -> None:
    with pytest.raises(InvalidRegistryEntryError):
        SkillSource(
            id="my-experiment",
            name="My Experiment",
            description="",
            source_type="local",
            source={"uri": "./experiments/my-skills", "ref": "develop"},
        )
