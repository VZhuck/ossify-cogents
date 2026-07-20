"""Shared base for pydantic models that round-trip through ossify-cogents.json.

Every field on a config-serialized model is written/read as kebab-case on
disk, regardless of its (snake_case) Python name, via `alias_generator`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


def to_kebab(name: str) -> str:
    return name.replace("_", "-")


class ConfigModel(BaseModel):
    """Frozen base model with kebab-case on-disk field aliases."""

    model_config = ConfigDict(frozen=True, alias_generator=to_kebab, populate_by_name=True)
