"""
Tests for version.py module.

Tests version extraction from Git tags, development version suffixes,
fallback behavior, and version parsing.
"""

import pytest
import subprocess
from unittest.mock import patch, MagicMock
import version


class TestGitVersionExtraction:
    """Tests for extracting version from Git tags"""

    def test_version_on_exact_tag(self, monkeypatch):
        """Test version extraction when exactly on a Git tag"""
        # Reset cache
        monkeypatch.setattr(version, '_VERSION_CACHE', None)

        def mock_run(args, **kwargs):
            result = MagicMock()
            if 'describe' in args:
                result.stdout = "v1.2.3-0-ga1b2c3d\n"
            result.returncode = 0
            return result

        with patch('subprocess.run', side_effect=mock_run):
            ver = version.get_version()
            assert ver == "v1.2.3"

    def test_version_ahead_of_tag(self, monkeypatch):
        """Test version when commits ahead of latest tag"""
        # Reset cache
        monkeypatch.setattr(version, '_VERSION_CACHE', None)

        def mock_run(args, **kwargs):
            result = MagicMock()
            if 'describe' in args:
                result.stdout = "v1.2.3-5-ga1b2c3d\n"
            result.returncode = 0
            return result

        with patch('subprocess.run', side_effect=mock_run):
            ver = version.get_version()
            assert ver == "v1.2.3-dev.5+a1b2c3d"

    def test_version_no_tags_exist(self, monkeypatch):
        """Test version when no Git tags exist"""
        # Reset cache
        monkeypatch.setattr(version, '_VERSION_CACHE', None)

        def mock_run(args, **kwargs):
            result = MagicMock()
            if 'describe' in args:
                result.stdout = "a1b2c3d\n"  # Just commit hash, no tags
            elif 'tag' in args and '--list' in args:
                result.stdout = ""  # No tags
            elif 'rev-parse' in args:
                result.stdout = "a1b2c3d\n"
            result.returncode = 0
            return result

        with patch('subprocess.run', side_effect=mock_run):
            ver = version.get_version()
            assert ver == "v0.0.0-dev+a1b2c3d"

    def test_version_git_not_available(self, monkeypatch):
        """Test fallback when Git is not available"""
        # Reset cache
        monkeypatch.setattr(version, '_VERSION_CACHE', None)

        def mock_run(args, **kwargs):
            raise FileNotFoundError("git command not found")

        with patch('subprocess.run', side_effect=mock_run):
            ver = version.get_version()
            assert ver == "v0.0.0-dev+unknown"

    def test_version_git_command_fails(self, monkeypatch):
        """Test fallback when Git command fails"""
        # Reset cache
        monkeypatch.setattr(version, '_VERSION_CACHE', None)

        def mock_run(args, **kwargs):
            raise subprocess.CalledProcessError(128, args)

        with patch('subprocess.run', side_effect=mock_run):
            ver = version.get_version()
            assert ver == "v0.0.0-dev+unknown"

    def test_version_git_timeout(self, monkeypatch):
        """Test fallback when Git command times out"""
        # Reset cache
        monkeypatch.setattr(version, '_VERSION_CACHE', None)

        def mock_run(args, **kwargs):
            raise subprocess.TimeoutExpired(args, timeout=5)

        with patch('subprocess.run', side_effect=mock_run):
            ver = version.get_version()
            assert ver == "v0.0.0-dev+unknown"


class TestVersionCaching:
    """Tests for version caching behavior"""

    def test_version_cached_after_first_call(self, monkeypatch):
        """Test that version is cached after first call"""
        # Reset cache
        monkeypatch.setattr(version, '_VERSION_CACHE', None)

        call_count = 0

        def mock_run(args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.stdout = "v1.0.0-0-ga1b2c3d\n"
            result.returncode = 0
            return result

        with patch('subprocess.run', side_effect=mock_run):
            # First call should invoke Git
            ver1 = version.get_version()
            assert call_count == 1

            # Second call should use cache
            ver2 = version.get_version()
            assert call_count == 1  # Should not increase

            assert ver1 == ver2 == "v1.0.0"


class TestEnvironmentVariableOverride:
    """Tests for environment variable override behavior"""

    def test_env_var_overrides_git(self, monkeypatch):
        """Test that SHUSAI_VERSION takes precedence over Git tags"""
        # Reset cache
        monkeypatch.setattr(version, '_VERSION_CACHE', None)
        monkeypatch.setenv('SHUSAI_VERSION', 'v2.0.0-prerelease')

        def mock_run(args, **kwargs):
            # Git is available and would return a different version
            result = MagicMock()
            if 'describe' in args:
                result.stdout = "v1.5.0-0-ga1b2c3d\n"
            result.returncode = 0
            return result

        with patch('subprocess.run', side_effect=mock_run):
            ver = version.get_version()
            # Should use env var, NOT Git
            assert ver == "v2.0.0-prerelease"

    def test_env_var_fallback_when_git_unavailable(self, monkeypatch):
        """Test using SHUSAI_VERSION when Git is not available"""
        # Reset cache
        monkeypatch.setattr(version, '_VERSION_CACHE', None)
        monkeypatch.setenv('SHUSAI_VERSION', 'v2.0.0-ci')

        def mock_run(args, **kwargs):
            raise FileNotFoundError("git not found")

        with patch('subprocess.run', side_effect=mock_run):
            ver = version.get_version()
            assert ver == "v2.0.0-ci"

    def test_git_used_when_env_var_not_set(self, monkeypatch):
        """Test that Git is used when SHUSAI_VERSION is not set"""
        # Reset cache
        monkeypatch.setattr(version, '_VERSION_CACHE', None)
        monkeypatch.delenv('SHUSAI_VERSION', raising=False)

        def mock_run(args, **kwargs):
            result = MagicMock()
            if 'describe' in args:
                result.stdout = "v1.5.0-0-ga1b2c3d\n"
            result.returncode = 0
            return result

        with patch('subprocess.run', side_effect=mock_run):
            ver = version.get_version()
            # Should use Git version
            assert ver == "v1.5.0"

    def test_fallback_without_env_var_and_git(self, monkeypatch):
        """Test fallback to default when no environment variable and no Git"""
        # Reset cache
        monkeypatch.setattr(version, '_VERSION_CACHE', None)
        monkeypatch.delenv('SHUSAI_VERSION', raising=False)

        def mock_run(args, **kwargs):
            raise FileNotFoundError("git not found")

        with patch('subprocess.run', side_effect=mock_run):
            ver = version.get_version()
            assert ver == "v0.0.0-dev+unknown"


class TestVersionTupleParsing:
    """Tests for version tuple parsing"""

    def test_parse_release_version(self, monkeypatch):
        """Test parsing a clean release version"""
        monkeypatch.setattr(version, '_VERSION_CACHE', "v1.2.3")

        version_tuple = version.get_version_tuple()
        assert version_tuple == (1, 2, 3, None)

    def test_parse_development_version(self, monkeypatch):
        """Test parsing a development version with suffix"""
        monkeypatch.setattr(version, '_VERSION_CACHE', "v1.2.3-dev.5+a1b2c3d")

        version_tuple = version.get_version_tuple()
        assert version_tuple == (1, 2, 3, "dev.5+a1b2c3d")

    def test_parse_version_without_v_prefix(self, monkeypatch):
        """Test parsing version without 'v' prefix"""
        monkeypatch.setattr(version, '_VERSION_CACHE', "2.0.0")

        version_tuple = version.get_version_tuple()
        assert version_tuple == (2, 0, 0, None)

    def test_parse_invalid_version_format(self, monkeypatch):
        """Test parsing an invalid version format"""
        monkeypatch.setattr(version, '_VERSION_CACHE', "invalid-version")

        version_tuple = version.get_version_tuple()
        # Should return fallback tuple
        assert version_tuple == (0, 0, 0, "invalid-version")

    def test_parse_version_with_rc_suffix(self, monkeypatch):
        """Test parsing version with release candidate suffix"""
        monkeypatch.setattr(version, '_VERSION_CACHE', "v1.0.0-rc.1")

        version_tuple = version.get_version_tuple()
        assert version_tuple == (1, 0, 0, "rc.1")


class TestModuleLevelConstants:
    """Tests for module-level constants"""

    def test_version_constant_available(self):
        """Test that __version__ is available at module level"""
        assert hasattr(version, '__version__')
        assert isinstance(version.__version__, str)
        assert len(version.__version__) > 0

    def test_version_info_constant_available(self):
        """Test that __version_info__ is available at module level"""
        assert hasattr(version, '__version_info__')
        assert isinstance(version.__version_info__, tuple)
        assert len(version.__version_info__) == 4

    def test_version_alias_available(self):
        """Test that VERSION alias is available"""
        assert hasattr(version, 'VERSION')
        assert version.VERSION == version.__version__


class TestVersionFormats:
    """Tests for various version format scenarios"""

    def test_version_with_multi_digit_components(self, monkeypatch):
        """Test version with multi-digit major/minor/patch"""
        monkeypatch.setattr(version, '_VERSION_CACHE', None)

        def mock_run(args, **kwargs):
            result = MagicMock()
            if 'describe' in args:
                result.stdout = "v12.34.567-0-gabcdef0\n"
            result.returncode = 0
            return result

        with patch('subprocess.run', side_effect=mock_run):
            ver = version.get_version()
            assert ver == "v12.34.567"

            version_tuple = version.get_version_tuple()
            assert version_tuple == (12, 34, 567, None)

    def test_version_with_long_dev_suffix(self, monkeypatch):
        """Test version with many commits ahead"""
        monkeypatch.setattr(version, '_VERSION_CACHE', None)

        def mock_run(args, **kwargs):
            result = MagicMock()
            if 'describe' in args:
                result.stdout = "v1.0.0-123-gabcdef0\n"
            result.returncode = 0
            return result

        with patch('subprocess.run', side_effect=mock_run):
            ver = version.get_version()
            assert ver == "v1.0.0-dev.123+abcdef0"

    def test_version_with_longer_commit_hash(self, monkeypatch):
        """Test version with longer commit hash format"""
        monkeypatch.setattr(version, '_VERSION_CACHE', None)

        def mock_run(args, **kwargs):
            result = MagicMock()
            if 'describe' in args:
                result.stdout = "v2.1.0-3-gabcdef0123\n"
            result.returncode = 0
            return result

        with patch('subprocess.run', side_effect=mock_run):
            ver = version.get_version()
            assert ver == "v2.1.0-dev.3+abcdef0123"


class TestRealWorldScenarios:
    """Integration-like tests for real-world scenarios"""

    def test_fresh_repository_no_tags(self, monkeypatch):
        """Test behavior in a fresh repository with no tags"""
        monkeypatch.setattr(version, '_VERSION_CACHE', None)

        def mock_run(args, **kwargs):
            result = MagicMock()
            if 'describe' in args:
                result.stdout = "abc123d\n"  # Just commit hash
            elif 'tag' in args and '--list' in args:
                result.stdout = ""  # No tags
            elif 'rev-parse' in args:
                result.stdout = "abc123d\n"
            result.returncode = 0
            return result

        with patch('subprocess.run', side_effect=mock_run):
            ver = version.get_version()
            assert ver.startswith("v0.0.0-dev+")
            assert "abc123d" in ver

    def test_ci_environment_with_env_var(self, monkeypatch):
        """Test CI/CD environment using environment variable"""
        monkeypatch.setattr(version, '_VERSION_CACHE', None)
        monkeypatch.setenv('SHUSAI_VERSION', 'v1.5.0-build.42')

        def mock_run(args, **kwargs):
            raise FileNotFoundError("Git not available in CI")

        with patch('subprocess.run', side_effect=mock_run):
            ver = version.get_version()
            assert ver == "v1.5.0-build.42"

    def test_release_tag_exact_match(self, monkeypatch):
        """Test exact match on a release tag"""
        monkeypatch.setattr(version, '_VERSION_CACHE', None)

        def mock_run(args, **kwargs):
            result = MagicMock()
            if 'describe' in args:
                result.stdout = "v2.0.0-0-g1234567\n"
            result.returncode = 0
            return result

        with patch('subprocess.run', side_effect=mock_run):
            ver = version.get_version()
            assert ver == "v2.0.0"

            # Should be a clean release version
            version_tuple = version.get_version_tuple()
            assert version_tuple == (2, 0, 0, None)
