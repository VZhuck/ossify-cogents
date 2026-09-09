"""Filesystem privilege handling shared by the adapters that write to disk.

Both helpers here exist so that `sudo` is never the answer to a failed install.

`writable` turns a raw `PermissionError` into a `TargetNotWritableError` naming
the path, who owns it, and the command that fixes it. Without that translation
the CLI printed a traceback, which reads as "try again with more privileges" —
and a `sudo` install leaves a workspace of root-owned files the developer can no
longer edit, which is a worse problem than the one it appeared to solve.

`deescalate` handles the case where someone reached for `sudo` anyway: the real
user is still named in `SUDO_UID`/`SUDO_GID`, so every path we create is chowned
back to them and stays editable without `sudo` once the run finishes.
"""

from __future__ import annotations

import errno
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from domain.errors import TargetNotWritableError

_DENIED = frozenset({errno.EACCES, errno.EPERM, errno.EROFS})


def invoking_user() -> tuple[int, int] | None:
    """The uid/gid that invoked `sudo`, or None when not running elevated via sudo.

    `SUDO_UID` is the only trustworthy record of who is behind an elevated run;
    `os.getlogin()` reads the controlling terminal and is absent in CI and pipes.
    """
    if os.name == "nt" or not hasattr(os, "geteuid") or os.geteuid() != 0:
        return None
    uid, gid = os.environ.get("SUDO_UID"), os.environ.get("SUDO_GID")
    if uid is None or gid is None:
        return None
    try:
        return int(uid), int(gid)
    except ValueError:
        return None


def deescalate(path: Path) -> None:
    """Give `path` back to the user behind `sudo`. A no-op for an unelevated run.

    `lchown` acts on the link itself: a linked capability whose *target* got
    chowned would silently re-own files in the source repository.
    """
    owner = invoking_user()
    if owner is None:
        return
    try:
        os.lchown(path, *owner)
    except OSError:
        # Best-effort: a failed hand-back must not fail an otherwise good install.
        pass


def deescalate_tree(root: Path) -> None:
    """`deescalate` over `root` and everything beneath it. A no-op for an unelevated run.

    Used for the git cache, where an elevated run would otherwise leave a
    root-owned clone that every later unelevated `fetch` fails to write into.
    The walk is skipped entirely when nothing was elevated, so the common path
    pays one `geteuid()`.
    """
    if invoking_user() is None:
        return
    deescalate(root)
    for directory, _, files in os.walk(root, followlinks=False):
        for name in files:
            deescalate(Path(directory) / name)
        deescalate(Path(directory))


def mkdir(path: Path) -> None:
    """`mkdir -p` that hands every directory it creates back to the invoking user."""
    if path.is_dir():
        return
    created: list[Path] = []
    probe = path
    while not probe.exists() and probe != probe.parent:
        created.append(probe)
        probe = probe.parent
    with writable(path):
        path.mkdir(parents=True, exist_ok=True)
    for directory in created:
        deescalate(directory)


@contextmanager
def writable(path: Path) -> Iterator[None]:
    """Re-raise a permission failure under `path` as an actionable domain error."""
    try:
        yield
    except OSError as exc:
        if not isinstance(exc, PermissionError) and exc.errno not in _DENIED:
            raise
        raise TargetNotWritableError(_explain(path, exc)) from exc


def _explain(path: Path, exc: OSError) -> str:
    """Name the path, the ancestor that denied us, and the fix that is not `sudo`."""
    blocker = _blocker(path)
    owner, user = _owner(blocker), _current_user()
    remedy = (
        f"grant yourself write access: chmod u+rwx {blocker}"
        if owner == user
        else f"take ownership: sudo chown -R $(id -un):$(id -gn) {blocker}"
    )
    return (
        f"cannot write {path}: {exc.strerror or 'permission denied'}. "
        f"{blocker} is owned by {owner} and you are running as {user}. "
        "Do not re-run ossify-cogents under sudo — that installs root-owned "
        f"capabilities you will not be able to edit afterwards. Instead, {remedy}"
    )


def _blocker(path: Path) -> Path:
    """The nearest ancestor that actually exists — the one whose mode denied us."""
    probe = path if path.exists() else path.parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return probe


def _owner(path: Path) -> str:
    try:
        return path.owner()
    except (KeyError, OSError, NotImplementedError):
        return "another user"


def _current_user() -> str:
    if not hasattr(os, "geteuid"):
        return "the current account"
    try:
        import pwd

        return pwd.getpwuid(os.geteuid()).pw_name
    except (KeyError, ImportError):
        return f"uid {os.geteuid()}"
