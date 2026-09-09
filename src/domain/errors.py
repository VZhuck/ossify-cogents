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


class ConfigAlreadyExistsError(OssifyError):
    """Raised when `ossify init` finds an ossify-cogents.json already at the workspace root."""


class DuplicateSourceIdError(OssifyError):
    """Raised when a registry entry's `id` collides with an existing entry."""


class InvalidRegistryEntryError(OssifyError):
    """Raised when a registry entry violates a business rule (e.g. `ref` on a local source)."""


class UnresolvableDiscoveryIdError(OssifyError):
    """Raised when a `discovery` id matches neither a built-in nor a custom strategy."""


class DuplicateDiscoveryIdError(OssifyError):
    """Raised when a `discovery-definitions` id collides with another custom entry or a built-in."""


class UnresolvableByPatternCategoryError(OssifyError):
    """Raised when an `install.by-pattern` category matches no discovery by-pattern category."""


class UnknownTargetPlatformError(OssifyError):
    """Raised when an `install.target-platforms` value is not a supported target platform."""


class UnmatchedInstallSelectionError(OssifyError):
    """Raised when an exact-literal install selection matches no discovered id."""


class UnsupportedTargetActionError(OssifyError):
    """Raised when a target adapter cannot perform a requested write action."""


class TargetNotWritableError(OssifyError):
    """Raised when the filesystem denies a write ossify-cogents needs to perform.

    Carries the offending path, its owner, and the `chown` that fixes it, because
    the reflex this error has to head off is re-running the command under `sudo`.
    """


class SourceFetchError(OssifyError):
    """Raised when materializing a registry source fails (e.g. a git clone/fetch failure)."""


class TargetLayoutUnavailableError(OssifyError):
    """Raised when no target-layout entry exists for a selected `(platform, category)` pair."""


class ShapeMismatchError(OssifyError):
    """Raised when a discovered item's shape disagrees with its target layout's expectation."""


class SeveredLinkError(OssifyError):
    """Raised when a `mode: link` destination holds content that differs from its source."""


class LinkNotSupportedError(OssifyError):
    """Raised when the platform cannot create the symbolic link a `mode: link` entry requires."""
