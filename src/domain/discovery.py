"""Discovery-strategy entities: how to find agents/skills/commands/rules in a source.

Custom strategies are declared in the `discovery-definitions` config section
(`DiscoveryDefinition`); built-in strategies are packaged code data (see
`domain/_builtins.py`) and never appear in the config file. There is no
model-level reserved-`ossify-`-prefix validator here — see design.md's
"Reserved-prefix is enforced via duplicate-id detection" decision for why:
a custom entry re-using a built-in's id is rejected as an already-defined
discovery strategy by the resolver's duplicate-id check, not by this module.
"""

from __future__ import annotations

from typing import Literal

from domain.config_model import ConfigModel


class GlobRule(ConfigModel):
    """One glob rule: a file or folder pattern relative to a source's root."""

    type: Literal["file", "folder"]
    path: str


class ByPatternRule(GlobRule):
    """A glob rule for a free-form, project-defined capability category."""

    category: str


class Mapping(ConfigModel):
    """Per-category glob rules for a discovery strategy."""

    agents: list[GlobRule] = []
    skills: list[GlobRule] = []
    commands: list[GlobRule] = []
    rules: list[GlobRule] = []
    by_pattern: list[ByPatternRule] = []


class DiscoveryDefinition(ConfigModel):
    """A custom `discovery-definitions` entry: an id plus its category mappings."""

    id: str
    type: Literal["custom"] = "custom"
    mappings: Mapping
