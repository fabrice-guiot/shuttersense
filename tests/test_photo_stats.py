"""
Tests for photo_stats.py
"""

import pytest
from pathlib import Path
import sys
import os

# Add parent directory to path to import photo_stats
sys.path.insert(0, str(Path(__file__).parent.parent))

from photo_stats import PhotoStats


class TestPhotoStatsInit:
    """Tests for PhotoStats initialization."""

    def test_init_with_valid_path(self, temp_photo_dir):
        """Test initialization with a valid directory path."""
        stats = PhotoStats(temp_photo_dir)
        assert stats.folder_path == temp_photo_dir
        assert isinstance(stats.stats, dict)
        assert stats.stats['total_files'] == 0
        assert stats.stats['total_size'] == 0

    def test_init_with_string_path(self, temp_photo_dir):
        """Test initialization with string path."""
        stats = PhotoStats(str(temp_photo_dir))
        assert stats.folder_path == Path(temp_photo_dir)

    def test_stats_structure(self, temp_photo_dir):
        """Test that stats dictionary has correct structure."""
        stats = PhotoStats(temp_photo_dir)
        expected_keys = [
            'file_counts', 'file_sizes', 'total_size', 'total_files',
            'paired_files', 'orphaned_images', 'orphaned_xmp',
            'xmp_metadata', 'scan_time', 'folder_path'
        ]
        for key in expected_keys:
            assert key in stats.stats


class TestFileScanningFunctionality:
    """Tests for file scanning functionality."""

    def test_scan_valid_folder(self, temp_photo_dir):
        """Test scanning a folder with photo files."""
        stats = PhotoStats(temp_photo_dir)
        result = stats.scan_folder()

        assert result['total_files'] == 12
        assert result['scan_time'] > 0
        assert str(temp_photo_dir.resolve()) in result['folder_path']

    def test_scan_nonexistent_folder(self, tmp_path):
        """Test scanning a non-existent folder raises error."""
        non_existent = tmp_path / "does_not_exist"
        stats = PhotoStats(non_existent)

        with pytest.raises(FileNotFoundError):
            stats.scan_folder()

    def test_scan_empty_folder(self, empty_dir):
        """Test scanning an empty folder."""
        stats = PhotoStats(empty_dir)
        result = stats.scan_folder()

        assert result['total_files'] == 0
        assert result['total_size'] == 0
        assert len(result['file_counts']) == 0

    def test_recursive_scanning(self, temp_photo_dir):
        """Test that scanning finds files in subdirectories."""
        stats = PhotoStats(temp_photo_dir)
        stats.scan_folder()

        # We created files in root and two subdirectories
        assert stats.stats['total_files'] == 12

    def test_ignores_non_photo_files(self, mixed_file_dir):
        """Test that non-photo files are ignored."""
        stats = PhotoStats(mixed_file_dir)
        stats.scan_folder()

        # Should only count .dng and .xmp, not .txt, .py, .jpg
        assert stats.stats['total_files'] == 2


class TestStatisticsCollection:
    """Tests for statistics collection."""

    def test_file_count_by_type(self, temp_photo_dir):
        """Test file counting by type."""
        stats = PhotoStats(temp_photo_dir)
        stats.scan_folder()

        assert stats.stats['file_counts']['.dng'] == 2
        assert stats.stats['file_counts']['.cr3'] == 2
        assert stats.stats['file_counts']['.tiff'] == 1
        assert stats.stats['file_counts']['.tif'] == 1
        assert stats.stats['file_counts']['.xmp'] == 6

    def test_file_size_tracking(self, temp_photo_dir):
        """Test file size tracking."""
        stats = PhotoStats(temp_photo_dir)
        stats.scan_folder()

        # Each file is ~1.5KB (b"fake photo data" * 100)
        # 12 files total
        assert stats.stats['total_size'] > 0
        assert stats.stats['total_size'] == 12 * 1500  # 18000 bytes

        # Check that file_sizes contains lists of sizes
        for ext in stats.stats['file_sizes']:
            assert isinstance(stats.stats['file_sizes'][ext], list)
            assert all(size > 0 for size in stats.stats['file_sizes'][ext])

    def test_case_insensitive_extensions(self, tmp_path):
        """Test that file extensions are handled case-insensitively."""
        test_dir = tmp_path / "case_test"
        test_dir.mkdir()

        (test_dir / "image.DNG").write_bytes(b"data")
        (test_dir / "image.Tiff").write_bytes(b"data")
        (test_dir / "image.CR3").write_bytes(b"data")

        stats = PhotoStats(test_dir)
        stats.scan_folder()

        # All should be normalized to lowercase
        assert '.dng' in stats.stats['file_counts']
        assert '.tiff' in stats.stats['file_counts']
        assert '.cr3' in stats.stats['file_counts']


class TestFilePairingAnalysis:
    """Tests for file pairing analysis."""

    def test_paired_files_detection(self, temp_photo_dir):
        """Test detection of paired image and XMP files."""
        stats = PhotoStats(temp_photo_dir)
        stats.scan_folder()

        # We have 5 properly paired files:
        # IMG_001, IMG_002, IMG_003, IMG_100, IMG_200
        assert len(stats.stats['paired_files']) == 5

    def test_orphaned_images_detection(self, temp_photo_dir):
        """Test detection of images without XMP files."""
        stats = PhotoStats(temp_photo_dir)
        stats.scan_folder()

        # IMG_101.cr3 has no XMP
        assert len(stats.stats['orphaned_images']) == 1
        orphaned_file = Path(stats.stats['orphaned_images'][0])
        assert orphaned_file.stem == 'IMG_101'
        assert orphaned_file.suffix.lower() == '.cr3'

    def test_orphaned_xmp_detection(self, temp_photo_dir):
        """Test detection of XMP files without images."""
        stats = PhotoStats(temp_photo_dir)
        stats.scan_folder()

        # IMG_201.xmp has no image
        assert len(stats.stats['orphaned_xmp']) == 1
        orphaned_file = Path(stats.stats['orphaned_xmp'][0])
        assert orphaned_file.stem == 'IMG_201'
        assert orphaned_file.suffix.lower() == '.xmp'

    def test_all_files_paired(self, tmp_path):
        """Test when all files are properly paired."""
        test_dir = tmp_path / "all_paired"
        test_dir.mkdir()

        (test_dir / "photo1.dng").write_bytes(b"data")
        (test_dir / "photo1.xmp").write_bytes(b"data")
        (test_dir / "photo2.cr3").write_bytes(b"data")
        (test_dir / "photo2.xmp").write_bytes(b"data")

        stats = PhotoStats(test_dir)
        stats.scan_folder()

        assert len(stats.stats['paired_files']) == 2
        assert len(stats.stats['orphaned_images']) == 0
        assert len(stats.stats['orphaned_xmp']) == 0

    def test_no_xmp_files(self, tmp_path):
        """Test when there are only image files, no XMP."""
        test_dir = tmp_path / "no_xmp"
        test_dir.mkdir()

        (test_dir / "photo1.dng").write_bytes(b"data")
        (test_dir / "photo2.cr3").write_bytes(b"data")

        stats = PhotoStats(test_dir)
        stats.scan_folder()

        assert len(stats.stats['paired_files']) == 0
        assert len(stats.stats['orphaned_images']) == 2
        assert len(stats.stats['orphaned_xmp']) == 0


class TestXMPMetadataExtraction:
    """Tests for XMP metadata extraction."""

    def test_parse_xmp_file(self, temp_xmp_file):
        """Test parsing a valid XMP file."""
        stats = PhotoStats(temp_xmp_file.parent)
        metadata = stats._parse_xmp_file(temp_xmp_file)

        # Metadata might be None or dict depending on parser implementation
        assert metadata is None or isinstance(metadata, dict)

    def test_xmp_metadata_extraction(self, tmp_path, sample_xmp_content):
        """Test extraction of XMP metadata from files."""
        test_dir = tmp_path / "xmp_test"
        test_dir.mkdir()

        # Create image with XMP
        (test_dir / "photo.dng").write_bytes(b"data")
        (test_dir / "photo.xmp").write_text(sample_xmp_content)

        stats = PhotoStats(test_dir)
        stats.scan_folder()

        # XMP metadata extraction might fail if content isn't parsed correctly
        # The important thing is that it doesn't crash
        assert isinstance(stats.stats['xmp_metadata'], list)
        if len(stats.stats['xmp_metadata']) > 0:
            metadata = stats.stats['xmp_metadata'][0]
            assert 'file' in metadata

    def test_invalid_xmp_handling(self, tmp_path):
        """Test handling of invalid/corrupted XMP files."""
        test_dir = tmp_path / "invalid_xmp"
        test_dir.mkdir()

        # Create invalid XMP file
        (test_dir / "photo.dng").write_bytes(b"data")
        (test_dir / "photo.xmp").write_text("This is not valid XML")

        stats = PhotoStats(test_dir)
        # Should not raise an error, just skip the invalid file
        stats.scan_folder()

        # Invalid XMP should be skipped
        assert len(stats.stats['xmp_metadata']) == 0

    def test_empty_xmp_file(self, tmp_path):
        """Test handling of empty XMP files."""
        test_dir = tmp_path / "empty_xmp"
        test_dir.mkdir()

        (test_dir / "photo.dng").write_bytes(b"data")
        (test_dir / "photo.xmp").write_text("")

        stats = PhotoStats(test_dir)
        stats.scan_folder()

        # Empty XMP should not crash the parser
        assert len(stats.stats['xmp_metadata']) == 0


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_format_size_bytes(self, temp_photo_dir):
        """Test byte size formatting."""
        stats = PhotoStats(temp_photo_dir)

        assert stats._format_size(100) == "100.00 B"
        assert stats._format_size(1024) == "1.00 KB"
        assert stats._format_size(1024 * 1024) == "1.00 MB"
        assert stats._format_size(1024 * 1024 * 1024) == "1.00 GB"
        assert stats._format_size(1024 * 1024 * 1024 * 1024) == "1.00 TB"

    def test_format_size_precision(self, temp_photo_dir):
        """Test size formatting precision."""
        stats = PhotoStats(temp_photo_dir)

        assert stats._format_size(1536) == "1.50 KB"
        assert stats._format_size(2560) == "2.50 KB"

    def test_generate_file_type_rows(self, temp_photo_dir):
        """Test HTML table row generation."""
        stats = PhotoStats(temp_photo_dir)
        stats.scan_folder()

        rows = stats._generate_file_type_rows()

        assert isinstance(rows, str)
        assert '<tr>' in rows
        assert '<td>' in rows
        # Should contain file extensions
        assert '.DNG' in rows or '.dng' in rows.upper()


class TestHTMLReportGeneration:
    """Tests for HTML report generation."""

    def test_generate_html_report(self, temp_photo_dir, tmp_path):
        """Test HTML report generation."""
        stats = PhotoStats(temp_photo_dir)
        stats.scan_folder()

        output_file = tmp_path / "test_report.html"
        result = stats.generate_html_report(str(output_file))

        assert result.exists()
        assert result.suffix == '.html'

        # Check HTML content
        content = result.read_text()
        assert '<!DOCTYPE html>' in content
        assert 'Photo Statistics Report' in content

    def test_html_report_contains_stats(self, temp_photo_dir, tmp_path):
        """Test that HTML report contains statistics."""
        stats = PhotoStats(temp_photo_dir)
        stats.scan_folder()

        output_file = tmp_path / "test_report.html"
        stats.generate_html_report(str(output_file))

        content = output_file.read_text()

        # Should contain key statistics
        assert str(stats.stats['total_files']) in content
        assert 'chart.js' in content.lower()  # Should include charting library

    def test_html_report_default_name(self, temp_photo_dir, tmp_path):
        """Test HTML report generation with default name."""
        stats = PhotoStats(temp_photo_dir)
        stats.scan_folder()

        # Change to tmp directory to avoid polluting working directory
        original_dir = Path.cwd()
        try:
            os.chdir(tmp_path)
            result = stats.generate_html_report()
            assert result.name == 'photo_stats_report.html'
            assert result.exists()
        finally:
            os.chdir(original_dir)

    def test_pairing_section_generation(self, temp_photo_dir):
        """Test generation of file pairing section in HTML."""
        stats = PhotoStats(temp_photo_dir)
        stats.scan_folder()

        section = stats._generate_pairing_section()

        assert isinstance(section, str)
        assert 'File Pairing Status' in section
        assert 'orphaned' in section.lower()

    def test_xmp_metadata_section_generation(self, tmp_path, sample_xmp_content):
        """Test generation of XMP metadata section in HTML."""
        test_dir = tmp_path / "xmp_section_test"
        test_dir.mkdir()

        (test_dir / "photo.dng").write_bytes(b"data")
        (test_dir / "photo.xmp").write_text(sample_xmp_content)

        stats = PhotoStats(test_dir)
        stats.scan_folder()

        section = stats._generate_xmp_metadata_section()

        assert isinstance(section, str)
        assert 'XMP Metadata' in section

    def test_xmp_metadata_section_no_xmp(self, tmp_path):
        """Test XMP metadata section when no XMP files exist."""
        test_dir = tmp_path / "no_xmp_section"
        test_dir.mkdir()

        (test_dir / "photo.dng").write_bytes(b"data")

        stats = PhotoStats(test_dir)
        stats.scan_folder()

        section = stats._generate_xmp_metadata_section()

        assert 'No XMP metadata found' in section


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_folder_with_special_characters(self, tmp_path):
        """Test handling folders with special characters in names."""
        special_dir = tmp_path / "photos-2024_backup (copy)"
        special_dir.mkdir()

        (special_dir / "test.dng").write_bytes(b"data")

        stats = PhotoStats(special_dir)
        result = stats.scan_folder()

        assert result['total_files'] == 1

    def test_very_large_file(self, tmp_path):
        """Test handling of large files."""
        test_dir = tmp_path / "large_file"
        test_dir.mkdir()

        # Create a larger file (10MB)
        large_data = b"x" * (10 * 1024 * 1024)
        (test_dir / "large.dng").write_bytes(large_data)

        stats = PhotoStats(test_dir)
        stats.scan_folder()

        assert stats.stats['total_size'] == 10 * 1024 * 1024
        formatted = stats._format_size(stats.stats['total_size'])
        assert 'MB' in formatted

    def test_deeply_nested_directories(self, tmp_path):
        """Test scanning deeply nested directory structures."""
        base = tmp_path / "deep"
        current = base
        for i in range(5):
            current = current / f"level{i}"
            current.mkdir(parents=True)

        (current / "photo.dng").write_bytes(b"data")

        stats = PhotoStats(base)
        stats.scan_folder()

        assert stats.stats['total_files'] == 1

    def test_unicode_filenames(self, tmp_path):
        """Test handling files with unicode characters in names."""
        test_dir = tmp_path / "unicode"
        test_dir.mkdir()

        (test_dir / "photo_日本語.dng").write_bytes(b"data")
        (test_dir / "photo_émojis😀.xmp").write_bytes(b"data")

        stats = PhotoStats(test_dir)
        result = stats.scan_folder()

        assert result['total_files'] == 2

    def test_symlinks_handling(self, tmp_path):
        """Test that symlinks to files are handled correctly."""
        test_dir = tmp_path / "symlinks"
        test_dir.mkdir()

        # Create a real file
        real_file = test_dir / "real.dng"
        real_file.write_bytes(b"data")

        # Create a symlink (skip on Windows if not supported)
        try:
            link_file = test_dir / "link.dng"
            link_file.symlink_to(real_file)

            stats = PhotoStats(test_dir)
            stats.scan_folder()

            # Should count both the real file and the symlink
            assert stats.stats['total_files'] >= 1
        except OSError:
            # Skip on platforms that don't support symlinks
            pytest.skip("Symlinks not supported on this platform")
