"""Implements `ports_out.ConfigRepository` — section-keyed, round-trip-safe JSON I/O."""

import json
import tempfile
from pathlib import Path
from typing import TypeVar

from pydantic import TypeAdapter

from domain.ossify_config import ConfigSection, OssifyConfig

T = TypeVar("T")

CONFIG_FILENAME = "ossify-cogents.json"


class OssifyConfigAdapter:
    """Reads/writes ossify-cogents.json by section, preserving unrecognized sections."""

    def exists(self, root: Path) -> bool:
        return (root / CONFIG_FILENAME).is_file()

    def read_section(self, root: Path, section: ConfigSection, model: type[T]) -> T | None:
        config = self._load(root)
        raw_value = config.section_value(section)
        if raw_value is None:
            return None
        return TypeAdapter(model).validate_python(raw_value)

    def write_section(self, root: Path, section: ConfigSection, value: T, model: type[T]) -> None:
        config = self._load(root)
        raw_value = TypeAdapter(model).dump_python(value, mode="json", exclude_none=True)
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
                json.dump(config.to_raw(), tmp_file, indent=2)
                tmp_file.write("\n")
            Path(tmp_name).replace(path)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
