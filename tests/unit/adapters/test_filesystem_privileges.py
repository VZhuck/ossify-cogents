"""`adapters._filesystem`: the guarantee that installing never needs `sudo`."""

import os
from pathlib import Path

import pytest

from adapters import _filesystem
from domain.errors import TargetNotWritableError


def test_writable_translates_permission_error_into_domain_error(tmp_path: Path) -> None:
    with pytest.raises(TargetNotWritableError) as exc_info:
        with _filesystem.writable(tmp_path / "file.txt"):
            raise PermissionError(13, "Permission denied")

    assert "file.txt" in str(exc_info.value)


def test_writable_error_names_the_existing_ancestor_that_denied_the_write(
    tmp_path: Path,
) -> None:
    with pytest.raises(TargetNotWritableError) as exc_info:
        with _filesystem.writable(tmp_path / "missing" / "deeper" / "file.txt"):
            raise PermissionError(13, "Permission denied")

    # The leaf does not exist; the mode that actually denied us belongs to tmp_path.
    assert str(tmp_path) in str(exc_info.value)


def test_writable_error_steers_away_from_sudo(tmp_path: Path) -> None:
    with pytest.raises(TargetNotWritableError) as exc_info:
        with _filesystem.writable(tmp_path):
            raise PermissionError(13, "Permission denied")

    assert "Do not re-run ossify-cogents under sudo" in str(exc_info.value)


def test_writable_reraises_unrelated_os_errors_untouched(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        with _filesystem.writable(tmp_path):
            raise FileNotFoundError(2, "No such file or directory")


def test_mkdir_creates_missing_parents(tmp_path: Path) -> None:
    _filesystem.mkdir(tmp_path / "a" / "b" / "c")

    assert (tmp_path / "a" / "b" / "c").is_dir()


def test_mkdir_is_idempotent_on_an_existing_directory(tmp_path: Path) -> None:
    _filesystem.mkdir(tmp_path)

    assert tmp_path.is_dir()


def test_invoking_user_is_none_when_not_elevated() -> None:
    assert _filesystem.invoking_user() is None


def test_invoking_user_reads_sudo_environment_when_elevated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    monkeypatch.setenv("SUDO_UID", "501")
    monkeypatch.setenv("SUDO_GID", "20")

    assert _filesystem.invoking_user() == (501, 20)


def test_invoking_user_is_none_for_a_real_root_login(monkeypatch: pytest.MonkeyPatch) -> None:
    """Root without `SUDO_UID` is deliberately root; there is nobody to hand back to."""
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    monkeypatch.delenv("SUDO_UID", raising=False)
    monkeypatch.delenv("SUDO_GID", raising=False)

    assert _filesystem.invoking_user() is None


def test_deescalate_is_a_noop_when_not_elevated(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    target.write_text("content")
    before = target.stat().st_uid

    _filesystem.deescalate(target)

    assert target.stat().st_uid == before


def test_deescalate_tree_skips_the_walk_entirely_when_not_elevated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args: object, **kwargs: object) -> object:
        raise AssertionError("unelevated runs must not pay for a tree walk")

    monkeypatch.setattr(os, "walk", fail)

    _filesystem.deescalate_tree(tmp_path)


def test_deescalate_acts_on_the_link_not_its_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chowning through a link would silently re-own files in the source repository."""
    source = tmp_path / "source.txt"
    source.write_text("content")
    link = tmp_path / "link.txt"
    link.symlink_to(source)

    chowned: list[Path] = []
    monkeypatch.setattr(_filesystem, "invoking_user", lambda: (os.getuid(), os.getgid()))
    monkeypatch.setattr(os, "lchown", lambda path, uid, gid: chowned.append(Path(path)))

    _filesystem.deescalate(link)

    assert chowned == [link]


def test_deescalate_survives_a_failed_handback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A best-effort chown must not fail an install that otherwise succeeded."""

    def refuse(*args: object, **kwargs: object) -> None:
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(_filesystem, "invoking_user", lambda: (0, 0))
    monkeypatch.setattr(os, "lchown", refuse)

    _filesystem.deescalate(tmp_path / "anything")


def test_deescalate_tree_hands_back_every_directory_and_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "file.txt").write_text("content")

    chowned: list[Path] = []
    monkeypatch.setattr(_filesystem, "invoking_user", lambda: (os.getuid(), os.getgid()))
    monkeypatch.setattr(os, "lchown", lambda path, uid, gid: chowned.append(Path(path)))

    _filesystem.deescalate_tree(tmp_path)

    assert set(chowned) == {tmp_path, tmp_path / "nested", tmp_path / "nested" / "file.txt"}
