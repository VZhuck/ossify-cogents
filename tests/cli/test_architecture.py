import ast
from pathlib import Path

import cli

CLI_SOURCE_FILES = list(Path(cli.__file__).parent.glob("*.py"))


def _imported_top_level_modules(source_file: Path) -> set[str]:
    tree = ast.parse(source_file.read_text())
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def test_cli_does_not_import_application_directly() -> None:
    for source_file in CLI_SOURCE_FILES:
        imported = _imported_top_level_modules(source_file)
        assert "application" not in imported, (
            f"{source_file} imports `application` directly; it must go through "
            "`ports_in` + `container` instead"
        )
