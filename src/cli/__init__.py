"""CLI entrypoint.

Depends only on `ports_in/` (via `container.py`), never on `application/` directly.
"""

from cli._app import app

__all__ = ["app"]
