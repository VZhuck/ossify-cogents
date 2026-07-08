from importlib.metadata import PackageNotFoundError, version

from domain.errors import VersionUnavailableError


class GetVersion:
    """Implements `ports_in.VersionPort` — no inheritance needed, structural typing."""

    def get_version(self) -> str:
        try:
            return version("ossify-cogents")
        except PackageNotFoundError as exc:
            raise VersionUnavailableError("ossify-cogents is not installed") from exc
