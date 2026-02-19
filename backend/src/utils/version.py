"""
Semantic version parsing utility for release manifest comparison.

Provides safe version parsing that strips 'v' prefixes and handles
invalid version strings gracefully, used by release endpoints and
agent outdated detection.
"""

from packaging.version import InvalidVersion, Version

# Fallback for unparseable version strings — sorts below any valid version.
_FALLBACK_VERSION = Version("0.0.0")


def parse_version_safe(version_str: str) -> Version:
    """Parse a version string for sorting, stripping leading 'v' prefix.

    Args:
        version_str: Version string such as "v1.18.0" or "1.8".

    Returns:
        A ``packaging.version.Version`` instance.  If *version_str* cannot
        be parsed, returns ``Version("0.0.0")`` so the entry sorts below
        every valid release.
    """
    try:
        return Version(version_str.lstrip("v"))
    except (InvalidVersion, AttributeError):
        return _FALLBACK_VERSION
