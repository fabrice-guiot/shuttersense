"""Unit tests for backend.src.utils.version — semantic version parsing."""

from packaging.version import Version

from backend.src.utils.version import parse_version_safe


class TestParseVersionSafe:
    """Tests for parse_version_safe()."""

    def test_strips_v_prefix(self):
        assert parse_version_safe("v1.2.3") == Version("1.2.3")

    def test_no_prefix(self):
        assert parse_version_safe("1.2.3") == Version("1.2.3")

    def test_semver_ordering_v1_18_gt_v1_8(self):
        assert parse_version_safe("v1.18") > parse_version_safe("v1.8")

    def test_semver_ordering_v2_gt_v1_99(self):
        assert parse_version_safe("v2.0.0") > parse_version_safe("v1.99.99")

    def test_invalid_version_falls_back_to_zero(self):
        assert parse_version_safe("not-a-version") == Version("0.0.0")

    def test_empty_string_falls_back_to_zero(self):
        assert parse_version_safe("") == Version("0.0.0")

    def test_fallback_sorts_below_any_valid_version(self):
        assert parse_version_safe("invalid") < parse_version_safe("v0.0.1")

    def test_two_part_version(self):
        assert parse_version_safe("v1.8") == Version("1.8")

    def test_sorting_list_of_versions(self):
        versions = ["v1.8", "v1.18", "v2.0.0", "v1.2.3", "v0.9"]
        sorted_versions = sorted(versions, key=parse_version_safe)
        assert sorted_versions == ["v0.9", "v1.2.3", "v1.8", "v1.18", "v2.0.0"]
