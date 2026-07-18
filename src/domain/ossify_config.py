"""The whole `ossify-cogents.json` config file, represented section-by-section."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConfigSection(StrEnum):
    """Maps a use case to its on-disk top-level key in ossify-cogents.json."""

    SKILL_REGISTRY = "ossify-skills-registry"


class OssifyConfig(BaseModel):
    """Raw, section-keyed representation of the config file.

    Holds sections as plain JSON values (not parsed pydantic models) so that
    sections this codebase doesn't model yet survive a read-modify-write
    round trip untouched.
    """

    model_config = ConfigDict(frozen=True)

    sections: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> OssifyConfig:
        return cls(sections=raw)

    def to_raw(self) -> dict[str, Any]:
        return dict(self.sections)

    def section_value(self, section: ConfigSection) -> Any | None:
        return self.sections.get(section.value)

    def with_section_value(self, section: ConfigSection, value: Any) -> OssifyConfig:
        return OssifyConfig(sections={**self.sections, section.value: value})
