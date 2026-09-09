import json
from pathlib import Path

import pytest

from adapters.targets import FilesystemTargetAdapter
from domain.errors import TargetNotWritableError, UnsupportedTargetActionError


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


def test_remove_unlinks_a_symlinked_directory_without_touching_its_target(
    adapter: FilesystemTargetAdapter, tmp_path: Path
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "SKILL.md").write_bytes(b"skill")
    link = tmp_path / "linked"
    link.symlink_to(source, target_is_directory=True)

    adapter.remove(Path("linked"))

    assert not link.exists()
    assert not link.is_symlink()
    assert (source / "SKILL.md").read_bytes() == b"skill"


def test_remove_still_deletes_a_real_directory_recursively(
    adapter: FilesystemTargetAdapter, tmp_path: Path
) -> None:
    (tmp_path / "tree/nested").mkdir(parents=True)
    (tmp_path / "tree/nested/file.txt").write_bytes(b"x")

    adapter.remove(Path("tree"))

    assert not (tmp_path / "tree").exists()


def test_remove_is_a_no_op_on_an_absent_path(adapter: FilesystemTargetAdapter) -> None:
    adapter.remove(Path("nothing/here"))


def test_link_creates_a_directory_symlink(adapter: FilesystemTargetAdapter, tmp_path: Path) -> None:
    source = tmp_path / "toolkit/skills/pdf"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_bytes(b"skill")

    adapter.link(Path(".claude/skills/pdf"), source, is_directory=True)

    destination = tmp_path / ".claude/skills/pdf"
    assert destination.is_symlink()
    assert (destination / "SKILL.md").read_bytes() == b"skill"


def test_link_creates_a_file_symlink_and_propagates_edits(
    adapter: FilesystemTargetAdapter, tmp_path: Path
) -> None:
    source = tmp_path / "toolkit/rules/style.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"original")

    adapter.link(Path(".claude/rules/style.md"), source, is_directory=False)

    destination = tmp_path / ".claude/rules/style.md"
    assert destination.is_symlink()
    destination.write_bytes(b"edited through the workspace")
    assert source.read_bytes() == b"edited through the workspace"


def test_relinking_an_existing_link_leaves_the_source_tree_intact(
    adapter: FilesystemTargetAdapter, tmp_path: Path
) -> None:
    # The one destructive failure mode worth pinning: `remove()` must unlink the
    # link rather than reach through it. A `rmtree(ignore_errors=True)` or a
    # hand-rolled recursion here would delete the toolkit's files.
    source = tmp_path / "toolkit/skills/pdf"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_bytes(b"skill")
    (source / "reference.md").write_bytes(b"reference")

    adapter.link(Path(".claude/skills/pdf"), source, is_directory=True)
    adapter.link(Path(".claude/skills/pdf"), source, is_directory=True)

    assert (tmp_path / ".claude/skills/pdf").is_symlink()
    assert sorted(path.name for path in source.iterdir()) == ["SKILL.md", "reference.md"]


def test_link_target_and_is_symlink_report_link_state(
    adapter: FilesystemTargetAdapter, tmp_path: Path
) -> None:
    source = tmp_path / "toolkit/rules/style.md"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"rule")
    adapter.override(Path("real.md"), b"real")

    adapter.link(Path("linked.md"), source, is_directory=False)

    assert adapter.is_symlink(Path("linked.md"))
    assert adapter.link_target(Path("linked.md")) == source.resolve()
    assert not adapter.is_symlink(Path("real.md"))
    assert adapter.link_target(Path("real.md")) is None


def test_write_into_an_unwritable_directory_reports_the_path_not_a_traceback(
    adapter: FilesystemTargetAdapter, tmp_path: Path
) -> None:
    blocked = tmp_path / "readonly"
    blocked.mkdir(mode=0o555)

    with pytest.raises(TargetNotWritableError) as exc_info:
        adapter.override(Path("readonly/nested/file.txt"), b"content")

    assert "readonly" in str(exc_info.value)
    assert "sudo" in str(exc_info.value)


def test_remove_from_an_unwritable_directory_reports_a_domain_error(
    adapter: FilesystemTargetAdapter, tmp_path: Path
) -> None:
    blocked = tmp_path / "readonly"
    blocked.mkdir()
    (blocked / "file.txt").write_bytes(b"content")
    blocked.chmod(0o555)

    try:
        with pytest.raises(TargetNotWritableError):
            adapter.remove(Path("readonly/file.txt"))
    finally:
        blocked.chmod(0o755)


def test_link_into_an_unwritable_directory_reports_a_domain_error(
    adapter: FilesystemTargetAdapter, tmp_path: Path
) -> None:
    source = tmp_path / "source.txt"
    source.write_bytes(b"content")
    blocked = tmp_path / "readonly"
    blocked.mkdir(mode=0o555)

    with pytest.raises(TargetNotWritableError):
        adapter.link(Path("readonly/nested/link.txt"), source, is_directory=False)
