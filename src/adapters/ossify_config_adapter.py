"""Implements `ports_out.ConfigRepository` — section-keyed, round-trip-safe JSON I/O."""

import json
import tempfile
from pathlib import Path
from typing import Any, TypeVar

from pydantic import TypeAdapter

from domain.ossify_config import ConfigSection, OssifyConfig

T = TypeVar("T")

CONFIG_FILENAME = "ossify-cogents.json"
_INDENT = "  "


def _render_json(value: Any, level: int = 0) -> str:
    """Pretty-print JSON like `indent=2`, but keep scalar-only objects on one line.

    A dict whose values are all scalars (no nested object/array) renders inline as
    `{ "k": v, ... }`; empty containers render as `{}` / `[]`; everything else
    expands one entry per line. Output is valid JSON — only whitespace differs.
    """
    pad = _INDENT * level
    child_pad = _INDENT * (level + 1)

    if isinstance(value, dict):
        if not value:
            return "{}"
        if all(not isinstance(item, (dict, list)) for item in value.values()):
            inline = ", ".join(f"{json.dumps(k)}: {json.dumps(v)}" for k, v in value.items())
            return f"{{ {inline} }}"
        entries = [
            f"{child_pad}{json.dumps(k)}: {_render_json(v, level + 1)}" for k, v in value.items()
        ]
        return "{\n" + ",\n".join(entries) + "\n" + pad + "}"

    if isinstance(value, list):
        if not value:
            return "[]"
        entries = [f"{child_pad}{_render_json(item, level + 1)}" for item in value]
        return "[\n" + ",\n".join(entries) + "\n" + pad + "]"

    return json.dumps(value)


class OssifyConfigAdapter:
    """Reads/writes ossify-cogents.json by section, preserving unrecognized sections."""

    def exists(self, root: Path) -> bool:
        return (root / CONFIG_FILENAME).is_file()

    def delete(self, root: Path) -> None:
        (root / CONFIG_FILENAME).unlink(missing_ok=True)

    def read_section(self, root: Path, section: ConfigSection, model: type[T]) -> T | None:
        config = self._load(root)
        raw_value = config.section_value(section)
        if raw_value is None:
            return None
        return TypeAdapter(model).validate_python(raw_value)

    def write_section(self, root: Path, section: ConfigSection, value: T, model: type[T]) -> None:
        config = self._load(root)
        raw_value = TypeAdapter(model).dump_python(
            value, mode="json", exclude_none=True, by_alias=True
        )
        updated = config.with_section_value(section, raw_value)
        self._save(root, updated)

    def _load(self, root: Path) -> OssifyConfig:
        path = root / CONFIG_FILENAME
        if not path.is_file():
            return OssifyConfig.from_raw({})
        return OssifyConfig.from_raw(json.loads(path.read_text()))

    def _save(self, root: Path, config: OssifyConfig) -> None:
        path = root / CONFIG_FILENAME
        fd, tmp_name = tempfile.mkstemp(dir=root, prefix=".ossify-cogents-", suffix=".json.tmp")
        try:
            with open(fd, "w") as tmp_file:
                tmp_file.write(_render_json(config.to_raw()))
                tmp_file.write("\n")
            Path(tmp_name).replace(path)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
