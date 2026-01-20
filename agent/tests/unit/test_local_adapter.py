"""
Unit tests for LocalAdapter.

Tests the LocalAdapter class which provides filesystem access
matching the StorageAdapter interface.
"""

import pytest
from pathlib import Path
import tempfile
import os

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.remote.local_adapter import LocalAdapter
from src.remote.base import FileInfo


class TestLocalAdapter:
    """Tests for LocalAdapter."""

    def test_init(self):
        """Test LocalAdapter initialization."""
        adapter = LocalAdapter({})
        assert adapter is not None

    def test_test_connection(self):
        """Test connection test always succeeds for local adapter."""
        adapter = LocalAdapter({})
        success, message = adapter.test_connection()
        assert success is True
        assert "Local filesystem access available" in message

    def test_list_files_with_temp_directory(self):
        """Test listing files in a temporary directory."""
        adapter = LocalAdapter({})

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some test files
            (Path(tmpdir) / "photo1.dng").write_text("test")
            (Path(tmpdir) / "photo2.cr3").write_text("test")
            (Path(tmpdir) / "subdir").mkdir()
            (Path(tmpdir) / "subdir" / "photo3.dng").write_text("test")

            files = adapter.list_files(tmpdir)

            assert len(files) == 3
            assert "photo1.dng" in files
            assert "photo2.cr3" in files
            # Subdir file should include relative path
            assert any("photo3.dng" in f for f in files)

    def test_list_files_with_metadata(self):
        """Test listing files with metadata."""
        adapter = LocalAdapter({})

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file with known content
            test_file = Path(tmpdir) / "test.dng"
            test_file.write_bytes(b"test content 123")

            files = adapter.list_files_with_metadata(tmpdir)

            assert len(files) == 1
            assert isinstance(files[0], FileInfo)
            assert files[0].path == "test.dng"
            assert files[0].size == 16  # len("test content 123")
            assert files[0].last_modified is not None

    def test_list_files_nonexistent_directory(self):
        """Test that listing nonexistent directory raises error."""
        adapter = LocalAdapter({})

        with pytest.raises(FileNotFoundError):
            adapter.list_files("/nonexistent/path/12345")

    def test_list_files_file_not_directory(self):
        """Test that listing a file (not directory) raises error."""
        adapter = LocalAdapter({})

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            temp_path = f.name

        try:
            with pytest.raises(ValueError):
                adapter.list_files(temp_path)
        finally:
            os.unlink(temp_path)


class TestFileInfoProperties:
    """Tests for FileInfo computed properties."""

    def test_name_simple(self):
        """Test name property for simple path."""
        fi = FileInfo(path="photo.dng", size=100)
        assert fi.name == "photo.dng"

    def test_name_with_directory(self):
        """Test name property with directory path."""
        fi = FileInfo(path="subdir/photo.dng", size=100)
        assert fi.name == "photo.dng"

    def test_name_nested_directory(self):
        """Test name property with nested directory path."""
        fi = FileInfo(path="a/b/c/photo.dng", size=100)
        assert fi.name == "photo.dng"

    def test_extension_lowercase(self):
        """Test extension property returns lowercase."""
        fi = FileInfo(path="photo.DNG", size=100)
        assert fi.extension == ".dng"

    def test_extension_already_lowercase(self):
        """Test extension property with lowercase extension."""
        fi = FileInfo(path="photo.cr3", size=100)
        assert fi.extension == ".cr3"

    def test_extension_no_extension(self):
        """Test extension property for file without extension."""
        fi = FileInfo(path="README", size=100)
        assert fi.extension == ""

    def test_stem_simple(self):
        """Test stem property for simple filename."""
        fi = FileInfo(path="photo.dng", size=100)
        assert fi.stem == "photo"

    def test_stem_complex(self):
        """Test stem property for complex filename."""
        fi = FileInfo(path="AB3D0001-HDR.dng", size=100)
        assert fi.stem == "AB3D0001-HDR"

    def test_stem_no_extension(self):
        """Test stem property for file without extension."""
        fi = FileInfo(path="README", size=100)
        assert fi.stem == "README"

    def test_from_path_object(self):
        """Test creating FileInfo from Path object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            test_file = base_path / "test.dng"
            test_file.write_bytes(b"test data here")

            fi = FileInfo.from_path_object(test_file, base_path)

            assert fi.path == "test.dng"
            assert fi.size == 14  # len("test data here")
            assert fi.last_modified is not None
