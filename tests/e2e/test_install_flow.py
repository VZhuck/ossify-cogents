import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli import app

runner = CliRunner()


def _write_open_standard_source(root: Path) -> None:
    """A source repo laid out per the built-in `ossify-open-standard` discovery."""
    skill = root / "skills" / "code-review"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# code review")
    (skill / "helper.py").write_text("print('hi')")


def _config_with_entry(workspace: Path, entry: dict) -> None:
    (workspace / "ossify-cogents.json").write_text(json.dumps({"ossify-skills-registry": [entry]}))


def test_local_install_writes_skill_into_claude(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _write_open_standard_source(source)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _config_with_entry(
        workspace,
        {
            "id": "pack",
            "name": "Pack",
            "description": "",
            "source-type": "local",
            "source": {"uri": str(source)},
            "discovery": ["ossify-open-standard"],
            "install": {"target-platforms": ["claude"], "skills": ["code-review"]},
        },
    )

    result = runner.invoke(app, ["--workspace", str(workspace), "install"])

    assert result.exit_code == 0, result.stdout
    assert (workspace / ".claude/skills/code-review/SKILL.md").read_text() == "# code review"
    assert (workspace / ".claude/skills/code-review/helper.py").exists()


def test_reinstall_removes_stale_file(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _write_open_standard_source(source)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _config_with_entry(
        workspace,
        {
            "id": "pack",
            "name": "Pack",
            "description": "",
            "source-type": "local",
            "source": {"uri": str(source)},
            "discovery": ["ossify-open-standard"],
            "install": {"target-platforms": ["claude"], "skills": ["code-review"]},
        },
    )
    runner.invoke(app, ["--workspace", str(workspace), "install"])
    # a stale file that no longer exists in the source must not survive a re-install
    stale = workspace / ".claude/skills/code-review/stale.txt"
    stale.write_text("old")

    result = runner.invoke(app, ["--workspace", str(workspace), "install"])

    assert result.exit_code == 0, result.stdout
    assert not stale.exists()


def test_copilot_install_uses_copilot_layout(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "agents").mkdir(parents=True)
    (source / "agents" / "planner.md").write_text("planner")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    # A file-rule discovery yields the bare stem `planner`; the copilot layout
    # re-adds its `.agent.md` extension.
    config = {
        "ossify-skills-registry": [
            {
                "id": "pack",
                "name": "Pack",
                "description": "",
                "source-type": "local",
                "source": {"uri": str(source)},
                "discovery": ["file-agents"],
                "install": {"target-platforms": ["copilot"], "agents": ["planner"]},
            }
        ],
        "discovery-definitions": [
            {
                "id": "file-agents",
                "type": "custom",
                "mappings": {"agents": [{"type": "file", "path": "agents/*.md"}]},
            }
        ],
    }
    (workspace / "ossify-cogents.json").write_text(json.dumps(config))

    result = runner.invoke(app, ["--workspace", str(workspace), "install"])

    assert result.exit_code == 0, result.stdout
    assert (workspace / ".github/agents/planner.agent.md").read_text() == "planner"


def test_by_pattern_json_merge_into_existing_file(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / ".vscode").mkdir(parents=True)
    (source / ".vscode" / "settings.json").write_text(json.dumps({"editor.tabSize": 4}))
    workspace = tmp_path / "workspace"
    (workspace / ".vscode").mkdir(parents=True)
    (workspace / ".vscode" / "settings.json").write_text(json.dumps({"editor.wordWrap": "on"}))
    config = {
        "ossify-skills-registry": [
            {
                "id": "pack",
                "name": "Pack",
                "description": "",
                "source-type": "local",
                "source": {"uri": str(source)},
                "discovery": ["vscode-strat"],
                "install": {"by-pattern": [{"category": "vs-code", "action": "json_merge"}]},
            }
        ],
        "discovery-definitions": [
            {
                "id": "vscode-strat",
                "type": "custom",
                "mappings": {
                    "by-pattern": [
                        {"type": "file", "path": ".vscode/settings.json", "category": "vs-code"}
                    ]
                },
            }
        ],
    }
    (workspace / "ossify-cogents.json").write_text(json.dumps(config))

    result = runner.invoke(app, ["--workspace", str(workspace), "install"])

    assert result.exit_code == 0, result.stdout
    merged = json.loads((workspace / ".vscode/settings.json").read_text())
    assert merged == {"editor.tabSize": 4, "editor.wordWrap": "on"}


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def bare_source_repo(tmp_path: Path) -> Path:
    work = tmp_path / "work"
    work.mkdir()
    _git(work, "init", "-b", "main")
    _git(work, "config", "user.email", "t@t.test")
    _git(work, "config", "user.name", "Test")
    skill = work / "skills" / "code-review"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# from git")
    _git(work, "add", ".")
    _git(work, "commit", "-m", "init")
    bare = tmp_path / "remote.git"
    _git(work, "clone", "--bare", str(work), str(bare))
    return bare


def test_git_install_and_cache_reuse(
    bare_source_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OSSIFY_CACHE_DIR", str(tmp_path / "cache"))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _config_with_entry(
        workspace,
        {
            "id": "pack",
            "name": "Pack",
            "description": "",
            "source-type": "git",
            "source": {"uri": str(bare_source_repo), "ref": "main"},
            "discovery": ["ossify-open-standard"],
            "install": {"target-platforms": ["claude"], "skills": ["code-review"]},
        },
    )

    first = runner.invoke(app, ["--workspace", str(workspace), "install"])
    assert first.exit_code == 0, first.stdout
    assert (workspace / ".claude/skills/code-review/SKILL.md").read_text() == "# from git"

    # second run reuses the cache (no re-clone) and still installs
    second = runner.invoke(app, ["--workspace", str(workspace), "install"])
    assert second.exit_code == 0, second.stdout
    cache_repos = list((tmp_path / "cache" / "repos").iterdir())
    assert len(cache_repos) == 1


def _write_file_shaped_source(root: Path) -> None:
    """A source whose `commands`/`rules` folders hold loose files, not directories."""
    (root / "commands").mkdir(parents=True)
    (root / "commands/md-to-word.md").write_text("# md to word")
    (root / "rules").mkdir(parents=True)
    (root / "rules/architecture.md").write_text("# architecture")


def _linked_workspace(tmp_path: Path, mode: str = "link", *, git: bool = True) -> tuple[Path, Path]:
    source = tmp_path / "toolkit"
    source.mkdir()
    _write_open_standard_source(source)
    _write_file_shaped_source(source)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    if git:
        (workspace / ".git/info").mkdir(parents=True)
    _config_with_entry(
        workspace,
        {
            "id": "toolkit",
            "name": "Toolkit",
            "description": "",
            "source-type": "local",
            "source": {"uri": str(source)},
            "discovery": ["ossify-open-standard"],
            "install": {
                "mode": mode,
                "target-platforms": ["claude"],
                "skills": ["code-review"],
                "commands": ["md-to-word"],
                "rules": ["architecture"],
            },
        },
    )
    return source, workspace


def test_file_shaped_items_install_without_a_doubled_extension(tmp_path: Path) -> None:
    _, workspace = _linked_workspace(tmp_path, mode="copy", git=False)

    result = runner.invoke(app, ["--workspace", str(workspace), "install"])

    assert result.exit_code == 0, result.stdout
    assert (workspace / ".claude/commands/md-to-word.md").read_text() == "# md to word"
    assert (workspace / ".claude/rules/architecture.md").read_text() == "# architecture"
    assert not (workspace / ".claude/commands/md-to-word.md.md").exists()


def test_link_mode_links_writes_the_exclude_block_and_renders_links(tmp_path: Path) -> None:
    source, workspace = _linked_workspace(tmp_path)

    result = runner.invoke(app, ["--workspace", str(workspace), "install"])

    assert result.exit_code == 0, result.stdout
    skill = workspace / ".claude/skills/code-review"
    rule = workspace / ".claude/rules/architecture.md"
    assert skill.is_symlink()
    assert rule.is_symlink()
    # the link is the source file: an edit through the workspace reaches the toolkit
    rule.write_text("# edited through the workspace")
    assert (source / "rules/architecture.md").read_text() == "# edited through the workspace"
    exclude = (workspace / ".git/info/exclude").read_text()
    assert ".claude/skills/code-review" in exclude
    assert "=>" in result.stdout


def test_link_install_is_idempotent(tmp_path: Path) -> None:
    _, workspace = _linked_workspace(tmp_path)
    runner.invoke(app, ["--workspace", str(workspace), "install"])
    first_exclude = (workspace / ".git/info/exclude").read_bytes()

    result = runner.invoke(app, ["--workspace", str(workspace), "install"])

    assert result.exit_code == 0, result.stdout
    assert (workspace / ".claude/skills/code-review").is_symlink()
    assert (workspace / ".git/info/exclude").read_bytes() == first_exclude


def test_copy_install_then_link_install_adopts_every_destination(tmp_path: Path) -> None:
    source, workspace = _linked_workspace(tmp_path, mode="copy")
    assert runner.invoke(app, ["--workspace", str(workspace), "install"]).exit_code == 0
    assert not (workspace / ".claude/skills/code-review").is_symlink()
    config = workspace / "ossify-cogents.json"
    config.write_text(config.read_text().replace('"mode": "copy"', '"mode": "link"'))

    result = runner.invoke(app, ["--workspace", str(workspace), "install"])

    assert result.exit_code == 0, result.stdout
    assert (workspace / ".claude/skills/code-review").is_symlink()
    assert (workspace / ".claude/rules/architecture.md").is_symlink()


def test_in_workspace_source_links_relatively_and_survives_a_move(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "tools/toolkit").mkdir(parents=True)
    _write_file_shaped_source(workspace / "tools/toolkit")
    _config_with_entry(
        workspace,
        {
            "id": "toolkit",
            "name": "Toolkit",
            "description": "",
            "source-type": "local",
            "source": {"uri": str(workspace / "tools/toolkit")},
            "discovery": ["ossify-open-standard"],
            "install": {
                "mode": "link",
                "target-platforms": ["claude"],
                "rules": ["architecture"],
            },
        },
    )

    result = runner.invoke(app, ["--workspace", str(workspace), "install"])

    assert result.exit_code == 0, result.stdout
    rule = workspace / ".claude/rules/architecture.md"
    assert not Path(rule.readlink()).is_absolute()
    moved = tmp_path / "moved"
    workspace.rename(moved)
    assert (moved / ".claude/rules/architecture.md").read_text() == "# architecture"
