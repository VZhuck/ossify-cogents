"""Generates `schema/v1.json` from the known `ossify-cogents.json` section models.

`OssifyConfig` holds sections as opaque `dict[str, Any]` (so unmodeled sections
survive a read-modify-write round trip), so it can't produce a schema itself.
This script composes the *known* section models instead. Run via
`uv run python scripts/generate_schema.py`; the quality gate re-runs it and
diffs the output against the committed file to catch model/schema drift.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_ROOT))

from pydantic import TypeAdapter  # noqa: E402

from domain.discovery import DiscoveryDefinition  # noqa: E402
from domain.skill_registry import SkillSource  # noqa: E402

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "v1.json"

_SECTIONS: dict[str, Any] = {
    "ossify-skills-registry": list[SkillSource],
    "discovery-definitions": list[DiscoveryDefinition],
}


def generate_schema() -> dict[str, Any]:
    properties: dict[str, Any] = {}
    definitions: dict[str, Any] = {}

    for section, model in _SECTIONS.items():
        section_schema = TypeAdapter(model).json_schema(by_alias=True)
        definitions.update(section_schema.pop("$defs", {}))
        properties[section] = section_schema

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "ossify-cogents.json",
        "type": "object",
        "properties": properties,
        "additionalProperties": True,
        "$defs": definitions,
    }


def main() -> None:
    schema = generate_schema()
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(json.dumps(schema, indent=2) + "\n")


if __name__ == "__main__":
    main()
