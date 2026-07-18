import json
from pathlib import Path

from typer.testing import CliRunner

from cli import app

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
    assert entry["source_type"] == "local"
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
