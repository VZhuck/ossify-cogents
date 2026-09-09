import json
from pathlib import Path

from typer.testing import CliRunner

from cli import app

runner = CliRunner()


def _init(tmp_path: Path, *args: str):
    return runner.invoke(app, ["--workspace", str(tmp_path), "init", *args])


def test_init_creates_default_config(tmp_path: Path) -> None:
    result = _init(tmp_path)

    assert result.exit_code == 0, result.stdout
    config_path = tmp_path / "ossify-cogents.json"
    assert config_path.is_file()

    raw = json.loads(config_path.read_text())
    entries = raw["ossify-skills-registry"]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["source"]["uri"] == "https://github.com/anthropics/skills"
    assert entry["source-type"] == "git"
    assert entry["discovery"] == ["ossify-open-standard"]
    assert entry["install"] == {
        "mode": "copy",
        "target-platforms": ["claude"],
        "agents": [],
        "skills": [],
        "commands": [],
        "rules": [],
        "by-pattern": [],
    }


def test_init_writes_schema_reference(tmp_path: Path) -> None:
    assert _init(tmp_path).exit_code == 0

    raw = json.loads((tmp_path / "ossify-cogents.json").read_text())
    assert raw["$schema"] == (
        "https://raw.githubusercontent.com/VZhuck/ossify-cogents/main/schema/v1.json"
    )


def test_init_writes_example_discovery_definition(tmp_path: Path) -> None:
    assert _init(tmp_path).exit_code == 0

    raw = json.loads((tmp_path / "ossify-cogents.json").read_text())
    definitions = raw["discovery-definitions"]
    assert len(definitions) == 1
    definition = definitions[0]
    assert definition["id"] == "example-standard"
    assert definition["mappings"]["skills"] == [{"type": "folder", "path": "skills"}]


def test_init_output_passes_config_verify(tmp_path: Path) -> None:
    assert _init(tmp_path).exit_code == 0

    verify = runner.invoke(app, ["--workspace", str(tmp_path), "config", "verify"])
    assert verify.exit_code == 0, verify.stdout


def test_init_fast_fails_and_leaves_existing_config_untouched(tmp_path: Path) -> None:
    assert _init(tmp_path).exit_code == 0
    config_path = tmp_path / "ossify-cogents.json"
    original = config_path.read_bytes()

    second = _init(tmp_path)

    assert second.exit_code != 0
    assert "already exists" in second.stdout
    assert config_path.read_bytes() == original


def test_init_force_overwrites_hand_edited_config(tmp_path: Path) -> None:
    config_path = tmp_path / "ossify-cogents.json"
    config_path.write_text(json.dumps({"ossify-skills-registry": [{"id": "hand-edited"}]}))

    result = _init(tmp_path, "--force")

    assert result.exit_code == 0, result.stdout
    raw = json.loads(config_path.read_text())
    ids = [entry["id"] for entry in raw["ossify-skills-registry"]]
    assert ids == ["anthropic-skills"]
    assert "discovery-definitions" in raw
    assert raw["$schema"] == (
        "https://raw.githubusercontent.com/VZhuck/ossify-cogents/main/schema/v1.json"
    )
    verify = runner.invoke(app, ["--workspace", str(tmp_path), "config", "verify"])
    assert verify.exit_code == 0, verify.stdout


def test_init_force_succeeds_over_malformed_config(tmp_path: Path) -> None:
    config_path = tmp_path / "ossify-cogents.json"
    config_path.write_text("{ this is not valid json ]")

    result = _init(tmp_path, "--force")

    assert result.exit_code == 0, result.stdout
    raw = json.loads(config_path.read_text())
    assert raw["ossify-skills-registry"][0]["id"] == "anthropic-skills"
