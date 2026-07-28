import json
from pathlib import Path

import pytest

from adapters.targets import FilesystemTargetAdapter
from domain.errors import UnsupportedTargetActionError


@pytest.fixture
def adapter(tmp_path: Path) -> FilesystemTargetAdapter:
    return FilesystemTargetAdapter(root=tmp_path)


def test_override_writes_and_creates_parent_directories(
    adapter: FilesystemTargetAdapter, tmp_path: Path
) -> None:
    adapter.override(Path("nested/dir/file.txt"), b"content")

    assert (tmp_path / "nested/dir/file.txt").read_bytes() == b"content"


def test_create_if_absent_writes_when_missing(
    adapter: FilesystemTargetAdapter, tmp_path: Path
) -> None:
    adapter.create_if_absent(Path("file.txt"), b"new")

    assert (tmp_path / "file.txt").read_bytes() == b"new"


def test_create_if_absent_leaves_existing_file_untouched(
    adapter: FilesystemTargetAdapter, tmp_path: Path
) -> None:
    (tmp_path / "file.txt").write_bytes(b"original")

    adapter.create_if_absent(Path("file.txt"), b"new")

    assert (tmp_path / "file.txt").read_bytes() == b"original"


def test_merge_writes_incoming_when_target_absent(
    adapter: FilesystemTargetAdapter, tmp_path: Path
) -> None:
    adapter.merge(Path("settings.json"), json.dumps({"a": 1}).encode())

    assert json.loads((tmp_path / "settings.json").read_text()) == {"a": 1}


def test_merge_deep_merges_nested_objects(adapter: FilesystemTargetAdapter, tmp_path: Path) -> None:
    (tmp_path / "settings.json").write_text(json.dumps({"editor": {"tabSize": 2}, "keep": True}))

    adapter.merge(Path("settings.json"), json.dumps({"editor": {"wordWrap": "on"}}).encode())

    assert json.loads((tmp_path / "settings.json").read_text()) == {
        "editor": {"tabSize": 2, "wordWrap": "on"},
        "keep": True,
    }


def test_merge_source_wins_on_scalar_conflict(
    adapter: FilesystemTargetAdapter, tmp_path: Path
) -> None:
    (tmp_path / "settings.json").write_text(json.dumps({"theme": "light"}))

    adapter.merge(Path("settings.json"), json.dumps({"theme": "dark"}).encode())

    assert json.loads((tmp_path / "settings.json").read_text()) == {"theme": "dark"}


def test_merge_source_wins_on_non_object_conflict(
    adapter: FilesystemTargetAdapter, tmp_path: Path
) -> None:
    # existing scalar under a key, incoming object for the same key: source replaces wholesale
    (tmp_path / "settings.json").write_text(json.dumps({"editor": 5}))

    adapter.merge(Path("settings.json"), json.dumps({"editor": {"tabSize": 4}}).encode())

    assert json.loads((tmp_path / "settings.json").read_text()) == {"editor": {"tabSize": 4}}


def test_merge_raises_unsupported_when_target_is_not_json(
    adapter: FilesystemTargetAdapter, tmp_path: Path
) -> None:
    (tmp_path / "settings.json").write_text("not json at all")

    with pytest.raises(UnsupportedTargetActionError):
        adapter.merge(Path("settings.json"), json.dumps({"a": 1}).encode())


def test_remove_deletes_a_directory_tree(adapter: FilesystemTargetAdapter, tmp_path: Path) -> None:
    (tmp_path / "skills/code-review").mkdir(parents=True)
    (tmp_path / "skills/code-review/SKILL.md").write_text("x")

    adapter.remove(Path("skills/code-review"))

    assert not (tmp_path / "skills/code-review").exists()


def test_remove_deletes_a_file(adapter: FilesystemTargetAdapter, tmp_path: Path) -> None:
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents/planner.md").write_text("x")

    adapter.remove(Path("agents/planner.md"))

    assert not (tmp_path / "agents/planner.md").exists()


def test_remove_is_a_noop_on_absent_path(adapter: FilesystemTargetAdapter) -> None:
    adapter.remove(Path("nope/missing"))  # must not raise
