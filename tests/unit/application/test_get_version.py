from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

import pytest

from application import GetVersion
from domain.errors import VersionUnavailableError


def test_get_version_returns_installed_package_version() -> None:
    use_case = GetVersion()

    with patch("application._get_version.version", return_value="1.2.3"):
        result = use_case.get_version()

    assert result == "1.2.3"


def test_get_version_raises_domain_error_when_package_not_installed() -> None:
    use_case = GetVersion()

    with patch("application._get_version.version", side_effect=PackageNotFoundError):
        with pytest.raises(VersionUnavailableError):
            use_case.get_version()
