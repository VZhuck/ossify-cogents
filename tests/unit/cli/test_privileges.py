"""`cli._privileges`: telling the user that `sudo` was never required."""

import os

import pytest

from cli._privileges import sudo_warning


def test_no_warning_for_an_ordinary_unelevated_run() -> None:
    assert sudo_warning() is None


def test_warns_when_the_command_was_elevated_with_sudo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    monkeypatch.setenv("SUDO_USER", "someone")

    warning = sudo_warning()

    assert warning is not None
    assert "does not need" in warning


def test_stays_quiet_for_a_real_root_login(monkeypatch: pytest.MonkeyPatch) -> None:
    """A container running as root is not a mistake to nag about."""
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    monkeypatch.delenv("SUDO_USER", raising=False)

    assert sudo_warning() is None
