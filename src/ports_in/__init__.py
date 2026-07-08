"""Inbound ports: interfaces that `cli/` and `tui/` call into, implemented by `application/`.

Uses `Protocol` rather than `ABC` so `application/` implementations don't need
to inherit from anything — structural typing keeps entrypoints decoupled from
a shared base class.
"""

from ports_in._version import VersionPort

__all__ = ["VersionPort"]
