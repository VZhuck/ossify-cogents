import pytest
from pydantic import TypeAdapter

from domain.dependencies import Dependencies
from domain.errors import InvalidRegistryEntryError
from domain.skill_registry import SkillSource, Source


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


def test_discovery_defaults_to_empty_list_when_omitted() -> None:
    entry = SkillSource(
        id="agent-pack",
        name="Agent Pack",
        description="",
        source_type="git",
        source={"uri": "https://github.com/acme-org/agent-pack.git"},
    )

    assert entry.discovery == []


def test_discovery_keeps_explicit_ids() -> None:
    entry = SkillSource(
        id="agent-pack",
        name="Agent Pack",
        description="",
        source_type="git",
        source={"uri": "https://github.com/acme-org/agent-pack.git"},
        discovery=["ossify-open-standard"],
    )

    assert entry.discovery == ["ossify-open-standard"]


def test_install_defaults_to_empty_block_when_omitted() -> None:
    entry = TypeAdapter(SkillSource).validate_python(
        {
            "id": "agent-pack",
            "name": "Agent Pack",
            "description": "",
            "source-type": "git",
            "source": {"uri": "https://github.com/acme-org/agent-pack.git"},
        }
    )

    assert entry.install == Dependencies()


def test_populated_install_round_trips_through_kebab_aliases() -> None:
    raw = {
        "id": "agent-pack",
        "name": "Agent Pack",
        "description": "",
        "source-type": "git",
        "source": {"uri": "https://github.com/acme-org/agent-pack.git"},
        "install": {
            "target-platforms": ["claude"],
            "skills": ["code-review"],
            "by-pattern": [{"category": "vs-code-settings", "action": "json_merge"}],
        },
    }

    entry = TypeAdapter(SkillSource).validate_python(raw)

    assert entry.install.target_platforms == ["claude"]
    assert entry.install.skills == ["code-review"]
    assert entry.model_dump(by_alias=True)["install"]["by-pattern"][0]["action"] == "json_merge"


def test_update_via_model_copy_preserves_install_block() -> None:
    # The registry update invariant: patching an entry's source must not drop `install`.
    original = SkillSource(
        id="agent-pack",
        name="Agent Pack",
        description="",
        source_type="git",
        source={"uri": "https://github.com/acme-org/agent-pack.git", "ref": "main"},
        install=Dependencies(skills=["code-review"]),
    )

    patched = original.model_copy(
        update={"source": Source(uri="https://github.com/acme-org/agent-pack.git", ref="develop")}
    )

    assert patched.source.ref == "develop"
    assert patched.install == original.install
