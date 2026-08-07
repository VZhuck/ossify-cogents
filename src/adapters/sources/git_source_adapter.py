"""Implements `ports_out.SourcePort` for `git` sources — clone/fetch into an OS cache.

The `git` binary is shelled out to (no pure-Python git); OS-path resolution uses
`platformdirs`. Both dependencies live here, at the edge of the hexagon. Cache
identity derives from a deterministic uri normalization (see `_normalize_uri`),
so two spellings of the same repo share one cache directory; the `ref` is checked
out into that shared directory and is deliberately not part of the identity.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from collections.abc import Iterable
from pathlib import Path

import platformdirs

from adapters.sources import _working_tree
from domain.errors import SourceFetchError
from domain.skill_registry import SkillSource

_CACHE_ENV_VAR = "OSSIFY_CACHE_DIR"
_APP_NAME = "ossify-cogents"
_UNSAFE_SLUG_CHARS = re.compile(r"[^A-Za-z0-9._-]")


class GitSourceAdapter:
    """Materializes a `git` source into a durable per-source cache at the entry's ref."""

    def materialize(self, entry: SkillSource) -> Path:
        uri = entry.source.uri
        ref = entry.source.ref or "main"
        repo_dir = self._cache_root() / "repos" / self._cache_name(uri)

        if (repo_dir / ".git").is_dir():
            self._git(["fetch", "--all", "--tags", "--prune"], cwd=repo_dir)
            if self._remote_branch_exists(repo_dir, ref):
                self._git(["checkout", "-B", ref, f"origin/{ref}"], cwd=repo_dir)
            else:
                self._git(["checkout", ref], cwd=repo_dir)
        else:
            repo_dir.parent.mkdir(parents=True, exist_ok=True)
            self._git(["clone", uri, str(repo_dir)], cwd=None)
            self._git(["checkout", ref], cwd=repo_dir)
        return repo_dir

    def _remote_branch_exists(self, repo_dir: Path, ref: str) -> bool:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{ref}"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0

    def walk(self, root: Path, subpath: Path) -> Iterable[Path]:
        return _working_tree.walk(root, subpath)

    def read_bytes(self, root: Path, path: Path) -> bytes:
        return _working_tree.read_bytes(root, path)

    def _cache_root(self) -> Path:
        override = os.environ.get(_CACHE_ENV_VAR)
        if override:
            return Path(override)
        return Path(platformdirs.user_cache_dir(_APP_NAME))

    def _cache_name(self, uri: str) -> str:
        digest = hashlib.sha256(_normalize_uri(uri).encode()).hexdigest()[:8]
        return f"{_slug(uri)}-{digest}"

    def _git(self, args: list[str], *, cwd: Path | None) -> None:
        try:
            subprocess.run(
                ["git", *args],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError as exc:
            raise SourceFetchError("git binary not found on PATH") from exc
        except subprocess.CalledProcessError as exc:
            raise SourceFetchError(
                f"git {' '.join(args)} failed: {exc.stderr.strip() or exc}"
            ) from exc


def _slug(uri: str) -> str:
    """The uri's last path segment, `.git` stripped, sanitized to filesystem-safe chars."""
    tail = uri.strip().rstrip("/").rsplit("/", 1)[-1]
    tail = tail.rsplit(":", 1)[-1]  # scp form host:name -> name
    if tail.endswith(".git"):
        tail = tail[: -len(".git")]
    tail = _UNSAFE_SLUG_CHARS.sub("-", tail)
    return tail or "source"


def _normalize_uri(uri: str) -> str:
    """Collapse scp/ssh/https spellings of one git repo to a canonical `host/path`.

    Trims whitespace, drops `?query`/`#fragment`, rewrites scp `[user@]host:path`,
    drops scheme and userinfo, lowercases the host only, drops a default port,
    strips a trailing `.git`, and strips trailing slashes.
    """
    uri = uri.strip()
    uri = uri.split("#", 1)[0].split("?", 1)[0]

    if "://" not in uri and ":" in uri and not uri.startswith("/"):
        userinfo_host, _, path = uri.partition(":")
        host = userinfo_host.rpartition("@")[2]
        rest = f"{host}/{path}" if path else host
    else:
        remainder = uri.partition("://")[2] or uri
        head, slash, path = remainder.partition("/")
        head = head.rpartition("@")[2]  # drop userinfo
        rest = f"{head}{slash}{path}"

    host_port, slash, path = rest.partition("/")
    host = host_port.partition(":")[0].lower()
    normalized = f"{host}{slash}{path}".rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[: -len(".git")]
    return normalized
