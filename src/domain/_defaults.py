"""Curated defaults written into a fresh `ossify-cogents.json` by `ossify init`.

Unlike `_builtins.py` (packaged code data that is *never* serialized), the value
here is *written to the config file* as a starting point the user then edits. It
is a fully-specified `SkillSource`, not inferred from a uri, so the default id /
name / description are stable and readable (see the change design for why
inference is not used here).
"""

from __future__ import annotations

from domain.dependencies import Dependencies
from domain.discovery import DiscoveryDefinition, GlobRule, Mapping
from domain.skill_registry import SkillSource, Source

DEFAULT_REGISTRY_ITEM = SkillSource(
    id="anthropic-skills",
    name="Anthropic Skills",
    description="Anthropic's library of agent skills.",
    source_type="git",
    source=Source(uri="https://github.com/anthropics/skills", ref="main"),
    discovery=["ossify-open-standard"],
    # An explicit empty skeleton: target-platforms is claude, every selection
    # list stays empty (installs nothing) so the written config teaches the
    # `install` block's shape without pulling anything in.
    install=Dependencies(target_platforms=["claude"]),
)
"""The single registry entry `ossify init` writes into a new config file."""

DEFAULT_DISCOVERY_DEFINITION = DiscoveryDefinition(
    # A distinct id (no `ossify-` prefix, no collision with a built-in) so the
    # written config passes `config verify`. Its mappings mirror the built-in
    # `ossify-open-standard` so the file documents what a custom strategy looks
    # like — built-ins are packaged code data and never appear in the config.
    id="example-standard",
    mappings=Mapping(
        agents=[GlobRule(type="folder", path="agents")],
        skills=[GlobRule(type="folder", path="skills")],
        commands=[GlobRule(type="folder", path="commands")],
        rules=[GlobRule(type="folder", path="rules")],
    ),
)
"""An example custom `discovery-definitions` entry `ossify init` writes as documentation."""
