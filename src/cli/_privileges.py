"""Tells the user when they have elevated a command that never needs elevation.

This is a render-time concern, not domain logic: `cli/` may not import `adapters/`,
so the environment check is repeated rather than shared. It is three lines, and
the alternative — a port and a use-case field carrying "you used sudo" through the
whole hexagon — would cost far more than it saves.
"""

from __future__ import annotations

import os

_MESSAGE = (
    "running under sudo, which ossify-cogents does not need. Installed capabilities "
    "are handed back to $SUDO_USER so you can still edit them, but a plain "
    "`ossify-cogents install` is the supported way to run this."
)


def sudo_warning() -> str | None:
    """A warning to print when the process was elevated via `sudo`, else None."""
    if os.name == "nt" or not hasattr(os, "geteuid") or os.geteuid() != 0:
        return None
    if not os.environ.get("SUDO_USER"):
        return None
    return _MESSAGE
