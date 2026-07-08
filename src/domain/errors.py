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
