from pathlib import Path

import pytest

from adapters.persistence import GitExcludeAdapter

START = "# --- ossify-cogents linked capabilities ---"
END = "# --- end ossify-cogents linked capabilities ---"


@pytest.fixture
def adapter() -> GitExcludeAdapter:
    return GitExcludeAdapter()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / ".git/info").mkdir(parents=True)
    return tmp_path


def _exclude(repo: Path) -> str:
    return (repo / ".git/info/exclude").read_text()


def test_creates_the_block(adapter: GitExcludeAdapter, repo: Path) -> None:
    assert adapter.set_excluded(repo, [Path(".claude/skills/pdf")]) is True

    assert _exclude(repo) == f"{START}\n.claude/skills/pdf\n{END}\n"


def test_rewrites_the_block_wholesale(adapter: GitExcludeAdapter, repo: Path) -> None:
    adapter.set_excluded(repo, [Path(".claude/skills/pdf")])
    adapter.set_excluded(repo, [Path(".claude/skills/docx")])

    content = _exclude(repo)
    assert ".claude/skills/docx" in content
    assert ".claude/skills/pdf" not in content


def test_empty_paths_remove_the_block(adapter: GitExcludeAdapter, repo: Path) -> None:
    (repo / ".git/info/exclude").write_text("# hand-written\n*.log\n")
    adapter.set_excluded(repo, [Path(".claude/skills/pdf")])

    adapter.set_excluded(repo, [])

    assert _exclude(repo) == "# hand-written\n*.log\n"


def test_preserves_content_outside_the_markers(adapter: GitExcludeAdapter, repo: Path) -> None:
    (repo / ".git/info/exclude").write_text("# hand-written\n*.log\n")

    adapter.set_excluded(repo, [Path(".claude/rules/style.md")])

    content = _exclude(repo)
    assert content.startswith("# hand-written\n*.log\n")
    assert ".claude/rules/style.md" in content


def test_repeated_identical_calls_are_byte_stable(adapter: GitExcludeAdapter, repo: Path) -> None:
    paths = [Path(".claude/skills/pdf"), Path(".claude/rules/style.md")]

    adapter.set_excluded(repo, paths)
    first = _exclude(repo)
    adapter.set_excluded(repo, list(reversed(paths)))

    assert _exclude(repo) == first


def test_resolves_a_gitdir_pointer_file(adapter: GitExcludeAdapter, tmp_path: Path) -> None:
    # A worktree or submodule has `.git` as a file pointing at the real git dir.
    real_git_dir = tmp_path / "actual-git-dir"
    (real_git_dir / "info").mkdir(parents=True)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".git").write_text(f"gitdir: {real_git_dir}\n")

    assert adapter.set_excluded(workspace, [Path(".claude/skills/pdf")]) is True

    assert ".claude/skills/pdf" in (real_git_dir / "info/exclude").read_text()


def test_worktree_writes_to_the_common_directory(
    adapter: GitExcludeAdapter, tmp_path: Path
) -> None:
    # Git reads `info/exclude` from the common dir, not the per-worktree git dir.
    common = tmp_path / "main/.git"
    (common / "info").mkdir(parents=True)
    worktree_git_dir = common / "worktrees/feature"
    worktree_git_dir.mkdir(parents=True)
    (worktree_git_dir / "commondir").write_text("../..\n")
    workspace = tmp_path / "feature"
    workspace.mkdir()
    (workspace / ".git").write_text(f"gitdir: {worktree_git_dir}\n")

    assert adapter.set_excluded(workspace, [Path(".claude/skills/pdf")]) is True

    assert ".claude/skills/pdf" in (common / "info/exclude").read_text()


def test_non_repository_returns_false_without_raising(
    adapter: GitExcludeAdapter, tmp_path: Path
) -> None:
    assert adapter.set_excluded(tmp_path, [Path(".claude/skills/pdf")]) is False
