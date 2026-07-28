from pathlib import Path

import pytest

from application.services import Destination, TargetLayout
from domain.errors import TargetLayoutUnavailableError


@pytest.fixture
def layout() -> TargetLayout:
    return TargetLayout()


@pytest.mark.parametrize(
    ("platform", "category", "item_id", "expected"),
    [
        ("claude", "skills", "code-review", Destination(Path(".claude/skills/code-review"), "dir")),
        ("claude", "agents", "planner", Destination(Path(".claude/agents/planner.md"), "file")),
        (
            "copilot",
            "agents",
            "planner",
            Destination(Path(".github/agents/planner.agent.md"), "file"),
        ),
        (
            "copilot",
            "rules",
            "style",
            Destination(Path(".github/instructions/style.instructions.md"), "file"),
        ),
        ("codex", "skills", "code-review", Destination(Path(".agents/skills/code-review"), "dir")),
    ],
)
def test_resolve_returns_expected_destination(
    layout: TargetLayout,
    platform: str,
    category: str,
    item_id: str,
    expected: Destination,
) -> None:
    assert layout.resolve(platform, category, item_id) == [expected]


def test_populated_platform_but_absent_category_raises(layout: TargetLayout) -> None:
    with pytest.raises(TargetLayoutUnavailableError):
        layout.resolve("codex", "agents", "planner")


def test_unknown_platform_raises(layout: TargetLayout) -> None:
    with pytest.raises(TargetLayoutUnavailableError):
        layout.resolve("eclipse", "skills", "code-review")
