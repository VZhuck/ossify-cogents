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
from domain.errors import (
    SeveredLinkError,
    ShapeMismatchError,
    TargetLayoutUnavailableError,
    UnmatchedInstallSelectionError,
)
from domain.ossify_config import ConfigSection
from domain.skill_registry import SkillSource
from ports_out import SourcePort


class FakeSource:
    """A `SourcePort` over an in-memory `{relative-path: bytes}` tree rooted anywhere."""

    def __init__(self, files: dict[str, bytes], root: Path | None = None) -> None:
        self._files = {Path(path): data for path, data in files.items()}
        self.root = root or Path("/materialized")

    def materialize(self, entry: SkillSource) -> Path:
        return self.root

    def walk(self, root: Path, subpath: Path):
        for path in sorted(self._files):
            if path == subpath or subpath in path.parents:
                yield path

    def read_bytes(self, root: Path, path: Path) -> bytes:
        return self._files[path]


class FakeTarget:
    """An in-memory `TargetPort` capturing writes, removals, and links by path."""

    def __init__(self) -> None:
        self.files: dict[Path, bytes] = {}
        self.removed: list[Path] = []
        self.links: dict[Path, Path] = {}
        self.link_dirs: set[Path] = set()

    def exists(self, path: Path) -> bool:
        return (
            path in self.files
            or path in self.links
            or any(path in existing.parents for existing in self.files)
        )

    def is_symlink(self, path: Path) -> bool:
        return path in self.links

    def walk(self, path: Path):
        for existing in sorted(self.files):
            if path in existing.parents:
                yield existing.relative_to(path)

    def read(self, path: Path) -> bytes:
        return self.files[path]

    def children(self, path: Path):
        seen: dict[Path, None] = {}
        for existing in sorted(list(self.files) + list(self.links)):
            if path in existing.parents:
                seen[path / existing.relative_to(path).parts[0]] = None
        return list(seen)

    def link_target(self, path: Path) -> Path | None:
        return self.links.get(path)

    def link(self, path: Path, source: Path, *, is_directory: bool) -> None:
        self.remove(path)
        self.links[path] = source
        if is_directory:
            self.link_dirs.add(path)

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
        self.links.pop(path, None)
        self.link_dirs.discard(path)


class FakeVcsExclude:
    """Records the paths handed to `set_excluded`; `applied` fakes a non-repository root."""

    def __init__(self, *, applied: bool = True) -> None:
        self.applied = applied
        self.calls: list[list[Path]] = []

    def set_excluded(self, root: Path, paths: list[Path]) -> bool:
        self.calls.append(list(paths))
        return self.applied


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
    source: SourcePort,
    target: FakeTarget,
    config: FakeConfigRepository,
    vcs_exclude: FakeVcsExclude | None = None,
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
                        commands=[GlobRule(type="folder", path="commands")],
                        rules=[GlobRule(type="folder", path="rules")],
                    ),
                )
            ]
        ),
        discovery_execution=DiscoveryExecution(),
        install_resolver=InstallResolver(supported_platforms={"claude", "copilot", "codex"}),
        target_layout=TargetLayout(),
        target_factory=lambda root: target,
        vcs_exclude=vcs_exclude or FakeVcsExclude(),
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
        vcs_exclude=FakeVcsExclude(),
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
        vcs_exclude=FakeVcsExclude(),
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


def test_file_shaped_item_installs_without_a_doubled_extension(tmp_path: Path) -> None:
    # A `folder` rule over loose files used to yield ids carrying `.md`, which the
    # layout template then doubled into `md-to-word.md.md`.
    source = FakeSource({"commands/md-to-word.md": b"command"})
    target = FakeTarget()
    config = FakeConfigRepository(
        [_entry(Dependencies(target_platforms=["claude"], commands=["md-to-word"]))]
    )

    _use_case(source, target, config).install(tmp_path)

    assert target.files[Path(".claude/commands/md-to-word.md")] == b"command"
    assert Path(".claude/commands/md-to-word.md.md") not in target.files


def test_shape_mismatch_raises_and_writes_nothing(tmp_path: Path) -> None:
    source = FakeSource({"commands/deploy/steps.md": b"x"})
    target = FakeTarget()
    config = FakeConfigRepository(
        [_entry(Dependencies(target_platforms=["claude"], commands=["deploy"]))]
    )

    with pytest.raises(ShapeMismatchError):
        _use_case(source, target, config).install(tmp_path)

    assert target.files == {}


def test_file_shaped_item_takes_each_platform_rename(tmp_path: Path) -> None:
    source = FakeSource({"rules/architecture.md": b"rule"})
    target = FakeTarget()
    config = FakeConfigRepository(
        [_entry(Dependencies(target_platforms=["claude", "copilot"], rules=["architecture"]))]
    )

    _use_case(source, target, config).install(tmp_path)

    assert target.files[Path(".claude/rules/architecture.md")] == b"rule"
    assert target.files[Path(".github/instructions/architecture.instructions.md")] == b"rule"


def _link_entry(install: Dependencies, uri: str = "/materialized") -> SkillSource:
    return SkillSource(
        id="toolkit",
        name="Toolkit",
        description="",
        source_type="local",
        source={"uri": uri},
        discovery=["ossify-open-standard"],
        install=install,
    )


def test_link_mode_links_and_copy_mode_copies(tmp_path: Path) -> None:
    source = FakeSource({"skills/pdf/SKILL.md": b"skill", "rules/style.md": b"rule"})
    target = FakeTarget()
    config = FakeConfigRepository(
        [
            _link_entry(
                Dependencies(mode="link", target_platforms=["claude"], skills=["pdf"]),
            ),
            _entry(Dependencies(target_platforms=["claude"], rules=["style"])),
        ]
    )

    _use_case(source, target, config).install(tmp_path)

    assert target.links[Path(".claude/skills/pdf")] == Path("/materialized/skills/pdf")
    assert Path(".claude/skills/pdf") in target.link_dirs
    assert target.files[Path(".claude/rules/style.md")] == b"rule"
    assert Path(".claude/rules/style.md") not in target.links


def test_out_of_workspace_source_links_absolutely_and_is_excluded(tmp_path: Path) -> None:
    source = FakeSource({"rules/style.md": b"rule"})
    target = FakeTarget()
    exclude = FakeVcsExclude()
    config = FakeConfigRepository(
        [_link_entry(Dependencies(mode="link", target_platforms=["claude"], rules=["style"]))]
    )

    _use_case(source, target, config, exclude).install(tmp_path)

    assert target.links[Path(".claude/rules/style.md")].is_absolute()
    assert exclude.calls == [[Path(".claude/rules/style.md")]]


def test_in_workspace_source_links_relatively_and_is_not_excluded(tmp_path: Path) -> None:
    # A source inside the repo links relatively, so the link survives a clone —
    # which is exactly why it is left committable rather than excluded.
    source = FakeSource({"rules/style.md": b"rule"}, root=tmp_path / "tools/toolkit")
    target = FakeTarget()
    exclude = FakeVcsExclude()
    config = FakeConfigRepository(
        [_link_entry(Dependencies(mode="link", target_platforms=["claude"], rules=["style"]))]
    )

    _use_case(source, target, config, exclude).install(tmp_path)

    assert target.links[Path(".claude/rules/style.md")] == Path(
        "../../tools/toolkit/rules/style.md"
    )
    assert exclude.calls == []


def test_matching_file_destination_is_adopted(tmp_path: Path) -> None:
    source = FakeSource({"rules/style.md": b"rule"})
    target = FakeTarget()
    target.files[Path(".claude/rules/style.md")] = b"rule"  # a previous copy-mode install
    config = FakeConfigRepository(
        [_link_entry(Dependencies(mode="link", target_platforms=["claude"], rules=["style"]))]
    )

    _use_case(source, target, config).install(tmp_path)

    assert target.is_symlink(Path(".claude/rules/style.md"))


def test_matching_directory_destination_is_adopted(tmp_path: Path) -> None:
    source = FakeSource({"skills/pdf/SKILL.md": b"skill", "skills/pdf/ref.md": b"ref"})
    target = FakeTarget()
    target.files[Path(".claude/skills/pdf/SKILL.md")] = b"skill"
    target.files[Path(".claude/skills/pdf/ref.md")] = b"ref"
    config = FakeConfigRepository(
        [_link_entry(Dependencies(mode="link", target_platforms=["claude"], skills=["pdf"]))]
    )

    _use_case(source, target, config).install(tmp_path)

    assert target.is_symlink(Path(".claude/skills/pdf"))


def test_diverged_destination_is_severed_and_left_untouched(tmp_path: Path) -> None:
    source = FakeSource({"rules/style.md": b"rule"})
    target = FakeTarget()
    target.files[Path(".claude/rules/style.md")] = b"edited in the workspace"
    config = FakeConfigRepository(
        [_link_entry(Dependencies(mode="link", target_platforms=["claude"], rules=["style"]))]
    )

    with pytest.raises(SeveredLinkError):
        _use_case(source, target, config).install(tmp_path)

    assert target.files[Path(".claude/rules/style.md")] == b"edited in the workspace"
    assert not target.is_symlink(Path(".claude/rules/style.md"))


@pytest.mark.parametrize("action", ["init", "json_merge"])
def test_unlinkable_by_pattern_actions_copy_with_a_warning(action: str, tmp_path: Path) -> None:
    source = FakeSource({".vscode/settings.json": b'{"a": 1}'})
    target = FakeTarget()
    entry = _by_pattern_entry(action).model_copy(
        update={
            "install": Dependencies(
                mode="link", by_pattern=[{"category": "vs-code-settings", "action": action}]
            )
        }
    )
    config = FakeConfigRepository([entry], definitions=[_custom_by_pattern_definition()])

    report = _use_case(source, target, config).install(tmp_path)

    assert Path(".vscode/settings.json") in target.files
    assert Path(".vscode/settings.json") not in target.links
    assert any(action in warning for warning in report.entries[0].warnings)


def test_replace_by_pattern_links_under_link_mode(tmp_path: Path) -> None:
    source = FakeSource({".vscode/settings.json": b'{"a": 1}'})
    target = FakeTarget()
    entry = _by_pattern_entry("replace").model_copy(
        update={
            "install": Dependencies(
                mode="link", by_pattern=[{"category": "vs-code-settings", "action": "replace"}]
            )
        }
    )
    config = FakeConfigRepository([entry], definitions=[_custom_by_pattern_definition()])

    report = _use_case(source, target, config).install(tmp_path)

    assert Path(".vscode/settings.json") in target.links
    assert report.entries[0].warnings == []


def test_stale_links_are_pruned_but_copies_and_foreign_links_are_not(tmp_path: Path) -> None:
    source = FakeSource({"skills/pdf/SKILL.md": b"skill"})
    target = FakeTarget()
    target.links[Path(".claude/skills/docx")] = Path("/materialized/skills/docx")
    target.links[Path(".claude/skills/foreign")] = Path("/elsewhere/skills/foreign")
    target.files[Path(".claude/skills/copied/SKILL.md")] = b"copied"
    config = FakeConfigRepository(
        [_link_entry(Dependencies(mode="link", target_platforms=["claude"], skills=["pdf"]))]
    )

    report = _use_case(source, target, config).install(tmp_path)

    assert report.pruned == [Path(".claude/skills/docx")]
    assert Path(".claude/skills/foreign") in target.links
    assert Path(".claude/skills/copied/SKILL.md") in target.files
    assert Path(".claude/skills/pdf") in target.links


def test_one_item_links_into_every_target_platform(tmp_path: Path) -> None:
    source = FakeSource({"rules/style.md": b"rule"})
    target = FakeTarget()
    config = FakeConfigRepository(
        [
            _link_entry(
                Dependencies(mode="link", target_platforms=["claude", "copilot"], rules=["style"])
            )
        ]
    )

    _use_case(source, target, config).install(tmp_path)

    assert (
        target.links[Path(".claude/rules/style.md")]
        == target.links[Path(".github/instructions/style.instructions.md")]
    )


def test_installed_items_carry_mode_and_link_target(tmp_path: Path) -> None:
    source = FakeSource({"rules/style.md": b"rule"})
    target = FakeTarget()
    config = FakeConfigRepository(
        [_link_entry(Dependencies(mode="link", target_platforms=["claude"], rules=["style"]))]
    )

    report = _use_case(source, target, config).install(tmp_path)

    item = report.entries[0].installed[0]
    assert (item.platform, item.category, item.item_id) == ("claude", "rules", "style")
    assert item.mode == "link"
    assert item.link_target == Path("/materialized/rules/style.md")


def test_non_repository_workspace_still_links_and_warns(tmp_path: Path) -> None:
    source = FakeSource({"rules/style.md": b"rule"})
    target = FakeTarget()
    config = FakeConfigRepository(
        [_link_entry(Dependencies(mode="link", target_platforms=["claude"], rules=["style"]))]
    )

    report = _use_case(source, target, config, FakeVcsExclude(applied=False)).install(tmp_path)

    assert Path(".claude/rules/style.md") in target.links
    assert report.warnings
