import json
from pathlib import Path

from typer.testing import CliRunner

from cli import app
from domain.dependencies import Dependencies

runner = CliRunner()


def test_registry_add_creates_config_and_infers_defaults(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(tmp_path),
            "registry",
            "add",
            "https://github.com/acme-org/agent-pack.git",
        ],
    )

    assert result.exit_code == 0, result.stdout
    raw = json.loads((tmp_path / "ossify-cogents.json").read_text())
    assert raw["ossify-skills-registry"][0]["id"] == "agent-pack"
    assert raw["ossify-skills-registry"][0]["source"]["ref"] == "main"


def test_registry_add_local_source(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(tmp_path),
            "registry",
            "add",
            "./experiments/my-skills",
            "--source-type",
            "local",
        ],
    )

    assert result.exit_code == 0, result.stdout
    raw = json.loads((tmp_path / "ossify-cogents.json").read_text())
    entry = raw["ossify-skills-registry"][0]
    assert entry["source-type"] == "local"
    assert "ref" not in entry["source"]


def test_registry_add_rejects_ref_with_local_source_type(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(tmp_path),
            "registry",
            "add",
            "./experiments/my-skills",
            "--source-type",
            "local",
            "--source.ref",
            "develop",
        ],
    )

    assert result.exit_code != 0
    assert not (tmp_path / "ossify-cogents.json").exists()


def test_registry_add_rejects_conflicting_uri_inputs(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(tmp_path),
            "registry",
            "add",
            "https://github.com/acme-org/agent-pack.git",
            "--source.uri",
            "https://github.com/other-org/other-pack.git",
        ],
    )

    assert result.exit_code != 0


def test_registry_get_lists_added_entries(tmp_path: Path) -> None:
    runner.invoke(
        app,
        [
            "--workspace",
            str(tmp_path),
            "registry",
            "add",
            "https://github.com/acme-org/agent-pack.git",
        ],
    )

    result = runner.invoke(app, ["--workspace", str(tmp_path), "registry", "get"])

    assert result.exit_code == 0
    assert "agent-pack" in result.stdout


def test_registry_get_reports_no_config_found(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--workspace", str(tmp_path), "registry", "get"])

    assert result.exit_code != 0


def test_registry_add_preserves_hand_authored_install_on_sibling_entry(tmp_path: Path) -> None:
    runner.invoke(
        app,
        ["--workspace", str(tmp_path), "registry", "add", "https://github.com/acme-org/first.git"],
    )
    config_path = tmp_path / "ossify-cogents.json"
    raw = json.loads(config_path.read_text())
    hand_authored_install = {
        "target-platforms": ["claude"],
        "skills": ["code-review"],
        "by-pattern": [{"category": "vs-code-settings", "action": "json_merge"}],
    }
    raw["ossify-skills-registry"][0]["install"] = hand_authored_install
    config_path.write_text(json.dumps(raw))

    result = runner.invoke(
        app,
        ["--workspace", str(tmp_path), "registry", "add", "https://github.com/acme-org/second.git"],
    )

    assert result.exit_code == 0, result.stdout
    updated = json.loads(config_path.read_text())
    # Round-trip normalizes the block (omitted empty categories materialize to []),
    # but every declared value is preserved — nothing hand-authored is dropped.
    preserved = updated["ossify-skills-registry"][0]["install"]
    assert Dependencies.model_validate(preserved) == Dependencies.model_validate(
        hand_authored_install
    )


def test_config_verify_passes_for_valid_registry(tmp_path: Path) -> None:
    runner.invoke(
        app,
        [
            "--workspace",
            str(tmp_path),
            "registry",
            "add",
            "https://github.com/acme-org/agent-pack.git",
        ],
    )

    result = runner.invoke(app, ["--workspace", str(tmp_path), "config", "verify"])

    assert result.exit_code == 0


def test_config_verify_reports_no_config_found(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--workspace", str(tmp_path), "config", "verify"])

    assert result.exit_code != 0


def test_config_verify_passes_for_builtin_discovery_id(tmp_path: Path) -> None:
    runner.invoke(
        app,
        [
            "--workspace",
            str(tmp_path),
            "registry",
            "add",
            "https://github.com/acme-org/agent-pack.git",
        ],
    )
    config_path = tmp_path / "ossify-cogents.json"
    raw = json.loads(config_path.read_text())
    raw["ossify-skills-registry"][0]["discovery"] = ["ossify-open-standard"]
    config_path.write_text(json.dumps(raw))

    result = runner.invoke(app, ["--workspace", str(tmp_path), "config", "verify"])

    assert result.exit_code == 0, result.stdout


def test_config_verify_fails_for_unresolvable_discovery_id(tmp_path: Path) -> None:
    runner.invoke(
        app,
        [
            "--workspace",
            str(tmp_path),
            "registry",
            "add",
            "https://github.com/acme-org/agent-pack.git",
        ],
    )
    config_path = tmp_path / "ossify-cogents.json"
    raw = json.loads(config_path.read_text())
    raw["ossify-skills-registry"][0]["discovery"] = ["no-such-strategy"]
    config_path.write_text(json.dumps(raw))

    result = runner.invoke(app, ["--workspace", str(tmp_path), "config", "verify"])

    assert result.exit_code != 0


def test_config_verify_fails_for_discovery_definition_colliding_with_builtin(
    tmp_path: Path,
) -> None:
    runner.invoke(
        app,
        [
            "--workspace",
            str(tmp_path),
            "registry",
            "add",
            "https://github.com/acme-org/agent-pack.git",
        ],
    )
    config_path = tmp_path / "ossify-cogents.json"
    raw = json.loads(config_path.read_text())
    raw["discovery-definitions"] = [
        {"id": "ossify-open-standard", "type": "custom", "mappings": {}}
    ]
    config_path.write_text(json.dumps(raw))

    result = runner.invoke(app, ["--workspace", str(tmp_path), "config", "verify"])

    assert result.exit_code != 0


def test_config_verify_rejects_link_mode_on_a_git_source(tmp_path: Path) -> None:
    # Enforced by the `SkillSource` model validator, so `config verify` catches it
    # while parsing — offline, without fetching the source.
    (tmp_path / "ossify-cogents.json").write_text(
        json.dumps(
            {
                "ossify-skills-registry": [
                    {
                        "id": "agent-pack",
                        "name": "Agent Pack",
                        "description": "",
                        "source-type": "git",
                        "source": {"uri": "https://github.com/acme-org/agent-pack.git"},
                        "discovery": [],
                        "install": {"mode": "link"},
                    }
                ]
            }
        )
    )

    result = runner.invoke(app, ["--workspace", str(tmp_path), "config", "verify"])

    assert result.exit_code != 0
