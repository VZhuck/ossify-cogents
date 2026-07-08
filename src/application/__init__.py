"""Use cases: implement `ports_in/`, depend on `ports_out/`.

Never imported directly by `adapters/`, `cli/`, or `tui/` — only `container.py`
constructs these and hands wired instances to entrypoints.
"""

from application._get_version import GetVersion

__all__ = ["GetVersion"]
