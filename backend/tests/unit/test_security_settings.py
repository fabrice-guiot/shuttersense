"""
Tests for security settings module.

Tests path validation and authorization functions used to prevent
path traversal attacks in collection and SPA file serving.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from backend.src.utils.security_settings import (
    get_authorized_local_roots,
    is_path_authorized,
    get_spa_dist_path,
    is_safe_static_file_path,
    clear_security_settings_cache,
    ENV_AUTHORIZED_LOCAL_ROOTS,
    ENV_SPA_DIST_PATH
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the cache before each test."""
    clear_security_settings_cache()
    yield
    clear_security_settings_cache()


class TestGetAuthorizedLocalRoots:
    """Tests for get_authorized_local_roots function."""

    def test_returns_empty_list_when_not_configured(self):
        """Test that empty list is returned when env var is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove the env var if it exists
            os.environ.pop(ENV_AUTHORIZED_LOCAL_ROOTS, None)
            clear_security_settings_cache()

            roots = get_authorized_local_roots()
            assert roots == []

    def test_parses_single_path(self):
        """Test parsing a single authorized path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {ENV_AUTHORIZED_LOCAL_ROOTS: temp_dir}):
                clear_security_settings_cache()
                roots = get_authorized_local_roots()

                assert len(roots) == 1
                assert roots[0] == Path(temp_dir).resolve()

    def test_parses_multiple_paths(self):
        """Test parsing multiple comma-separated paths."""
        with tempfile.TemporaryDirectory() as temp_dir1:
            with tempfile.TemporaryDirectory() as temp_dir2:
                env_value = f"{temp_dir1},{temp_dir2}"
                with patch.dict(os.environ, {ENV_AUTHORIZED_LOCAL_ROOTS: env_value}):
                    clear_security_settings_cache()
                    roots = get_authorized_local_roots()

                    assert len(roots) == 2
                    assert Path(temp_dir1).resolve() in roots
                    assert Path(temp_dir2).resolve() in roots

    def test_expands_tilde_in_paths(self):
        """Test that ~ is expanded to home directory."""
        home_dir = Path.home()
        with patch.dict(os.environ, {ENV_AUTHORIZED_LOCAL_ROOTS: "~/test_path"}):
            clear_security_settings_cache()
            roots = get_authorized_local_roots()

            assert len(roots) == 1
            assert roots[0] == (home_dir / "test_path").resolve()

    def test_ignores_empty_entries(self):
        """Test that empty entries in comma list are ignored."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_value = f",{temp_dir},,,"
            with patch.dict(os.environ, {ENV_AUTHORIZED_LOCAL_ROOTS: env_value}):
                clear_security_settings_cache()
                roots = get_authorized_local_roots()

                assert len(roots) == 1
                assert roots[0] == Path(temp_dir).resolve()

    def test_caches_results(self):
        """Test that results are cached."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {ENV_AUTHORIZED_LOCAL_ROOTS: temp_dir}):
                clear_security_settings_cache()

                roots1 = get_authorized_local_roots()
                roots2 = get_authorized_local_roots()

                # Should be the same object (cached)
                assert roots1 is roots2


class TestIsPathAuthorized:
    """Tests for is_path_authorized function."""

    def test_rejects_path_when_no_roots_configured(self):
        """Test that paths are rejected when no roots are configured."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop(ENV_AUTHORIZED_LOCAL_ROOTS, None)
            clear_security_settings_cache()

            is_auth, error = is_path_authorized("/some/path")

            assert is_auth is False
            assert error is not None
            assert "disabled" in error.lower()

    def test_rejects_path_traversal_attempts(self):
        """Test that paths with .. are rejected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {ENV_AUTHORIZED_LOCAL_ROOTS: temp_dir}):
                clear_security_settings_cache()

                # Test various path traversal patterns
                traversal_paths = [
                    f"{temp_dir}/../etc/passwd",
                    f"{temp_dir}/..%2F..%2Fetc",
                    "../../../etc/passwd",
                    "foo/../bar/../etc",
                ]

                for path in traversal_paths:
                    is_auth, error = is_path_authorized(path)
                    assert is_auth is False, f"Path {path} should be rejected"
                    assert error is not None
                    assert ".." in error

    def test_accepts_authorized_path(self):
        """Test that paths under authorized roots are accepted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subdir = Path(temp_dir) / "photos" / "2024"
            subdir.mkdir(parents=True)

            with patch.dict(os.environ, {ENV_AUTHORIZED_LOCAL_ROOTS: temp_dir}):
                clear_security_settings_cache()

                is_auth, error = is_path_authorized(str(subdir))

                assert is_auth is True
                assert error is None

    def test_rejects_path_outside_authorized_roots(self):
        """Test that paths outside authorized roots are rejected."""
        with tempfile.TemporaryDirectory() as temp_dir1:
            with tempfile.TemporaryDirectory() as temp_dir2:
                # Only authorize temp_dir1
                with patch.dict(os.environ, {ENV_AUTHORIZED_LOCAL_ROOTS: temp_dir1}):
                    clear_security_settings_cache()

                    # Try to access temp_dir2
                    is_auth, error = is_path_authorized(temp_dir2)

                    assert is_auth is False
                    assert error is not None
                    assert "not under an authorized root" in error.lower()

    def test_accepts_path_with_tilde(self):
        """Test that paths with ~ are properly expanded and validated."""
        home_dir = Path.home()
        with tempfile.TemporaryDirectory(dir=home_dir) as temp_dir:
            # Get the relative path from home
            rel_path = Path(temp_dir).relative_to(home_dir)

            with patch.dict(os.environ, {ENV_AUTHORIZED_LOCAL_ROOTS: str(home_dir)}):
                clear_security_settings_cache()

                is_auth, error = is_path_authorized(f"~/{rel_path}")

                assert is_auth is True
                assert error is None

    def test_handles_relative_paths(self):
        """Test that relative paths are resolved correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {ENV_AUTHORIZED_LOCAL_ROOTS: temp_dir}):
                clear_security_settings_cache()

                # Create a file to test with
                test_file = Path(temp_dir) / "test.txt"
                test_file.touch()

                # Current directory might not be under authorized root
                # so a simple relative path should be rejected unless cwd is temp_dir
                original_cwd = os.getcwd()
                try:
                    os.chdir(temp_dir)
                    is_auth, error = is_path_authorized("test.txt")
                    assert is_auth is True
                finally:
                    os.chdir(original_cwd)


class TestGetSpaDistPath:
    """Tests for get_spa_dist_path function."""

    def test_returns_configured_path_when_set(self):
        """Test that configured SPA dist path is returned."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {ENV_SPA_DIST_PATH: temp_dir}):
                clear_security_settings_cache()

                result = get_spa_dist_path()

                assert result == Path(temp_dir).resolve()

    def test_returns_default_path_when_not_set(self):
        """Test that default path is returned when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop(ENV_SPA_DIST_PATH, None)
            clear_security_settings_cache()

            result = get_spa_dist_path()

            # Should be frontend/dist relative to project root
            assert result.name == "dist"
            assert result.parent.name == "frontend"

    def test_expands_tilde_in_configured_path(self):
        """Test that ~ is expanded in configured SPA path."""
        with patch.dict(os.environ, {ENV_SPA_DIST_PATH: "~/spa_dist"}):
            clear_security_settings_cache()

            result = get_spa_dist_path()

            assert result == (Path.home() / "spa_dist").resolve()

    def test_caches_results(self):
        """Test that SPA dist path is cached."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {ENV_SPA_DIST_PATH: temp_dir}):
                clear_security_settings_cache()

                result1 = get_spa_dist_path()
                result2 = get_spa_dist_path()

                assert result1 is result2


class TestIsSafeStaticFilePath:
    """Tests for is_safe_static_file_path function."""

    def test_rejects_empty_path(self):
        """Test that empty paths are rejected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            is_safe, path = is_safe_static_file_path("", Path(temp_dir))

            assert is_safe is False
            assert path is None

    def test_rejects_path_traversal(self):
        """Test that path traversal attempts are rejected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            test_file = Path(temp_dir) / "test.txt"
            test_file.touch()

            traversal_paths = [
                "../etc/passwd",
                "..%2F..%2Fetc/passwd",
                "foo/../../../etc/passwd",
                "test.txt/../../../etc/passwd",
            ]

            for path in traversal_paths:
                is_safe, result = is_safe_static_file_path(path, Path(temp_dir))
                assert is_safe is False, f"Path {path} should be rejected"
                assert result is None

    def test_rejects_absolute_paths(self):
        """Test that absolute paths are rejected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            is_safe, path = is_safe_static_file_path("/etc/passwd", Path(temp_dir))

            assert is_safe is False
            assert path is None

    def test_accepts_safe_file(self):
        """Test that safe files within base directory are accepted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            test_file = Path(temp_dir) / "favicon.ico"
            test_file.touch()

            is_safe, path = is_safe_static_file_path("favicon.ico", Path(temp_dir))

            assert is_safe is True
            # Compare resolved paths to handle symlinks (e.g., /var -> /private/var on macOS)
            assert path == test_file.resolve()

    def test_rejects_nonexistent_file(self):
        """Test that non-existent files are rejected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            is_safe, path = is_safe_static_file_path(
                "nonexistent.txt", Path(temp_dir)
            )

            assert is_safe is False
            assert path is None

    def test_accepts_file_in_subdirectory(self):
        """Test that files in subdirectories within base are accepted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a subdirectory with a file
            subdir = Path(temp_dir) / "assets"
            subdir.mkdir()
            test_file = subdir / "style.css"
            test_file.touch()

            is_safe, path = is_safe_static_file_path(
                "assets/style.css", Path(temp_dir)
            )

            assert is_safe is True
            # Compare resolved paths to handle symlinks (e.g., /var -> /private/var on macOS)
            assert path == test_file.resolve()

    def test_rejects_directory(self):
        """Test that directories are rejected (must be files)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a subdirectory
            subdir = Path(temp_dir) / "assets"
            subdir.mkdir()

            is_safe, path = is_safe_static_file_path("assets", Path(temp_dir))

            assert is_safe is False
            assert path is None

    def test_rejects_symlink_outside_base(self):
        """Test that symlinks pointing outside base directory are rejected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with tempfile.TemporaryDirectory() as outside_dir:
                # Create a file outside the base directory
                outside_file = Path(outside_dir) / "secret.txt"
                outside_file.write_text("secret data")

                # Create a symlink inside base pointing outside
                symlink = Path(temp_dir) / "link.txt"
                try:
                    symlink.symlink_to(outside_file)
                except OSError:
                    pytest.skip("Cannot create symlinks on this system")

                is_safe, path = is_safe_static_file_path("link.txt", Path(temp_dir))

                # Should be rejected because resolved path is outside base
                assert is_safe is False
                assert path is None


class TestCollectionPathSecurity:
    """Integration tests for collection path security."""

    def test_collection_creation_requires_authorized_roots(self, test_db_session, test_encryptor):
        """Test that collection creation validates against authorized roots."""
        from backend.src.services.collection_service import CollectionService
        from backend.src.services.connector_service import ConnectorService
        from backend.src.models import CollectionType, CollectionState
        from backend.src.utils.cache import FileListingCache

        cache = FileListingCache()
        connector_service = ConnectorService(test_db_session, test_encryptor)
        service = CollectionService(test_db_session, cache, connector_service)

        with tempfile.TemporaryDirectory() as temp_dir:
            # With no authorized roots, creation should fail
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop(ENV_AUTHORIZED_LOCAL_ROOTS, None)
                # Keep required env vars
                os.environ['PHOTO_ADMIN_MASTER_KEY'] = 'test-key-for-testing-123'
                os.environ['PHOTO_ADMIN_DB_URL'] = 'sqlite:///:memory:'
                clear_security_settings_cache()

                result = service.create_collection(
                    name="Test Collection",
                    type=CollectionType.LOCAL,
                    location=temp_dir,
                    state=CollectionState.LIVE
                )

                # Should fail because path is not authorized
                assert result.is_accessible is False
                assert result.last_error is not None
                assert "disabled" in result.last_error.lower()

    def test_collection_creation_succeeds_with_authorized_root(self, test_db_session, test_encryptor):
        """Test that collection creation succeeds when path is under authorized root."""
        from backend.src.services.collection_service import CollectionService
        from backend.src.services.connector_service import ConnectorService
        from backend.src.models import CollectionType, CollectionState
        from backend.src.utils.cache import FileListingCache

        cache = FileListingCache()
        connector_service = ConnectorService(test_db_session, test_encryptor)
        service = CollectionService(test_db_session, cache, connector_service)

        with tempfile.TemporaryDirectory() as temp_dir:
            # Configure the temp directory as an authorized root
            with patch.dict(os.environ, {ENV_AUTHORIZED_LOCAL_ROOTS: temp_dir}):
                clear_security_settings_cache()

                result = service.create_collection(
                    name="Test Collection",
                    type=CollectionType.LOCAL,
                    location=temp_dir,
                    state=CollectionState.LIVE
                )

                # Should succeed because path is authorized
                assert result.is_accessible is True
                assert result.last_error is None
