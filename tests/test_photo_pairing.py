"""
Tests for Photo Pairing Tool

This module tests the photo pairing functionality including:
- Filename validation and parsing
- File grouping and ImageGroup building
- Cache operations
- Analytics calculations
- HTML report generation
"""

import pytest
import json
import tempfile
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from utils.filename_parser import FilenameParser
from utils.config_manager import PhotoAdminConfig
import photo_pairing


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_valid_filenames():
    """Sample valid filenames for testing."""
    return [
        'AB3D0001.dng',
        'XYZW0035.tiff',
        'AB3D0042.cr3',
        'R5M21234.DNG',  # uppercase extension
        'AB3D0001-HDR.dng',
        'AB3D0001-2.dng',
        'AB3D0001-HDR-BW.dng',
        'AB3D0001-2-HDR.dng',
        'XYZW0001-Focus Stack.tiff',
        'AB3D0001-Test_File.dng',
    ]


@pytest.fixture
def sample_invalid_filenames():
    """Sample invalid filenames with expected error reasons."""
    return [
        ('ab3d0001.dng', 'Camera ID must be uppercase alphanumeric [A-Z0-9]'),
        ('AB3D0000.dng', 'Counter cannot be 0000 - must be 0001-9999'),
        ('AB3D001.dng', 'Counter must be 4 digits'),
        ('AB3D0001-.dng', 'Empty property name detected'),
        ('AB3D0001--HDR.dng', 'Empty property name detected'),
        ('AB3D0001-HDR-.dng', 'Empty property name detected'),
        ('AB3D0001-@#$.dng', 'Invalid characters in property name'),
    ]


@pytest.fixture
def sample_imagegroups():
    """Sample ImageGroup structure for testing."""
    return [
        {
            'group_id': 'AB3D0001',
            'camera_id': 'AB3D',
            'counter': '0001',
            'separate_images': {
                '': {  # Base image
                    'files': ['AB3D0001.dng', 'AB3D0001.xmp'],
                    'properties': []
                },
                '2': {  # Separate image #2
                    'files': ['AB3D0001-2.cr3'],
                    'properties': ['HDR']
                }
            }
        },
        {
            'group_id': 'XYZW0035',
            'camera_id': 'XYZW',
            'counter': '0035',
            'separate_images': {
                '': {
                    'files': ['XYZW0035-HDR.tiff'],
                    'properties': ['HDR']
                }
            }
        }
    ]


@pytest.fixture
def temp_photo_folder(tmp_path):
    """Create a temporary folder with test photo files."""
    photo_dir = tmp_path / "test_photos"
    photo_dir.mkdir()

    # Create sample files
    files = [
        'AB3D0001.dng',
        'AB3D0001.xmp',
        'AB3D0001-2.cr3',
        'AB3D0001-2-HDR.tiff',
        'XYZW0035.dng',
        'XYZW0035-HDR.tiff',
        'invalid_file.dng',  # Invalid filename
    ]

    for filename in files:
        (photo_dir / filename).write_bytes(b"fake data")

    return photo_dir


@pytest.fixture
def temp_config(tmp_path):
    """Create a temporary config file for testing."""
    config_content = """photo_extensions:
  - .dng
  - .cr3
  - .tiff
metadata_extensions:
  - .xmp
camera_mappings:
  AB3D:
    - name: Canon EOS R5
      serial_number: 12345
  XYZW:
    - name: Sony A7R5
      serial_number: 67890
processing_methods:
  HDR: High Dynamic Range
  BW: Black and White
"""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(config_content)
    return config_file


# =============================================================================
# T044: Tests for Filename Validation
# =============================================================================

class TestFilenameValidation:
    """Tests for FilenameParser.validate_filename()"""

    def test_valid_filenames(self, sample_valid_filenames):
        """Test that valid filenames pass validation."""
        for filename in sample_valid_filenames:
            is_valid, error_reason = FilenameParser.validate_filename(filename)
            assert is_valid, f"Expected {filename} to be valid, got error: {error_reason}"
            assert error_reason is None

    def test_invalid_filenames(self, sample_invalid_filenames):
        """Test that invalid filenames fail validation with correct reasons."""
        for filename, expected_reason in sample_invalid_filenames:
            is_valid, error_reason = FilenameParser.validate_filename(filename)
            assert not is_valid, f"Expected {filename} to be invalid"
            if expected_reason:
                assert error_reason == expected_reason, \
                    f"For {filename}, expected '{expected_reason}', got '{error_reason}'"

    def test_lowercase_camera_id(self):
        """Test that lowercase camera IDs are rejected."""
        is_valid, error = FilenameParser.validate_filename('ab3d0001.dng')
        assert not is_valid
        assert 'uppercase' in error.lower()

    def test_counter_zero(self):
        """Test that counter 0000 is rejected."""
        is_valid, error = FilenameParser.validate_filename('AB3D0000.dng')
        assert not is_valid
        assert '0000' in error

    def test_empty_property(self):
        """Test that empty properties are rejected."""
        # Trailing dash
        is_valid, error = FilenameParser.validate_filename('AB3D0001-.dng')
        assert not is_valid
        assert 'Empty property' in error

        # Double dash
        is_valid, error = FilenameParser.validate_filename('AB3D0001--HDR.dng')
        assert not is_valid
        assert 'Empty property' in error


# =============================================================================
# T045: Tests for Filename Parsing
# =============================================================================

class TestFilenameParsing:
    """Tests for FilenameParser.parse_filename()"""

    def test_parse_basic_filename(self):
        """Test parsing a basic filename without properties."""
        result = FilenameParser.parse_filename('AB3D0001.dng')
        assert result == {
            'camera_id': 'AB3D',
            'counter': '0001',
            'properties': [],
            'extension': '.dng'
        }

    def test_parse_with_single_property(self):
        """Test parsing filename with one property."""
        result = FilenameParser.parse_filename('AB3D0001-HDR.dng')
        assert result['camera_id'] == 'AB3D'
        assert result['counter'] == '0001'
        assert result['properties'] == ['HDR']
        assert result['extension'] == '.dng'

    def test_parse_with_multiple_properties(self):
        """Test parsing filename with multiple properties."""
        result = FilenameParser.parse_filename('AB3D0001-HDR-BW.dng')
        assert result['properties'] == ['HDR', 'BW']

    def test_parse_with_numeric_property(self):
        """Test parsing filename with numeric property (separate image)."""
        result = FilenameParser.parse_filename('AB3D0001-2.dng')
        assert result['properties'] == ['2']

    def test_parse_with_mixed_properties(self):
        """Test parsing filename with numeric and alphanumeric properties."""
        result = FilenameParser.parse_filename('AB3D0001-2-HDR.dng')
        assert result['properties'] == ['2', 'HDR']

    def test_parse_case_insensitive_extension(self):
        """Test that extensions are parsed regardless of case."""
        result = FilenameParser.parse_filename('AB3D0001.DNG')
        assert result['extension'] == '.DNG'

    def test_parse_with_spaces_in_property(self):
        """Test parsing property with spaces."""
        result = FilenameParser.parse_filename('AB3D0001-Focus Stack.tiff')
        assert result['properties'] == ['Focus Stack']

    def test_parse_with_underscores(self):
        """Test parsing property with underscores."""
        result = FilenameParser.parse_filename('AB3D0001-HDR_BW.dng')
        assert result['properties'] == ['HDR_BW']

    def test_parse_invalid_filename_returns_none(self):
        """Test that parsing invalid filename returns None."""
        result = FilenameParser.parse_filename('invalid.dng')
        assert result is None


# =============================================================================
# T046: Tests for Property Type Detection
# =============================================================================

class TestPropertyTypeDetection:
    """Tests for FilenameParser.detect_property_type()"""

    def test_numeric_property_is_separate_image(self):
        """Test that numeric properties are detected as separate images."""
        assert FilenameParser.detect_property_type('2') == 'separate_image'
        assert FilenameParser.detect_property_type('10') == 'separate_image'
        assert FilenameParser.detect_property_type('999') == 'separate_image'

    def test_alphanumeric_property_is_processing_method(self):
        """Test that alphanumeric properties are processing methods."""
        assert FilenameParser.detect_property_type('HDR') == 'processing_method'
        assert FilenameParser.detect_property_type('BW') == 'processing_method'
        assert FilenameParser.detect_property_type('Focus Stack') == 'processing_method'

    def test_mixed_property_is_processing_method(self):
        """Test that mixed alphanumeric properties are processing methods."""
        assert FilenameParser.detect_property_type('HDR2') == 'processing_method'
        assert FilenameParser.detect_property_type('2X') == 'processing_method'


# =============================================================================
# T047-T050: Tests for File Grouping and ImageGroup Building
# =============================================================================

class TestImageGroupBuilding:
    """Tests for build_imagegroups() function"""

    def test_group_files_by_8char_prefix(self, temp_photo_folder):
        """Test that files are grouped by 8-character prefix."""
        files = list(temp_photo_folder.glob('*.dng'))
        result = photo_pairing.build_imagegroups(files, temp_photo_folder)

        imagegroups = result['imagegroups']
        group_ids = [g['group_id'] for g in imagegroups]

        assert 'AB3D0001' in group_ids
        assert 'XYZW0035' in group_ids

    def test_separate_images_structure(self, temp_photo_folder):
        """Test that separate_images structure is built correctly."""
        files = list(temp_photo_folder.rglob('AB3D0001*'))
        result = photo_pairing.build_imagegroups(files, temp_photo_folder)

        imagegroups = result['imagegroups']
        ab3d_group = next(g for g in imagegroups if g['group_id'] == 'AB3D0001')

        # Should have base image ('') and separate image ('2')
        assert '' in ab3d_group['separate_images']
        assert '2' in ab3d_group['separate_images']

    def test_duplicate_property_deduplication(self, tmp_path):
        """Test that duplicate properties in same separate image are deduplicated."""
        test_folder = tmp_path / "test"
        test_folder.mkdir()

        # Create files with same properties
        (test_folder / 'AB3D0001-HDR.dng').write_bytes(b"data")
        (test_folder / 'AB3D0001-HDR.cr3').write_bytes(b"data")

        files = list(test_folder.glob('*'))
        result = photo_pairing.build_imagegroups(files, test_folder)

        group = result['imagegroups'][0]
        base_image = group['separate_images']['']

        # Property 'HDR' should appear only once
        assert base_image['properties'] == ['HDR']
        assert len(base_image['files']) == 2

    def test_empty_property_detection(self):
        """Test that filenames with empty properties are marked invalid."""
        # This is tested through validation, empty properties should be caught
        is_valid, error = FilenameParser.validate_filename('AB3D0001-.dng')
        assert not is_valid
        assert 'Empty property' in error

    def test_invalid_files_are_tracked(self, temp_photo_folder):
        """Test that invalid files are tracked with reasons."""
        files = list(temp_photo_folder.rglob('*'))
        result = photo_pairing.build_imagegroups(files, temp_photo_folder)

        invalid_files = result['invalid_files']

        # 'invalid_file.dng' should be in invalid files
        invalid_names = [f['filename'] for f in invalid_files]
        assert 'invalid_file.dng' in invalid_names

        # Check that reason is provided
        invalid_entry = next(f for f in invalid_files if f['filename'] == 'invalid_file.dng')
        assert invalid_entry['reason'] is not None
        assert len(invalid_entry['reason']) > 0


# =============================================================================
# T054: Tests for Hash Calculations
# =============================================================================

class TestHashCalculations:
    """Tests for hash calculation functions"""

    def test_file_list_hash_consistency(self, tmp_path):
        """Test that file list hash is consistent for same files."""
        test_folder = tmp_path / "test"
        test_folder.mkdir()

        # Create test files
        (test_folder / 'AB3D0001.dng').write_bytes(b"data1")
        (test_folder / 'AB3D0002.dng').write_bytes(b"data2")

        extensions = {'.dng'}

        hash1 = photo_pairing.calculate_file_list_hash(test_folder, extensions)
        hash2 = photo_pairing.calculate_file_list_hash(test_folder, extensions)

        assert hash1 == hash2

    def test_file_list_hash_changes_with_new_file(self, tmp_path):
        """Test that file list hash changes when files are added."""
        test_folder = tmp_path / "test"
        test_folder.mkdir()

        (test_folder / 'AB3D0001.dng').write_bytes(b"data1")

        extensions = {'.dng'}
        hash1 = photo_pairing.calculate_file_list_hash(test_folder, extensions)

        # Add a new file
        (test_folder / 'AB3D0002.dng').write_bytes(b"data2")
        hash2 = photo_pairing.calculate_file_list_hash(test_folder, extensions)

        assert hash1 != hash2

    def test_imagegroups_hash_consistency(self, sample_imagegroups):
        """Test that imagegroups hash is consistent."""
        hash1 = photo_pairing.calculate_imagegroups_hash(sample_imagegroups)
        hash2 = photo_pairing.calculate_imagegroups_hash(sample_imagegroups)

        assert hash1 == hash2

    def test_imagegroups_hash_changes_with_modification(self, sample_imagegroups):
        """Test that imagegroups hash changes when data is modified."""
        import copy

        hash1 = photo_pairing.calculate_imagegroups_hash(sample_imagegroups)

        # Modify the data
        modified = copy.deepcopy(sample_imagegroups)
        modified[0]['separate_images']['']['files'].append('new_file.dng')

        hash2 = photo_pairing.calculate_imagegroups_hash(modified)

        assert hash1 != hash2


# =============================================================================
# T055-T056: Tests for Cache Operations
# =============================================================================

class TestCacheOperations:
    """Tests for cache save/load/validation"""

    def test_cache_save_and_load_roundtrip(self, tmp_path, sample_imagegroups):
        """Test that cache can be saved and loaded correctly."""
        test_folder = tmp_path / "test"
        test_folder.mkdir()

        invalid_files = [{'filename': 'bad.dng', 'path': 'bad.dng', 'reason': 'Invalid'}]
        file_list_hash = 'abc123'

        # Save cache
        success = photo_pairing.save_cache(
            test_folder,
            sample_imagegroups,
            invalid_files,
            file_list_hash
        )
        assert success

        # Load cache
        loaded = photo_pairing.load_cache(test_folder)

        assert loaded is not None
        assert loaded['imagegroups'] == sample_imagegroups
        assert loaded['invalid_files'] == invalid_files
        assert loaded['metadata']['file_list_hash'] == file_list_hash

    def test_cache_validation_valid_cache(self, tmp_path, sample_imagegroups):
        """Test cache validation with valid cache."""
        test_folder = tmp_path / "test"
        test_folder.mkdir()

        file_list_hash = 'abc123'
        photo_pairing.save_cache(test_folder, sample_imagegroups, [], file_list_hash)

        cache_data = photo_pairing.load_cache(test_folder)
        validation = photo_pairing.validate_cache(cache_data, file_list_hash)

        assert validation['valid']
        assert not validation['folder_changed']
        assert not validation['cache_edited']

    def test_cache_validation_folder_changed(self, tmp_path, sample_imagegroups):
        """Test cache validation detects folder changes."""
        test_folder = tmp_path / "test"
        test_folder.mkdir()

        old_hash = 'abc123'
        new_hash = 'def456'

        photo_pairing.save_cache(test_folder, sample_imagegroups, [], old_hash)
        cache_data = photo_pairing.load_cache(test_folder)

        validation = photo_pairing.validate_cache(cache_data, new_hash)

        assert not validation['valid']
        assert validation['folder_changed']

    def test_cache_validation_cache_edited(self, tmp_path, sample_imagegroups):
        """Test cache validation detects manual cache edits."""
        test_folder = tmp_path / "test"
        test_folder.mkdir()

        file_list_hash = 'abc123'
        photo_pairing.save_cache(test_folder, sample_imagegroups, [], file_list_hash)

        # Manually edit cache
        cache_path = test_folder / '.photo_pairing_imagegroups'
        cache_data = json.loads(cache_path.read_text())
        cache_data['imagegroups'][0]['group_id'] = 'MODIFIED'
        cache_path.write_text(json.dumps(cache_data))

        # Reload and validate
        loaded = photo_pairing.load_cache(test_folder)
        validation = photo_pairing.validate_cache(loaded, file_list_hash)

        assert not validation['valid']
        assert validation['cache_edited']

    def test_load_cache_missing_file(self, tmp_path):
        """Test loading cache when file doesn't exist."""
        test_folder = tmp_path / "test"
        test_folder.mkdir()

        loaded = photo_pairing.load_cache(test_folder)
        assert loaded is None

    def test_load_cache_corrupted_json(self, tmp_path):
        """Test loading cache with corrupted JSON."""
        test_folder = tmp_path / "test"
        test_folder.mkdir()

        cache_path = test_folder / '.photo_pairing_imagegroups'
        cache_path.write_text('{ invalid json }')

        loaded = photo_pairing.load_cache(test_folder)
        assert loaded is None


# =============================================================================
# T057: Tests for Analytics Calculations
# =============================================================================

class TestAnalyticsCalculations:
    """Tests for calculate_analytics() function"""

    def test_camera_usage_calculation(self, sample_imagegroups):
        """Test that camera usage is calculated correctly."""
        camera_mappings = {
            'AB3D': [{'name': 'Canon EOS R5', 'serial_number': '12345'}],
            'XYZW': [{'name': 'Sony A7R5', 'serial_number': '67890'}]
        }
        processing_methods = {'HDR': 'High Dynamic Range'}

        analytics = photo_pairing.calculate_analytics(
            sample_imagegroups,
            camera_mappings,
            processing_methods
        )

        camera_usage = analytics['camera_usage']

        assert 'AB3D' in camera_usage
        assert 'XYZW' in camera_usage

        assert camera_usage['AB3D']['name'] == 'Canon EOS R5'
        assert camera_usage['AB3D']['group_count'] == 1
        assert camera_usage['AB3D']['image_count'] == 2  # Base + separate image #2

    def test_method_usage_calculation(self, sample_imagegroups):
        """Test that processing method usage is calculated correctly."""
        camera_mappings = {}
        processing_methods = {'HDR': 'High Dynamic Range'}

        analytics = photo_pairing.calculate_analytics(
            sample_imagegroups,
            camera_mappings,
            processing_methods
        )

        method_usage = analytics['method_usage']

        assert 'HDR' in method_usage
        assert method_usage['HDR']['description'] == 'High Dynamic Range'
        assert method_usage['HDR']['image_count'] == 2  # One in each group

    def test_statistics_calculation(self, sample_imagegroups):
        """Test that report statistics are calculated correctly."""
        camera_mappings = {}
        processing_methods = {}

        analytics = photo_pairing.calculate_analytics(
            sample_imagegroups,
            camera_mappings,
            processing_methods
        )

        stats = analytics['statistics']

        assert stats['total_groups'] == 2
        assert stats['total_images'] == 3  # AB3D has 2, XYZW has 1
        assert stats['total_files_scanned'] == 4  # Count all files
        assert stats['cameras_used'] == 2
        assert stats['processing_methods_used'] == 1


# =============================================================================
# T058: Tests for HTML Report Generation
# =============================================================================

class TestHTMLReportGeneration:
    """Tests for generate_html_report() function"""

    def test_html_report_structure(self, tmp_path, sample_imagegroups):
        """Test that HTML report has correct structure with template-based rendering."""
        analytics = {
            'camera_usage': {
                'AB3D': {'name': 'Canon EOS R5', 'serial_number': '12345', 'group_count': 1, 'image_count': 2}
            },
            'method_usage': {
                'HDR': {'description': 'High Dynamic Range', 'image_count': 1}
            },
            'statistics': {
                'total_groups': 2,
                'total_images': 3,
                'total_files_scanned': 4,
                'avg_files_per_group': 2.0,
                'max_files_per_group': 3,
                'cameras_used': 1,
                'processing_methods_used': 1
            }
        }

        invalid_files = [{'filename': 'bad.dng', 'reason': 'Invalid format'}]
        report_path = tmp_path / "report.html"
        folder_path = Path("/test/folder")
        scan_duration = 1.5

        photo_pairing.generate_html_report(
            analytics,
            invalid_files,
            report_path,
            folder_path,
            scan_duration
        )

        assert report_path.exists()

        html_content = report_path.read_text(encoding='utf-8')

        # Check key sections exist
        assert '<!DOCTYPE html>' in html_content
        assert 'Photo Pairing' in html_content

        # Check template-based styling elements
        assert 'kpi-card' in html_content
        assert 'section-title' in html_content
        assert 'chart-container' in html_content

        # Check CSS color variables from base template
        assert '--color-primary' in html_content
        assert '--color-success' in html_content
        assert '--gradient-purple' in html_content

        # Check statistics are included
        assert 'Canon EOS R5' in html_content
        assert 'High Dynamic Range' in html_content
        assert 'bad.dng' in html_content

        # Check Chart.js is included
        assert 'chart.js' in html_content.lower()
        assert 'CHART_COLORS' in html_content

    def test_html_report_no_invalid_files(self, tmp_path):
        """Test HTML report when there are no invalid files (template-based)."""
        analytics = {
            'camera_usage': {},
            'method_usage': {},
            'statistics': {
                'total_groups': 0,
                'total_images': 0,
                'total_files_scanned': 0,
                'avg_files_per_group': 0,
                'max_files_per_group': 0,
                'cameras_used': 0,
                'processing_methods_used': 0
            }
        }

        report_path = tmp_path / "report.html"

        photo_pairing.generate_html_report(
            analytics,
            [],  # No invalid files
            report_path,
            Path("/test"),
            1.0
        )

        html_content = report_path.read_text(encoding='utf-8')

        # With no invalid files, the Invalid Files KPI should show 0 with success status
        assert 'Invalid Files' in html_content
        assert 'kpi-card success' in html_content  # Success status for 0 invalid files

        # Should not have any warnings section (empty warnings)
        assert '<div class="warnings-section">' not in html_content or 'Warnings</h2>' not in html_content


# =============================================================================
# T059-T061: Integration Tests
# =============================================================================

class TestIntegrationWorkflows:
    """Integration tests for complete workflows"""

    def test_first_run_workflow(self, tmp_path, monkeypatch):
        """
        T059: Test complete first-run workflow
        - No cache exists
        - Files are scanned and analyzed
        - User is prompted for camera/method info
        - HTML report is generated
        - Cache is saved
        """
        # Create test folder with photos
        test_folder = tmp_path / "photos"
        test_folder.mkdir()

        (test_folder / 'AB3D0001.dng').write_bytes(b"data")
        (test_folder / 'AB3D0001-HDR.dng').write_bytes(b"data")
        (test_folder / 'XYZW0100.cr3').write_bytes(b"data")

        # Create config
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_content = """photo_extensions:
  - .dng
  - .cr3
metadata_extensions:
  - .xmp
camera_mappings: {}
processing_methods: {}
"""
        config_file.write_text(config_content)

        # Mock user input for camera and method prompts
        inputs = iter([
            'Canon R5',  # Camera name for AB3D
            '12345',     # Serial for AB3D
            'Sony A7',   # Camera name for XYZW
            '67890',     # Serial for XYZW
            'High Dynamic Range'  # Method description for HDR
        ])

        def mock_input(prompt):
            return next(inputs)

        monkeypatch.setattr('builtins.input', mock_input)

        # Patch PhotoAdminConfig to use our test config
        from utils.config_manager import PhotoAdminConfig
        original_init = PhotoAdminConfig.__init__

        def patched_init(self, config_path=None):
            original_init(self, config_file)

        monkeypatch.setattr(PhotoAdminConfig, '__init__', patched_init)

        # Change to test directory
        monkeypatch.setattr('pathlib.Path.cwd', lambda: tmp_path)

        # Run the analysis (simulate calling main functions)
        from utils.config_manager import PhotoAdminConfig
        config = PhotoAdminConfig()

        # Scan files
        files = list(photo_pairing.scan_folder(test_folder, config.photo_extensions))
        assert len(files) == 3

        # Build imagegroups
        result = photo_pairing.build_imagegroups(files, test_folder)
        assert len(result['imagegroups']) == 2
        assert len(result['invalid_files']) == 0

        # Ensure camera/method mappings (simulates prompting)
        camera_ids = {'AB3D', 'XYZW'}
        for camera_id in sorted(camera_ids):
            if camera_id not in config.camera_mappings:
                info = config.ensure_camera_mapping(camera_id)
                assert info is not None

        methods = {'HDR'}
        for method in sorted(methods):
            if method not in config.processing_methods:
                desc = config.ensure_processing_method(method)
                assert desc is not None

        # Reload config
        config.reload()

        # Calculate analytics
        analytics = photo_pairing.calculate_analytics(
            result['imagegroups'],
            config.camera_mappings,
            config.processing_methods
        )

        assert analytics['statistics']['total_groups'] == 2
        assert 'AB3D' in analytics['camera_usage']
        assert 'HDR' in analytics['method_usage']

        # Generate report
        report_path = tmp_path / "report.html"
        photo_pairing.generate_html_report(
            analytics,
            result['invalid_files'],
            report_path,
            test_folder,
            1.5
        )

        assert report_path.exists()

        # Save cache
        file_list_hash = photo_pairing.calculate_file_list_hash(test_folder, config.photo_extensions)
        success = photo_pairing.save_cache(
            test_folder,
            result['imagegroups'],
            result['invalid_files'],
            file_list_hash
        )

        assert success
        assert (test_folder / '.photo_pairing_imagegroups').exists()

    def test_cached_analysis_workflow(self, tmp_path):
        """
        T060: Test workflow with valid cache
        - Cache exists and is valid
        - No file scanning needed
        - Cache data is used directly
        - Report is generated from cache
        """
        # Create test folder
        test_folder = tmp_path / "photos"
        test_folder.mkdir()

        (test_folder / 'AB3D0001.dng').write_bytes(b"data")
        (test_folder / 'AB3D0001-HDR.dng').write_bytes(b"data")

        # Create imagegroups and save to cache
        imagegroups = [
            {
                'group_id': 'AB3D0001',
                'camera_id': 'AB3D',
                'counter': '0001',
                'separate_images': {
                    '': {
                        'files': ['AB3D0001.dng', 'AB3D0001-HDR.dng'],
                        'properties': ['HDR']
                    }
                }
            }
        ]

        file_list_hash = photo_pairing.calculate_file_list_hash(test_folder, {'.dng'})
        photo_pairing.save_cache(test_folder, imagegroups, [], file_list_hash)

        # Load cache
        cache_data = photo_pairing.load_cache(test_folder)
        assert cache_data is not None

        # Validate cache
        validation = photo_pairing.validate_cache(cache_data, file_list_hash)
        assert validation['valid']
        assert not validation['folder_changed']
        assert not validation['cache_edited']

        # Use cached data
        result = {
            'imagegroups': cache_data['imagegroups'],
            'invalid_files': cache_data.get('invalid_files', [])
        }

        assert len(result['imagegroups']) == 1
        assert result['imagegroups'][0]['group_id'] == 'AB3D0001'

    def test_stale_cache_handling(self, tmp_path, monkeypatch):
        """
        T061: Test workflow when cache is stale
        - Cache exists but folder content changed
        - User is prompted for action
        - User chooses to re-analyze
        - Fresh analysis is performed
        """
        # Create test folder with initial files
        test_folder = tmp_path / "photos"
        test_folder.mkdir()

        (test_folder / 'AB3D0001.dng').write_bytes(b"data1")

        # Create and save initial cache
        imagegroups = [
            {
                'group_id': 'AB3D0001',
                'camera_id': 'AB3D',
                'counter': '0001',
                'separate_images': {
                    '': {
                        'files': ['AB3D0001.dng'],
                        'properties': []
                    }
                }
            }
        ]

        old_hash = photo_pairing.calculate_file_list_hash(test_folder, {'.dng'})
        photo_pairing.save_cache(test_folder, imagegroups, [], old_hash)

        # Add a new file (folder content changes)
        (test_folder / 'AB3D0002.dng').write_bytes(b"data2")

        # Calculate new hash
        new_hash = photo_pairing.calculate_file_list_hash(test_folder, {'.dng'})

        # Load cache
        cache_data = photo_pairing.load_cache(test_folder)
        assert cache_data is not None

        # Validate cache - should be invalid due to folder change
        validation = photo_pairing.validate_cache(cache_data, new_hash)
        assert not validation['valid']
        assert validation['folder_changed']

        # Mock user choosing to re-analyze
        monkeypatch.setattr('builtins.input', lambda prompt: 'b')

        action = photo_pairing.prompt_cache_action(
            validation['folder_changed'],
            validation['cache_edited']
        )

        assert action == 're_analyze'

        # Perform fresh scan (simulated)
        files = list(photo_pairing.scan_folder(test_folder, {'.dng'}))
        assert len(files) == 2  # Now we have 2 files

        result = photo_pairing.build_imagegroups(files, test_folder)
        assert len(result['imagegroups']) == 2  # 2 groups now


# =============================================================================
# Run tests
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])


# =============================================================================
# Help Text Tests (T029-T032)
# =============================================================================

class TestHelpText:
    """Tests for command-line help text."""

    def test_help_flag_displays_help_and_exits_zero(self):
        """Test that --help displays help text and exits with code 0."""
        result = subprocess.run(
            [sys.executable, 'photo_pairing.py', '--help'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'Photo Pairing' in result.stdout
        assert 'usage:' in result.stdout

    def test_h_flag_works_identically(self):
        """Test that -h flag works identically to --help."""
        help_result = subprocess.run(
            [sys.executable, 'photo_pairing.py', '--help'],
            capture_output=True,
            text=True
        )
        
        h_result = subprocess.run(
            [sys.executable, 'photo_pairing.py', '-h'],
            capture_output=True,
            text=True
        )
        
        assert h_result.returncode == 0
        assert h_result.stdout == help_result.stdout

    def test_help_contains_required_elements(self):
        """Test that help text contains description, usage examples, and config notes."""
        result = subprocess.run(
            [sys.executable, 'photo_pairing.py', '--help'],
            capture_output=True,
            text=True
        )
        
        help_text = result.stdout
        
        # Check for description
        assert 'Photo Pairing' in help_text
        assert 'filename patterns' in help_text
        
        # Check for usage examples
        assert 'Examples:' in help_text
        assert '/path/to/photos' in help_text
        
        # Check for configuration notes
        assert 'Configuration:' in help_text
        assert 'config/config.yaml' in help_text
        assert 'template-config.yaml' in help_text
        
        # Check for report output information
        assert 'Report Output:' in help_text
        assert 'photo_pairing_report' in help_text
        
        # Check for "How It Works" section
        assert 'How It Works:' in help_text
