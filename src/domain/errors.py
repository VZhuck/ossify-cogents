"""Domain errors.

All errors raised across ossify-cogents subclass `OssifyError`, so callers
can catch at whatever granularity they need. `application/` is responsible
for translating low-level adapter exceptions into a specific `OssifyError`
subclass before they escape to `cli/`/`tui/`.
"""


class OssifyError(Exception):
    """Base class for all ossify-cogents domain errors."""


class VersionUnavailableError(OssifyError):
    """Raised when the installed package version cannot be determined."""


class ConfigNotFoundError(OssifyError):
    """Raised when no ossify-cogents.json exists at the resolved workspace root."""


class DuplicateSourceIdError(OssifyError):
    """Raised when a registry entry's `id` collides with an existing entry."""


class InvalidRegistryEntryError(OssifyError):
    """Raised when a registry entry violates a business rule (e.g. `ref` on a local source)."""
