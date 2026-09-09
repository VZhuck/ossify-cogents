"""Implements `ports_out.VcsExcludePort` over git's per-developer `info/exclude`.

Absolute-target links are one developer's private arrangement, so they belong in
the never-committed exclude file rather than `.gitignore` — which would also
ignore those paths for a teammate who *copies* the same capabilities.

The tool-owned block is delimited by markers and rewritten wholesale on every
call, so it is idempotent, self-correcting when an entry stops linking, and needs
no recorded state. Everything outside the markers is preserved untouched.
"""

from __future__ import annotations

from pathlib import Path

from adapters import _filesystem

_START = "# --- ossify-cogents linked capabilities ---"
_END = "# --- end ossify-cogents linked capabilities ---"
_GITDIR_PREFIX = "gitdir:"


class GitExcludeAdapter:
    """Maintains the ossify block in `<git-dir>/info/exclude`."""

    def set_excluded(self, root: Path, paths: list[Path]) -> bool:
        git_dir = self._git_dir(root)
        if git_dir is None:
            return False

        exclude = git_dir / "info" / "exclude"
        existing = exclude.read_text() if exclude.is_file() else ""
        updated = self._rewrite(existing, paths)
        if updated == existing:
            return True

        _filesystem.mkdir(exclude.parent)
        with _filesystem.writable(exclude):
            exclude.write_text(updated)
        _filesystem.deescalate(exclude)
        return True

    def _rewrite(self, existing: str, paths: list[Path]) -> str:
        preserved = self._without_block(existing).rstrip("\n")
        if not paths:
            return f"{preserved}\n" if preserved else ""

        # Sorted and de-duplicated so repeated runs are byte-identical.
        entries = sorted({path.as_posix() for path in paths})
        block = "\n".join([_START, *entries, _END])
        return f"{preserved}\n\n{block}\n" if preserved else f"{block}\n"

    def _without_block(self, existing: str) -> str:
        kept: list[str] = []
        inside = False
        for line in existing.splitlines():
            if line.strip() == _START:
                inside = True
            elif line.strip() == _END:
                inside = False
            elif not inside:
                kept.append(line)
        return "\n".join(kept)

    def _git_dir(self, root: Path) -> Path | None:
        """The git directory whose `info/exclude` applies to `root`, or None if unversioned.

        `.git` is a directory in a normal clone and a `gitdir:` pointer file in a
        worktree or submodule. Worktrees additionally split state: `info/exclude`
        lives in the common directory, named by a `commondir` file.
        """
        candidate = root / ".git"
        if candidate.is_dir():
            return candidate
        if not candidate.is_file():
            return None

        pointer = candidate.read_text().strip()
        if not pointer.startswith(_GITDIR_PREFIX):
            return None
        target = Path(pointer[len(_GITDIR_PREFIX) :].strip())
        resolved = target if target.is_absolute() else (root / target).resolve()
        if not resolved.is_dir():
            return None
        return self._common_dir(resolved)

    def _common_dir(self, git_dir: Path) -> Path:
        commondir = git_dir / "commondir"
        if not commondir.is_file():
            return git_dir
        common = Path(commondir.read_text().strip())
        return common if common.is_absolute() else (git_dir / common).resolve()
