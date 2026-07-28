import json
from pathlib import Path
from typing import Any

import pytest

from application import InstallCapabilities
from application.services import (
    DiscoveryExecution,
    DiscoveryResolver,
    InstallResolver,
    TargetLayout,
)
from domain.dependencies import Dependencies
from domain.discovery import ByPatternRule, DiscoveryDefinition, GlobRule, Mapping
from domain.errors import TargetLayoutUnavailableError, UnmatchedInstallSelectionError
from domain.ossify_config import ConfigSection
from domain.skill_registry import SkillSource
from ports_out import SourcePort


class FakeSource:
    """A `SourcePort` over an in-memory `{relative-path: bytes}` tree rooted anywhere."""

    def __init__(self, files: dict[str, bytes]) -> None:
        self._files = {Path(path): data for path, data in files.items()}
        self.root = Path("/materialized")

    def materialize(self, entry: SkillSource) -> Path:
        return self.root

    def walk(self, root: Path, subpath: Path):
        for path in sorted(self._files):
            if path == subpath or subpath in path.parents:
                yield path

    def read_bytes(self, root: Path, path: Path) -> bytes:
        return self._files[path]


class FakeTarget:
    """An in-memory `TargetPort` capturing writes and removals by path."""

    def __init__(self) -> None:
        self.files: dict[Path, bytes] = {}
        self.removed: list[Path] = []

    def exists(self, path: Path) -> bool:
        return path in self.files

    def create_if_absent(self, path: Path, data: bytes) -> None:
        self.files.setdefault(path, data)

    def override(self, path: Path, data: bytes) -> None:
        self.files[path] = data

    def merge(self, path: Path, data: bytes) -> None:
        base = json.loads(self.files[path]) if path in self.files else {}
        base.update(json.loads(data))
        self.files[path] = json.dumps(base).encode()

    def remove(self, path: Path) -> None:
        self.removed.append(path)
        for existing in [p for p in self.files if p == path or path in p.parents]:
            del self.files[existing]


class FakeConfigRepository:
    """Serves fixed skill-registry entries and (optional) custom discovery definitions."""

    def __init__(
        self,
        entries: list[SkillSource],
        definitions: list[DiscoveryDefinition] | None = None,
        *,
        exists: bool = True,
    ) -> None:
        self._entries = entries
        self._definitions = definitions or []
        self._exists = exists

    def exists(self, root: Path) -> bool:
        return self._exists

    def delete(self, root: Path) -> None:  # pragma: no cover - unused
        raise NotImplementedError

    def read_section(self, root: Path, section: ConfigSection, model: type[Any]) -> Any:
        if section is ConfigSection.SKILL_REGISTRY:
            return self._entries
        if section is ConfigSection.DISCOVERY_DEFINITIONS:
            return self._definitions
        return None

    def write_section(
        self, root: Path, section: ConfigSection, value: Any, model: type[Any]
    ) -> None:  # pragma: no cover
        raise NotImplementedError


def _entry(install: Dependencies, discovery: list[str] | None = None) -> SkillSource:
    return SkillSource(
        id="pack",
        name="Pack",
        description="",
        source_type="local",
        source={"uri": "/somewhere"},
        discovery=discovery or ["ossify-open-standard"],
        install=install,
    )


def _use_case(
    source: SourcePort, target: FakeTarget, config: FakeConfigRepository
) -> InstallCapabilities:
    return InstallCapabilities(
        config_repository=config,
        sources={"local": source, "git": source},
        discovery_resolver=DiscoveryResolver(
            builtins=[
                DiscoveryDefinition(
                    id="ossify-open-standard",
                    mappings=Mapping(
                        skills=[GlobRule(type="folder", path="skills")],
                        agents=[GlobRule(type="file", path="agents/*.md")],
                    ),
                )
            ]
        ),
        discovery_execution=DiscoveryExecution(),
        install_resolver=InstallResolver(supported_platforms={"claude", "copilot", "codex"}),
        target_layout=TargetLayout(),
        target_factory=lambda root: target,
    )


def test_fixed_category_skill_installs_into_claude(tmp_path: Path) -> None:
    source = FakeSource(
        {"skills/code-review/SKILL.md": b"skill", "skills/code-review/helper.py": b"code"}
    )
    target = FakeTarget()
    config = FakeConfigRepository(
        [_entry(Dependencies(target_platforms=["claude"], skills=["code-review"]))]
    )

    _use_case(source, target, config).install(tmp_path)

    assert target.files[Path(".claude/skills/code-review/SKILL.md")] == b"skill"
    assert target.files[Path(".claude/skills/code-review/helper.py")] == b"code"


def test_agent_installs_into_copilot_with_agent_extension(tmp_path: Path) -> None:
    source = FakeSource({"agents/planner.md": b"agent"})
    target = FakeTarget()
    config = FakeConfigRepository(
        [_entry(Dependencies(target_platforms=["copilot"], agents=["planner"]))]
    )

    _use_case(source, target, config).install(tmp_path)

    assert target.files[Path(".github/agents/planner.agent.md")] == b"agent"


def test_codex_agent_selection_raises_layout_unavailable(tmp_path: Path) -> None:
    source = FakeSource({"skills/s/SKILL.md": b"s", "agents/a.md": b"a"})
    target = FakeTarget()
    config = FakeConfigRepository(
        [_entry(Dependencies(target_platforms=["codex"], skills=["s"], agents=["a"]))]
    )

    with pytest.raises(TargetLayoutUnavailableError):
        _use_case(source, target, config).install(tmp_path)

    # the skill wrote before the agent raised
    assert target.files[Path(".agents/skills/s/SKILL.md")] == b"s"


def test_replace_removes_stale_destination_first(tmp_path: Path) -> None:
    source = FakeSource({"skills/code-review/SKILL.md": b"new"})
    target = FakeTarget()
    config = FakeConfigRepository(
        [_entry(Dependencies(target_platforms=["claude"], skills=["code-review"]))]
    )

    _use_case(source, target, config).install(tmp_path)

    assert Path(".claude/skills/code-review") in target.removed


def test_unmatched_literal_raises(tmp_path: Path) -> None:
    source = FakeSource({"skills/code-review/SKILL.md": b"x"})
    target = FakeTarget()
    config = FakeConfigRepository(
        [_entry(Dependencies(target_platforms=["claude"], skills=["missing"]))]
    )

    with pytest.raises(UnmatchedInstallSelectionError):
        _use_case(source, target, config).install(tmp_path)


def test_empty_selection_installs_nothing(tmp_path: Path) -> None:
    source = FakeSource({"skills/code-review/SKILL.md": b"x"})
    target = FakeTarget()
    config = FakeConfigRepository([_entry(Dependencies(target_platforms=["claude"]))])

    report = _use_case(source, target, config).install(tmp_path)

    assert target.files == {}
    assert report.entries[0].installed == []


def _by_pattern_entry(action: str) -> SkillSource:
    return SkillSource(
        id="pack",
        name="Pack",
        description="",
        source_type="local",
        source={"uri": "/somewhere"},
        discovery=["custom"],
        install=Dependencies(by_pattern=[{"category": "vs-code-settings", "action": action}]),
    )


def _custom_by_pattern_definition() -> DiscoveryDefinition:
    return DiscoveryDefinition(
        id="custom",
        mappings=Mapping(
            by_pattern=[
                ByPatternRule(
                    type="file", path=".vscode/settings.json", category="vs-code-settings"
                )
            ]
        ),
    )


@pytest.mark.parametrize("action", ["init", "replace", "json_merge"])
def test_by_pattern_writes_to_discovery_path(action: str, tmp_path: Path) -> None:
    source = FakeSource({".vscode/settings.json": b'{"a": 1}'})
    target = FakeTarget()
    config = FakeConfigRepository(
        [_by_pattern_entry(action)], definitions=[_custom_by_pattern_definition()]
    )
    use_case = InstallCapabilities(
        config_repository=config,
        sources={"local": source, "git": source},
        discovery_resolver=DiscoveryResolver(builtins=[]),
        discovery_execution=DiscoveryExecution(),
        install_resolver=InstallResolver(supported_platforms={"claude"}),
        target_layout=TargetLayout(),
        target_factory=lambda root: target,
    )

    use_case.install(tmp_path)

    assert Path(".vscode/settings.json") in target.files


def test_by_pattern_init_does_not_clobber_existing(tmp_path: Path) -> None:
    source = FakeSource({".vscode/settings.json": b'{"a": 1}'})
    target = FakeTarget()
    target.files[Path(".vscode/settings.json")] = b'{"existing": true}'
    config = FakeConfigRepository(
        [_by_pattern_entry("init")], definitions=[_custom_by_pattern_definition()]
    )
    use_case = InstallCapabilities(
        config_repository=config,
        sources={"local": source, "git": source},
        discovery_resolver=DiscoveryResolver(builtins=[]),
        discovery_execution=DiscoveryExecution(),
        install_resolver=InstallResolver(supported_platforms={"claude"}),
        target_layout=TargetLayout(),
        target_factory=lambda root: target,
    )

    use_case.install(tmp_path)

    assert target.files[Path(".vscode/settings.json")] == b'{"existing": true}'


def test_missing_config_raises(tmp_path: Path) -> None:
    source = FakeSource({})
    target = FakeTarget()
    config = FakeConfigRepository([], exists=False)

    from domain.errors import ConfigNotFoundError

    with pytest.raises(ConfigNotFoundError):
        _use_case(source, target, config).install(tmp_path)
