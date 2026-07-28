from collections.abc import Iterable
from pathlib import Path

import pytest

from application.services import DiscoveryExecution
from domain.discovery import ByPatternRule, DiscoveryDefinition, GlobRule, Mapping


class FakeSource:
    """A read-side-only `SourcePort` over a real tmp tree (materialize is unused here)."""

    def materialize(self, entry: object) -> Path:  # pragma: no cover - unused
        raise NotImplementedError

    def walk(self, root: Path, subpath: Path) -> Iterable[Path]:
        base = root / subpath
        if not base.exists():
            return
        if base.is_file():
            yield base.relative_to(root)
            return
        for path in sorted(base.rglob("*")):
            if path.is_file():
                yield path.relative_to(root)

    def read_bytes(self, root: Path, path: Path) -> bytes:
        return (root / path).read_bytes()


@pytest.fixture
def source() -> FakeSource:
    return FakeSource()


def _definition(mappings: Mapping) -> DiscoveryDefinition:
    return DiscoveryDefinition(id="strat", mappings=mappings)


def test_folder_rule_enumerates_children_as_ids(source: FakeSource, tmp_path: Path) -> None:
    (tmp_path / "skills/code-review").mkdir(parents=True)
    (tmp_path / "skills/code-review/SKILL.md").write_text("x")
    (tmp_path / "skills/planner").mkdir()
    (tmp_path / "skills/planner/SKILL.md").write_text("y")
    definition = _definition(Mapping(skills=[GlobRule(type="folder", path="skills")]))

    result = source_enumerate(source, tmp_path, definition)

    assert result.fixed["skills"] == {
        "code-review": Path("skills/code-review"),
        "planner": Path("skills/planner"),
    }


def test_file_rule_enumerates_by_stem(source: FakeSource, tmp_path: Path) -> None:
    (tmp_path / "rules").mkdir()
    (tmp_path / "rules/style.md").write_text("a")
    (tmp_path / "rules/naming.md").write_text("b")
    definition = _definition(Mapping(rules=[GlobRule(type="file", path="rules/*.md")]))

    result = source_enumerate(source, tmp_path, definition)

    assert result.fixed["rules"] == {
        "style": Path("rules/style.md"),
        "naming": Path("rules/naming.md"),
    }


def test_missing_path_yields_no_ids(source: FakeSource, tmp_path: Path) -> None:
    definition = _definition(Mapping(agents=[GlobRule(type="folder", path="agents")]))

    result = source_enumerate(source, tmp_path, definition)

    assert result.fixed.get("agents", {}) == {}


def test_by_pattern_category_is_recorded(source: FakeSource, tmp_path: Path) -> None:
    (tmp_path / ".vscode").mkdir()
    (tmp_path / ".vscode/settings.json").write_text("{}")
    definition = _definition(
        Mapping(
            by_pattern=[
                ByPatternRule(
                    type="file", path=".vscode/settings.json", category="vs-code-settings"
                )
            ]
        )
    )

    result = source_enumerate(source, tmp_path, definition)

    assert result.by_pattern["vs-code-settings"] == {"settings": Path(".vscode/settings.json")}


def source_enumerate(source: FakeSource, root: Path, definition: DiscoveryDefinition):
    return DiscoveryExecution().enumerate(source, root, [definition])
