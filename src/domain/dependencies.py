"""Install-dependency entities: which discovered capabilities get installed, and how.

The `install` block on a registry entry (`Dependencies`) selects discovered
agents/skills/commands/rules via `fnmatch` name-globs and declares, per
`by-pattern` category, how foreign/pre-existing files are written (`action`).
It is embedded on `SkillSource` so selection names are scoped to that entry's
own discovered set. An empty `Dependencies` block is a valid stub that installs
nothing.
"""

from __future__ import annotations

from typing import Literal

from domain.config_model import ConfigModel


class ByPatternDependency(ConfigModel):
    """One by-pattern install entry: a discovery by-pattern `category` plus its write `action`."""

    category: str
    action: Literal["init", "replace", "json_merge"]


class Dependencies(ConfigModel):
    """The `install` block: selection of discovered items plus how they are written.

    `target-platforms` governs the fixed categories only (`by-pattern` mirrors to
    its discovery path). Each fixed-category list holds `fnmatch` name-globs over
    discovered ids; absent/empty selects nothing, `"*"` matches everything.

    `mode` is the sole control over copy-versus-link installation — there is no
    CLI flag, because linking is a per-entry decision. `link` requires a `local`
    source; the rule is enforced on `SkillSource`, which knows the source type.
    """

    mode: Literal["copy", "link"] = "copy"
    target_platforms: list[str] = []
    agents: list[str] = []
    skills: list[str] = []
    commands: list[str] = []
    rules: list[str] = []
    by_pattern: list[ByPatternDependency] = []
