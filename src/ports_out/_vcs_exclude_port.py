from pathlib import Path
from typing import Protocol


class VcsExcludePort(Protocol):
    """Maintains the repository's local, non-committed ignore list.

    Machine-specific install destinations (absolute-target links) must not be
    committed, but they also must not land in a shared `.gitignore`, which would
    ignore the same paths for a teammate who legitimately *copies* them. This port
    owns the per-developer exclude file and the VCS layout knowledge that finding
    it needs, so the install use case stays free of both.
    """

    def set_excluded(self, root: Path, paths: list[Path]) -> bool:
        """Replace the tool-owned exclude block with `paths`, wholesale.

        The block is rewritten from current state on every call — so it is
        idempotent and self-corrects when an entry stops linking — and an empty
        `paths` removes it. Returns whether the exclusion was applied: `False`
        when `root` is not a repository, which is a skip, not a failure.
        """
        ...
