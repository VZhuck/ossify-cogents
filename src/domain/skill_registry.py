"""Skill registry entities: a registered third-party skill/agent/rule source."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from domain.errors import InvalidRegistryEntryError


class Source(BaseModel):
    """Location of a skill source: a git remote (uri + ref) or a local path (uri only)."""

    model_config = ConfigDict(frozen=True)

    uri: str
    ref: str | None = None


class SkillSource(BaseModel):
    """A single registry entry: identity plus its source location.

    `ref` is only meaningful for a `git` source_type; the coupling between
    source_type and ref is enforced here (not via separate Git/Local classes)
    so it stays a single model — see design.md for the rationale.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    description: str
    source_type: Literal["git", "local"]
    source: Source

    @model_validator(mode="after")
    def _apply_source_type_rules(self) -> SkillSource:
        if self.source_type == "local" and self.source.ref is not None:
            raise InvalidRegistryEntryError(
                f"local source {self.id!r} must not set source.ref"
            )

        if self.source_type == "git" and self.source.ref is None:
            object.__setattr__(
                self, "source", self.source.model_copy(update={"ref": "main"})
            )

        return self
