from pathlib import Path
from unittest.mock import patch

from adapters.workspace_adapter import WorkspaceAdapter


def test_resolve_returns_explicit_path_without_searching(tmp_path: Path) -> None:
    adapter = WorkspaceAdapter()
    explicit = tmp_path / "some-repo"

    result = adapter.resolve(explicit)

    assert result == explicit


def test_resolve_walks_up_to_nearest_git_directory(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / ".git").mkdir(parents=True)
    nested = repo_root / "nested" / "deeper"
    nested.mkdir(parents=True)
    adapter = WorkspaceAdapter()

    with patch("adapters.workspace_adapter.Path.cwd", return_value=nested):
        result = adapter.resolve(None)

    assert result == repo_root


def test_resolve_walks_up_to_nearest_config_file(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    (repo_root / "ossify-cogents.json").write_text("{}")
    nested = repo_root / "nested"
    nested.mkdir()
    adapter = WorkspaceAdapter()

    with patch("adapters.workspace_adapter.Path.cwd", return_value=nested):
        result = adapter.resolve(None)

    assert result == repo_root


def test_resolve_falls_back_to_cwd_when_no_markers_found(tmp_path: Path) -> None:
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    adapter = WorkspaceAdapter()

    with patch("adapters.workspace_adapter.Path.cwd", return_value=isolated):
        result = adapter.resolve(None)

    assert result == isolated
