from pathlib import Path

import pytest

from adapters.sources import LocalSourceAdapter
from domain.errors import SourceFetchError
from domain.skill_registry import SkillSource


def _local_entry(uri: str) -> SkillSource:
    return SkillSource(
        id="local-pack",
        name="Local Pack",
        description="",
        source_type="local",
        source={"uri": uri},
    )


def test_materialize_returns_uri_path_without_copying(tmp_path: Path) -> None:
    adapter = LocalSourceAdapter()

    root = adapter.materialize(_local_entry(str(tmp_path)))

    assert root == tmp_path


def test_walk_yields_files_relative_to_root(tmp_path: Path) -> None:
    (tmp_path / "skills/code-review").mkdir(parents=True)
    (tmp_path / "skills/code-review/SKILL.md").write_text("body")
    adapter = LocalSourceAdapter()

    files = list(adapter.walk(tmp_path, Path("skills")))

    assert files == [Path("skills/code-review/SKILL.md")]


def test_walk_missing_path_yields_nothing(tmp_path: Path) -> None:
    adapter = LocalSourceAdapter()

    assert list(adapter.walk(tmp_path, Path("absent"))) == []


def test_read_bytes_reads_from_root(tmp_path: Path) -> None:
    (tmp_path / "file.txt").write_bytes(b"data")
    adapter = LocalSourceAdapter()

    assert adapter.read_bytes(tmp_path, Path("file.txt")) == b"data"


def test_materialize_missing_path_raises(tmp_path: Path) -> None:
    # A missing local source used to walk to nothing, so the entry installed zero
    # items and exited zero — a silent no-op for a broken config.
    entry = SkillSource(
        id="toolkit",
        name="Toolkit",
        description="",
        source_type="local",
        source={"uri": str(tmp_path / "absent")},
    )

    with pytest.raises(SourceFetchError) as excinfo:
        LocalSourceAdapter().materialize(entry)

    assert "toolkit" in str(excinfo.value)
