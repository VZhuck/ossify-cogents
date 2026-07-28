import subprocess
from pathlib import Path

import pytest

from adapters.sources import GitSourceAdapter
from adapters.sources.git_source_adapter import _normalize_uri, _slug
from domain.errors import SourceFetchError
from domain.skill_registry import SkillSource


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def bare_remote(tmp_path: Path) -> Path:
    """A local bare repo with one commit on `main` — stands in for a network remote."""
    work = tmp_path / "work"
    work.mkdir()
    _git(work, "init", "-b", "main")
    _git(work, "config", "user.email", "t@t.test")
    _git(work, "config", "user.name", "Test")
    (work / "skills").mkdir()
    (work / "skills" / "note.md").write_text("hello")
    _git(work, "add", ".")
    _git(work, "commit", "-m", "init")

    bare = tmp_path / "remote.git"
    _git(work, "clone", "--bare", str(work), str(bare))
    return bare


def _git_entry(uri: str, ref: str = "main") -> SkillSource:
    return SkillSource(
        id="pack",
        name="Pack",
        description="",
        source_type="git",
        source={"uri": uri, "ref": ref},
    )


def test_clone_checks_out_ref_and_reads_tree(
    bare_remote: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OSSIFY_CACHE_DIR", str(tmp_path / "cache"))
    adapter = GitSourceAdapter()

    root = adapter.materialize(_git_entry(str(bare_remote)))

    assert (root / "skills" / "note.md").read_text() == "hello"


def test_existing_cache_is_reused_not_recloned(
    bare_remote: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OSSIFY_CACHE_DIR", str(tmp_path / "cache"))
    adapter = GitSourceAdapter()
    first = adapter.materialize(_git_entry(str(bare_remote)))
    marker = first / "local-marker.txt"
    marker.write_text("kept")  # a re-clone would wipe the directory

    second = adapter.materialize(_git_entry(str(bare_remote)))

    assert second == first
    assert marker.exists()


def test_cache_dir_honors_env_override(
    bare_remote: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = tmp_path / "custom-cache"
    monkeypatch.setenv("OSSIFY_CACHE_DIR", str(cache))
    adapter = GitSourceAdapter()

    root = adapter.materialize(_git_entry(str(bare_remote)))

    assert cache in root.parents


def test_distinct_uris_get_distinct_cache_dirs(
    bare_remote: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = tmp_path / "other.git"
    _git(tmp_path, "clone", "--bare", str(bare_remote), str(other))
    monkeypatch.setenv("OSSIFY_CACHE_DIR", str(tmp_path / "cache"))
    adapter = GitSourceAdapter()

    first = adapter.materialize(_git_entry(str(bare_remote)))
    second = adapter.materialize(_git_entry(str(other)))

    assert first != second


def test_fetch_failure_raises_source_fetch_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OSSIFY_CACHE_DIR", str(tmp_path / "cache"))
    adapter = GitSourceAdapter()

    with pytest.raises(SourceFetchError):
        adapter.materialize(_git_entry(str(tmp_path / "does-not-exist.git")))


@pytest.mark.parametrize(
    ("uri", "expected"),
    [
        ("git@github.com:anthropics/skills.git", "github.com/anthropics/skills"),
        ("https://github.com/anthropics/skills", "github.com/anthropics/skills"),
        ("https://github.com/anthropics/skills.git/", "github.com/anthropics/skills"),
        ("https://user@GitHub.com:443/Anthropics/Skills.git?x=1#f", "github.com/Anthropics/Skills"),
    ],
)
def test_normalize_uri_collapses_spellings(uri: str, expected: str) -> None:
    assert _normalize_uri(uri) == expected


def test_ssh_and_https_spellings_share_a_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OSSIFY_CACHE_DIR", str(tmp_path / "cache"))
    adapter = GitSourceAdapter()

    ssh_name = adapter._cache_name("git@github.com:anthropics/skills.git")
    https_name = adapter._cache_name("https://github.com/anthropics/skills")

    assert ssh_name == https_name


def test_slug_is_last_segment_without_git_suffix() -> None:
    assert _slug("https://github.com/anthropics/skills.git") == "skills"
    assert _slug("git@github.com:anthropics/skills.git") == "skills"
