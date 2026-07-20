"""Built-in discovery strategies: packaged code data, never written to config.

NOTE: the `ossify-` id prefix is reserved for built-in discovery strategies,
by convention/documentation only — there is no dedicated validator enforcing
it. A custom `discovery-definitions` entry that re-uses one of these ids
(e.g. `ossify-open-standard`) is rejected by the discovery resolver's
duplicate-id check, the same way two custom entries sharing an id are.
"""

from __future__ import annotations

from domain.discovery import DiscoveryDefinition, GlobRule, Mapping

OSSIFY_OPEN_STANDARD = DiscoveryDefinition(
    id="ossify-open-standard",
    mappings=Mapping(
        agents=[GlobRule(type="folder", path="agents")],
        skills=[GlobRule(type="folder", path="skills")],
        commands=[GlobRule(type="folder", path="commands")],
        rules=[GlobRule(type="folder", path="rules")],
    ),
)

BUILTIN_DISCOVERY_STRATEGIES: list[DiscoveryDefinition] = [OSSIFY_OPEN_STANDARD]
