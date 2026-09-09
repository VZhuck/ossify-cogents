"""Application-owned target-layout registry: canonical item -> per-platform path.

Layout knowledge lives here (not in the target adapter, which stays a dumb
per-path writer). The registry is a constant keyed `(platform, category)`, and
the layout for an entry is selected dynamically by the platform key drawn from
`install.target-platforms` — so the same const can later be config-overridden
without touching the install pipeline. Each entry maps to a *list* of
destinations (most single-element) so a future platform whose one category fans
out to several dirs is a data-only addition.

Installs are verbatim content copy: a destination relocates and renames an item
(directory vs file, per-platform extension) but never transforms its bytes. A
`(platform, category)` with no registry entry is an error, not a silent skip.

A destination's `shape` is what this layout *expects* to find. Discovery owns the
*observed* shape of an item; the install pipeline compares the two and refuses a
destination whose expectation the source contradicts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from domain.errors import TargetLayoutUnavailableError

Shape = Literal["dir", "file"]


@dataclass(frozen=True)
class Destination:
    """A resolved install destination: a repo-relative path plus its expected shape.

    `shape` says what this layout expects an item to be, not what it is — the
    observed shape comes from discovery and is checked against this.
    """

    path: Path
    shape: Shape


# `(platform, category) -> [(destination template, shape)]`. `{id}` is filled with
# the discovered id; file-shaped templates re-add the per-platform extension the
# bare discovery stem lacks.
DEFAULT_TARGET_LAYOUTS: dict[str, dict[str, list[tuple[str, Shape]]]] = {
    "claude": {
        "skills": [(".claude/skills/{id}", "dir")],
        "agents": [(".claude/agents/{id}.md", "file")],
        "commands": [(".claude/commands/{id}.md", "file")],
        "rules": [(".claude/rules/{id}.md", "file")],
    },
    "copilot": {
        "skills": [(".github/skills/{id}", "dir")],
        "agents": [(".github/agents/{id}.agent.md", "file")],
        "rules": [(".github/instructions/{id}.instructions.md", "file")],
    },
    "codex": {
        "skills": [(".agents/skills/{id}", "dir")],
    },
}


class TargetLayout:
    """Resolves `(platform, category, id)` to the destination(s) an item installs to."""

    def __init__(
        self, layouts: dict[str, dict[str, list[tuple[str, Shape]]]] | None = None
    ) -> None:
        self._layouts = layouts if layouts is not None else DEFAULT_TARGET_LAYOUTS

    def owned_roots(self) -> list[Path]:
        """The directories the configured layouts install into, deduplicated.

        Stale-link pruning scans these: a destination this tool could have written
        is the only place it may unlink something it no longer claims.
        """
        roots: dict[Path, None] = {}
        for by_category in self._layouts.values():
            for templates in by_category.values():
                for template, _ in templates:
                    roots[Path(template).parent] = None
        return list(roots)

    def resolve(self, platform: str, category: str, item_id: str) -> list[Destination]:
        by_category = self._layouts.get(platform)
        if by_category is None:
            raise TargetLayoutUnavailableError(f"no target layout for platform {platform!r}")
        templates = by_category.get(category)
        if templates is None:
            raise TargetLayoutUnavailableError(
                f"no target layout for category {category!r} on platform {platform!r}"
            )
        return [
            Destination(path=Path(template.format(id=item_id)), shape=shape)
            for template, shape in templates
        ]
