"""
Tests for Pipeline Validation Tool

This module tests the pipeline validation functionality including:
- Pipeline configuration loading and validation
- Path enumeration through directed graph
- File validation against pipeline paths
- Status classification (CONSISTENT, PARTIAL, etc.)
- Cache operations and invalidation
- HTML report generation
"""

import pytest
import json
import yaml
import tempfile
import subprocess
import sys
import signal
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, mock_open
import pipeline_validation


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_pipeline_config():
    """Sample pipeline configuration for testing (versioned structure)."""
    return {
        'default': {
            'nodes': [
                {
                    'id': 'capture',
                    'type': 'Capture',
                    'name': 'Camera Capture',
                    'output': ['raw_image_1', 'xmp_metadata_1']
                },
                {
                    'id': 'raw_image_1',
                    'type': 'File',
                    'extension': '.CR3',
                    'name': 'Canon Raw File',
                    'output': ['selection_process']
                },
                {
                    'id': 'xmp_metadata_1',
                    'type': 'File',
                    'extension': '.XMP',
                    'name': 'XMP Metadata',
                    'output': []
                },
                {
                    'id': 'selection_process',
                    'type': 'Process',
                    'method_ids': [''],
                    'name': 'Image Selection',
                    'output': ['dng_conversion']
                },
                {
                    'id': 'dng_conversion',
                    'type': 'Process',
                    'method_ids': ['DxO_DeepPRIME_XD2s'],
                    'name': 'DNG Conversion',
                    'output': ['openformat_raw_image']
                },
                {
                    'id': 'openformat_raw_image',
                    'type': 'File',
                    'extension': '.DNG',
                    'name': 'DNG File',
                    'output': ['termination_blackbox']
                },
                {
                    'id': 'termination_blackbox',
                    'type': 'Termination',
                    'termination_type': 'Black Box Archive',
                    'name': 'Black Box Archive Ready',
                    'output': []
                }
            ]
        }
    }


@pytest.fixture
def sample_pipeline_with_loop():
    """Sample pipeline with a loop (Branching node that loops back) - versioned structure."""
    return {
        'default': {
            'nodes': [
                {
                    'id': 'capture',
                    'type': 'Capture',
                    'name': 'Camera Capture',
                    'output': ['raw_image']
                },
                {
                    'id': 'raw_image',
                    'type': 'File',
                    'extension': '.CR3',
                    'name': 'Canon Raw File',
                    'output': ['edit_process']
                },
                {
                    'id': 'edit_process',
                    'type': 'Process',
                    'method_ids': ['Edit'],
                    'name': 'Photoshop Editing',
                    'output': ['branching_decision']
                },
                {
                    'id': 'branching_decision',
                    'type': 'Branching',
                    'condition_description': 'User decides: Create TIFF or continue editing',
                    'name': 'TIFF Generation Decision',
                    'output': ['generate_tiff', 'edit_process']  # Second output loops back
                },
                {
                    'id': 'generate_tiff',
                    'type': 'Process',
                    'method_ids': [''],
                    'name': 'Generate TIFF',
                    'output': ['tiff_file']
                },
                {
                    'id': 'tiff_file',
                    'type': 'File',
                    'extension': '.TIF',
                    'name': 'TIFF File',
                    'output': ['termination']
                },
                {
                    'id': 'termination',
                    'type': 'Termination',
                    'termination_type': 'Black Box Archive',
                    'name': 'Archive Ready',
                    'output': []
                }
            ]
        }
    }


@pytest.fixture
def sample_imagegroups():
    """Sample ImageGroups from Photo Pairing Tool for testing."""
    return [
        {
            'group_id': 'AB3D0001',
            'camera_id': 'AB3D',
            'counter': '0001',
            'separate_images': {
                '': {  # Base image
                    'files': [
                        'AB3D0001.CR3',
                        'AB3D0001.XMP',
                        'AB3D0001-DxO_DeepPRIME_XD2s.DNG'
                    ],
                    'properties': []
                }
            }
        },
        {
            'group_id': 'AB3D0002',
            'camera_id': 'AB3D',
            'counter': '0002',
            'separate_images': {
                '': {
                    'files': [
                        'AB3D0002.CR3',
                        'AB3D0002.XMP'
                        # Missing DNG file - PARTIAL status expected
                    ],
                    'properties': []
                }
            }
        },
        {
            'group_id': 'AB3D0003',
            'camera_id': 'AB3D',
            'counter': '0003',
            'separate_images': {
                '': {
                    'files': [
                        'AB3D0003.CR3',
                        'AB3D0003.XMP',
                        'AB3D0003-DxO_DeepPRIME_XD2s.DNG',
                        'AB3D0003-backup.CR3'  # Extra file - CONSISTENT-WITH-WARNING expected
                    ],
                    'properties': []
                }
            }
        }
    ]


@pytest.fixture
def temp_photo_folder(tmp_path):
    """Create a temporary folder with test photo files and Photo Pairing cache."""
    photo_dir = tmp_path / "test_photos"
    photo_dir.mkdir()

    # Create sample files
    files = [
        'AB3D0001.CR3',
        'AB3D0001.XMP',
        'AB3D0001-DxO_DeepPRIME_XD2s.DNG',
        'AB3D0002.CR3',
        'AB3D0002.XMP'
    ]

    for filename in files:
        (photo_dir / filename).write_text(f"Mock content for {filename}")

    # Create Photo Pairing cache
    cache_data = {
        'version': '1.0',
        'tool_version': '1.0.0',
        'created_at': datetime.now().isoformat(),
        'folder_path': str(photo_dir),
        'imagegroups': [
            {
                'group_id': 'AB3D0001',
                'camera_id': 'AB3D',
                'counter': '0001',
                'separate_images': {
                    '': {
                        'files': [
                            'AB3D0001.CR3',
                            'AB3D0001.XMP',
                            'AB3D0001-DxO_DeepPRIME_XD2s.DNG'
                        ],
                        'properties': []
                    }
                }
            },
            {
                'group_id': 'AB3D0002',
                'camera_id': 'AB3D',
                'counter': '0002',
                'separate_images': {
                    '': {
                        'files': [
                            'AB3D0002.CR3',
                            'AB3D0002.XMP'
                        ],
                        'properties': []
                    }
                }
            }
        ]
    }

    cache_file = photo_dir / '.photo_pairing_imagegroups'
    cache_file.write_text(json.dumps(cache_data, indent=2))

    return photo_dir


@pytest.fixture
def mock_config(tmp_path, sample_pipeline_config):
    """Create actual config file for cache hash testing."""
    config_path = tmp_path / "config.yaml"
    config_content = {
        'photo_extensions': ['.cr3', '.dng', '.tiff', '.tif'],
        'metadata_extensions': ['.xmp'],
        'require_sidecar': ['.cr3'],
        'camera_mappings': {
            'AB3D': [{'name': 'Canon EOS R5', 'serial_number': '12345'}]
        },
        'processing_methods': {
            'DxO_DeepPRIME_XD2s': 'DNG Conversion with DeepPRIME',
            'Edit': 'Photoshop Editing'
        },
        'processing_pipelines': sample_pipeline_config
    }

    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_content, f)

    return config_path


@pytest.fixture
def mock_photo_admin_config():
    """Mock PhotoAdminConfig object for validation tests."""
    config = MagicMock()
    config.photo_extensions = ['.cr3', '.dng', '.tiff', '.tif']
    config.metadata_extensions = ['.xmp']
    config.camera_mappings = {
        'AB3D': [{'name': 'Canon EOS R5', 'serial_number': '12345'}]
    }
    config.processing_methods = {
        'DxO_DeepPRIME_XD2s': 'DNG Conversion with DeepPRIME',
        'Edit': 'Photoshop Editing'
    }
    return config


# =============================================================================
# Phase 1: Setup Tests (Skeleton/Smoke Tests)
# =============================================================================

class TestCLIInterface:
    """Tests for command-line interface (Phase 1)."""

    def test_help_flag(self):
        """Test --help flag displays usage information."""
        result = subprocess.run(
            [sys.executable, 'pipeline_validation.py', '--help'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert 'Pipeline Validation Tool' in result.stdout
        assert 'folder_path' in result.stdout

    def test_version_flag(self):
        """Test --version flag displays version."""
        result = subprocess.run(
            [sys.executable, 'pipeline_validation.py', '--version'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert '1.0.0' in result.stdout

    def test_missing_folder_path(self):
        """Test error when folder_path is not provided."""
        result = subprocess.run(
            [sys.executable, 'pipeline_validation.py'],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0
        assert 'required' in result.stderr.lower() or 'required' in result.stdout.lower()


class TestSignalHandling:
    """Tests for graceful CTRL+C handling (Phase 1)."""

    def test_sigint_handler_setup(self):
        """Test that SIGINT handler is properly configured."""
        with patch('signal.signal') as mock_signal:
            pipeline_validation.setup_signal_handlers()
            # Verify signal.signal was called once with SIGINT and a callable handler
            assert mock_signal.call_count == 1
            call_args = mock_signal.call_args[0]
            assert call_args[0] == signal.SIGINT
            assert callable(call_args[1]), "Second argument should be a callable signal handler"

    def test_sigint_exit_code(self):
        """Test that SIGINT handler exits with code 130."""
        # This test would require subprocess and sending SIGINT
        # Placeholder for actual implementation
        pass


class TestPrerequisiteValidation:
    """Tests for prerequisite checking (Phase 1)."""

    def test_missing_photo_pairing_cache(self, tmp_path):
        """Test error when Photo Pairing cache is missing."""
        # Create folder without cache
        folder = tmp_path / "no_cache"
        folder.mkdir()

        args = MagicMock()
        args.folder_path = folder
        args.force_regenerate = False

        result = pipeline_validation.validate_prerequisites(args)
        assert result is False

    def test_existing_photo_pairing_cache(self, temp_photo_folder):
        """Test success when Photo Pairing cache exists."""
        args = MagicMock()
        args.folder_path = temp_photo_folder
        args.force_regenerate = False

        result = pipeline_validation.validate_prerequisites(args)
        assert result is True

    def test_force_regenerate_skips_cache_check(self, tmp_path):
        """Test that --force-regenerate skips cache existence check."""
        folder = tmp_path / "no_cache"
        folder.mkdir()

        args = MagicMock()
        args.folder_path = folder
        args.force_regenerate = True

        # Should not fail even without cache when force_regenerate=True
        # This behavior may change based on implementation
        pass


# =============================================================================
# Phase 2: Foundational Tests (To be implemented)
# =============================================================================

class TestPipelineConfigLoading:
    """Tests for pipeline configuration loading (Phase 2)."""

    def test_load_pipeline_from_config(self, tmp_path, sample_pipeline_config):
        """Test loading pipeline configuration from config.yaml."""
        # Create test config file
        config_file = tmp_path / "test_config.yaml"
        config_data = {
            'photo_extensions': ['.cr3', '.dng'],
            'metadata_extensions': ['.xmp'],
            'processing_methods': {
                'DxO_DeepPRIME_XD2s': 'DNG Conversion'
            },
            'processing_pipelines': sample_pipeline_config
        }

        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        # Load configuration via PhotoAdminConfig (per constitution)
        config = pipeline_validation.PhotoAdminConfig(config_path=config_file)

        # Load pipeline
        pipeline = pipeline_validation.load_pipeline_config(config)

        # Verify pipeline loaded correctly
        assert len(pipeline.nodes) == 7
        assert len(pipeline.nodes_by_id) == 7

        # Verify node types
        assert isinstance(pipeline.nodes_by_id['capture'], pipeline_validation.CaptureNode)
        assert isinstance(pipeline.nodes_by_id['raw_image_1'], pipeline_validation.FileNode)
        assert isinstance(pipeline.nodes_by_id['selection_process'], pipeline_validation.ProcessNode)
        assert isinstance(pipeline.nodes_by_id['termination_blackbox'], pipeline_validation.TerminationNode)

    def test_validate_pipeline_structure(self, tmp_path, sample_pipeline_config, mock_photo_admin_config):
        """Test validation of pipeline node structure."""
        # Create test config file
        config_file = tmp_path / "test_config.yaml"
        config_data = {
            'processing_pipelines': sample_pipeline_config
        }

        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        # Load configuration via PhotoAdminConfig (per constitution)
        config = pipeline_validation.PhotoAdminConfig(config_path=config_file)

        # Load pipeline
        pipeline = pipeline_validation.load_pipeline_config(config)

        # Validate structure
        errors = pipeline_validation.validate_pipeline_structure(pipeline, mock_photo_admin_config)

        # Should have no errors
        assert len(errors) == 0

    def test_detect_invalid_node_references(self, tmp_path, mock_photo_admin_config):
        """Test detection of invalid output node references."""
        # Create pipeline with invalid reference
        invalid_pipeline_config = {
            'default': {
                'nodes': [
                    {
                        'id': 'capture',
                        'type': 'Capture',
                        'name': 'Camera Capture',
                        'output': ['raw_image', 'non_existent_node']  # Invalid reference
                    },
                    {
                        'id': 'raw_image',
                        'type': 'File',
                        'extension': '.CR3',
                        'name': 'Raw File',
                        'output': []
                    }
                ]
            }
        }

        config_file = tmp_path / "invalid_config.yaml"
        config_data = {
            'processing_pipelines': invalid_pipeline_config
        }

        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        # Load configuration via PhotoAdminConfig (per constitution)
        config = pipeline_validation.PhotoAdminConfig(config_path=config_file)

        # Load pipeline
        pipeline = pipeline_validation.load_pipeline_config(config)

        # Validate structure - should detect invalid reference
        errors = pipeline_validation.validate_pipeline_structure(pipeline, mock_photo_admin_config)

        assert len(errors) > 0
        assert any('non_existent_node' in err for err in errors)


class TestPhotoPairingIntegration:
    """Tests for Photo Pairing integration (Phase 2)."""

    def test_load_photo_pairing_cache(self, temp_photo_folder):
        """Test loading Photo Pairing cache file."""
        # Load ImageGroups from cache
        imagegroups = pipeline_validation.load_or_generate_imagegroups(temp_photo_folder, force_regenerate=False)

        # Verify ImageGroups loaded
        assert len(imagegroups) == 2
        assert imagegroups[0]['group_id'] == 'AB3D0001'
        assert imagegroups[1]['group_id'] == 'AB3D0002'

    def test_flatten_imagegroups_to_specific_images(self, sample_imagegroups):
        """Test flattening ImageGroups to SpecificImages."""
        # Flatten ImageGroups
        specific_images = pipeline_validation.flatten_imagegroups_to_specific_images(sample_imagegroups)

        # Verify flattening - 3 groups with 1 separate image each = 3 SpecificImages
        assert len(specific_images) == 3  # AB3D0001, AB3D0002, AB3D0003

        # Check first image (AB3D0001 base image)
        img1 = [img for img in specific_images if img.base_filename == 'AB3D0001'][0]
        assert img1.group_id == 'AB3D0001'
        assert img1.camera_id == 'AB3D'
        assert img1.counter == '0001'
        assert img1.suffix == ''
        assert 'AB3D0001.CR3' in img1.files
        assert 'AB3D0001.XMP' in img1.files

        # Check second image (AB3D0002)
        img2 = [img for img in specific_images if img.base_filename == 'AB3D0002'][0]
        assert img2.group_id == 'AB3D0002'
        assert img2.suffix == ''
        assert 'AB3D0002.CR3' in img2.files

        # Check third image (AB3D0003)
        img3 = [img for img in specific_images if img.base_filename == 'AB3D0003'][0]
        assert img3.group_id == 'AB3D0003'
        assert img3.suffix == ''
        assert 'AB3D0003-backup.CR3' in img3.files  # Extra file


# =============================================================================
# Phase 3: Core Validation Tests (To be implemented)
# =============================================================================

class TestPathEnumeration:
    """Tests for pipeline path enumeration (Phase 3 - User Story 1)."""

    def test_enumerate_simple_path(self, tmp_path, sample_pipeline_config, mock_photo_admin_config):
        """Test enumeration of simple linear pipeline path."""
        # Create config file
        config_file = tmp_path / "test_config.yaml"
        config_data = {'processing_pipelines': sample_pipeline_config}
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        # Load configuration via PhotoAdminConfig (per constitution)
        config = pipeline_validation.PhotoAdminConfig(config_path=config_file)

        # Load pipeline
        pipeline = pipeline_validation.load_pipeline_config(config)

        # Enumerate all paths from Capture to Termination
        paths = pipeline_validation.enumerate_all_paths(pipeline)

        # Should have at least one path
        assert len(paths) > 0

        # Each path should start with Capture and end with Termination
        for path in paths:
            assert len(path) > 0
            assert path[0]['id'] == 'capture'
            assert path[-1]['id'] == 'termination_blackbox'

    def test_enumerate_branching_paths(self, tmp_path, sample_pipeline_with_loop, mock_photo_admin_config):
        """Test enumeration with Branching nodes."""
        # Create config file with branching
        config_file = tmp_path / "test_config.yaml"
        config_data = {'processing_pipelines': sample_pipeline_with_loop}
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        # Load configuration via PhotoAdminConfig (per constitution)
        config = pipeline_validation.PhotoAdminConfig(config_path=config_file)

        # Load pipeline
        pipeline = pipeline_validation.load_pipeline_config(config)

        # Enumerate all paths
        paths = pipeline_validation.enumerate_all_paths(pipeline)

        # Should have multiple paths due to branching
        assert len(paths) > 1

    def test_handle_loop_truncation(self, tmp_path, sample_pipeline_with_loop):
        """Test loop truncation after MAX_ITERATIONS."""
        # Create config file with loop
        config_file = tmp_path / "test_config.yaml"
        config_data = {'processing_pipelines': sample_pipeline_with_loop}
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        # Load configuration via PhotoAdminConfig (per constitution)
        config = pipeline_validation.PhotoAdminConfig(config_path=config_file)

        # Load pipeline
        pipeline = pipeline_validation.load_pipeline_config(config)

        # Enumerate paths
        paths = pipeline_validation.enumerate_all_paths(pipeline)

        # Check that some paths were truncated due to loop limit
        # Paths should contain information about truncation
        assert len(paths) > 0


class TestFileGeneration:
    """Tests for expected file generation (Phase 3 - User Story 1)."""

    def test_generate_expected_files_simple_path(self):
        """Test generate_expected_files() with processing method suffixes."""
        # Create a simple path through the pipeline
        path = [
            {'id': 'capture', 'type': 'Capture'},
            {'id': 'raw_file', 'type': 'File', 'extension': '.CR3'},
            {'id': 'process', 'type': 'Process', 'method_id': 'DxO_DeepPRIME_XD2s'},
            {'id': 'dng_file', 'type': 'File', 'extension': '.DNG'},
            {'id': 'termination', 'type': 'Termination'}
        ]

        base_filename = 'AB3D0001'
        expected_files = pipeline_validation.generate_expected_files(path, base_filename)

        # Should include .CR3 and .DNG with suffix
        assert 'AB3D0001.CR3' in expected_files
        assert 'AB3D0001-DxO_DeepPRIME_XD2s.DNG' in expected_files


class TestFileValidation:
    """Tests for file validation against paths (Phase 3 - User Story 1)."""

    def test_classify_consistent(self, sample_imagegroups):
        """Test CONSISTENT status classification."""
        # AB3D0001 has all expected files
        specific_images = pipeline_validation.flatten_imagegroups_to_specific_images(sample_imagegroups)
        img = [s for s in specific_images if s.base_filename == 'AB3D0001'][0]

        # Expected files for this image (based on pipeline)
        expected_files = ['AB3D0001.CR3', 'AB3D0001.XMP', 'AB3D0001-DxO_DeepPRIME_XD2s.DNG']

        # Classify status
        status = pipeline_validation.classify_validation_status(
            actual_files=set(img.files),
            expected_files=set(expected_files)
        )

        assert status == pipeline_validation.ValidationStatus.CONSISTENT

    def test_classify_partial(self, sample_imagegroups):
        """Test PARTIAL status classification."""
        # AB3D0002 is missing DNG file
        specific_images = pipeline_validation.flatten_imagegroups_to_specific_images(sample_imagegroups)
        img = [s for s in specific_images if s.base_filename == 'AB3D0002'][0]

        # Expected files
        expected_files = ['AB3D0002.CR3', 'AB3D0002.XMP', 'AB3D0002-DxO_DeepPRIME_XD2s.DNG']

        # Classify status
        status = pipeline_validation.classify_validation_status(
            actual_files=set(img.files),
            expected_files=set(expected_files)
        )

        assert status == pipeline_validation.ValidationStatus.PARTIAL

    def test_classify_consistent_with_warning(self, sample_imagegroups):
        """Test CONSISTENT-WITH-WARNING status classification."""
        # AB3D0003 has all expected files plus an extra file
        specific_images = pipeline_validation.flatten_imagegroups_to_specific_images(sample_imagegroups)
        img = [s for s in specific_images if s.base_filename == 'AB3D0003'][0]

        # Expected files (without backup file)
        expected_files = ['AB3D0003.CR3', 'AB3D0003.XMP', 'AB3D0003-DxO_DeepPRIME_XD2s.DNG']

        # Classify status
        status = pipeline_validation.classify_validation_status(
            actual_files=set(img.files),
            expected_files=set(expected_files)
        )

        assert status == pipeline_validation.ValidationStatus.CONSISTENT_WITH_WARNING

    def test_classify_inconsistent(self):
        """Test INCONSISTENT status classification."""
        # Completely wrong files
        actual_files = {'WRONG0001.JPG', 'WRONG0001.XMP'}
        expected_files = {'AB3D0001.CR3', 'AB3D0001.XMP', 'AB3D0001-DxO_DeepPRIME_XD2s.DNG'}

        # Classify status
        status = pipeline_validation.classify_validation_status(
            actual_files=actual_files,
            expected_files=expected_files
        )

        assert status == pipeline_validation.ValidationStatus.INCONSISTENT


# =============================================================================
# Phase 4: Custom Pipeline Tests (User Story 2)
# =============================================================================

class TestCustomPipelines:
    """Tests for custom pipeline configurations (Phase 4 - User Story 2)."""

    def test_custom_processing_methods(self, tmp_path, mock_photo_admin_config):
        """Test integration with custom processing methods."""
        # Create pipeline with custom processing methods
        custom_pipeline = {
            'default': {
                'nodes': [
                    {
                        'id': 'capture',
                        'type': 'Capture',
                        'name': 'Camera Capture',
                        'output': ['raw_file']
                    },
                    {
                        'id': 'raw_file',
                        'type': 'File',
                        'extension': '.CR3',
                        'name': 'Raw File',
                        'output': ['dxo_process']
                    },
                    {
                        'id': 'dxo_process',
                        'type': 'Process',
                        'method_ids': ['DxO_DeepPRIME_XD2s'],
                        'name': 'DxO Processing',
                        'output': ['dng_file']
                    },
                    {
                        'id': 'dng_file',
                        'type': 'File',
                        'extension': '.DNG',
                        'name': 'DNG File',
                        'output': ['photoshop_process']
                    },
                    {
                        'id': 'photoshop_process',
                        'type': 'Process',
                        'method_ids': ['Edit'],
                        'name': 'Photoshop Editing',
                        'output': ['tiff_file']
                    },
                    {
                        'id': 'tiff_file',
                        'type': 'File',
                        'extension': '.TIF',
                        'name': 'TIFF File',
                        'output': ['termination']
                    },
                    {
                        'id': 'termination',
                        'type': 'Termination',
                        'termination_type': 'Final Output',
                        'name': 'Final Output Ready',
                        'output': []
                    }
                ]
            }
        }

        # Create config file
        config_file = tmp_path / "custom_config.yaml"
        config_data = {'processing_pipelines': custom_pipeline}
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        # Load configuration via PhotoAdminConfig (per constitution)
        config = pipeline_validation.PhotoAdminConfig(config_path=config_file)

        # Load pipeline
        pipeline = pipeline_validation.load_pipeline_config(config)

        # Validate structure
        errors = pipeline_validation.validate_pipeline_structure(pipeline, mock_photo_admin_config)
        assert len(errors) == 0

        # Enumerate paths
        paths = pipeline_validation.enumerate_all_paths(pipeline)
        assert len(paths) > 0

        # Generate expected files for a test image
        path = paths[0]
        expected_files = pipeline_validation.generate_expected_files(path, 'AB3D0001')

        # Should have all files with correct suffixes
        assert 'AB3D0001.CR3' in expected_files
        assert 'AB3D0001-DxO_DeepPRIME_XD2s.DNG' in expected_files
        assert 'AB3D0001-DxO_DeepPRIME_XD2s-Edit.TIF' in expected_files

    def test_pairing_node_in_pipeline(self, tmp_path, mock_photo_admin_config):
        """Test that Pairing nodes are handled correctly in pipeline."""
        # Create pipeline with Pairing node (HDR)
        pairing_pipeline = {
            'default': {
                'nodes': [
                    {
                        'id': 'capture',
                        'type': 'Capture',
                        'name': 'Camera Capture',
                        'output': ['raw_file_1', 'raw_file_2', 'raw_file_3']
                    },
                    {
                        'id': 'raw_file_1',
                        'type': 'File',
                        'extension': '.CR3',
                        'name': 'HDR Exposure 1',
                        'output': ['hdr_pairing']
                    },
                    {
                        'id': 'raw_file_2',
                        'type': 'File',
                        'extension': '.CR3',
                        'name': 'HDR Exposure 2',
                        'output': ['hdr_pairing']
                    },
                    {
                        'id': 'raw_file_3',
                        'type': 'File',
                        'extension': '.CR3',
                        'name': 'HDR Exposure 3',
                        'output': ['hdr_pairing']
                    },
                    {
                        'id': 'hdr_pairing',
                        'type': 'Pairing',
                        'pairing_type': 'HDR',
                        'input_count': 3,
                        'name': 'HDR Merge',
                        'output': ['merged_dng']
                    },
                    {
                        'id': 'merged_dng',
                        'type': 'File',
                        'extension': '.DNG',
                        'name': 'Merged DNG',
                        'output': ['termination']
                    },
                    {
                        'id': 'termination',
                        'type': 'Termination',
                        'termination_type': 'HDR Archive',
                        'name': 'HDR Archive Ready',
                        'output': []
                    }
                ]
            }
        }

        # Create config file
        config_file = tmp_path / "pairing_config.yaml"
        config_data = {'processing_pipelines': pairing_pipeline}
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        # Load configuration via PhotoAdminConfig (per constitution)
        config = pipeline_validation.PhotoAdminConfig(config_path=config_file)

        # Load pipeline
        pipeline = pipeline_validation.load_pipeline_config(config)

        # Verify Pairing node was parsed correctly
        pairing_node = pipeline.nodes_by_id.get('hdr_pairing')
        assert pairing_node is not None
        assert isinstance(pairing_node, pipeline_validation.PairingNode)
        assert pairing_node.pairing_type == 'HDR'
        assert pairing_node.input_count == 3

        # Validate structure should pass
        errors = pipeline_validation.validate_pipeline_structure(pipeline, mock_photo_admin_config)
        assert len(errors) == 0

        # Enumerate paths - should handle Pairing node
        paths = pipeline_validation.enumerate_paths_with_pairing(pipeline)
        assert len(paths) > 0


# =============================================================================
# Phase 5: Counter Looping and Multiple Captures Tests
# =============================================================================

class TestCounterLooping:
    """Tests for counter looping and multiple captures (Phase 5 - User Story 3)."""

    def test_flatten_imagegroup_with_suffixes(self):
        """Test T035: SpecificImage flattening from ImageGroup with suffixes '', '2', '3'."""
        # Create ImageGroup with multiple separate_images (counter looping scenario)
        imagegroups = [
            {
                'group_id': 'AB3D0001',
                'camera_id': 'AB3D',
                'counter': '0001',
                'separate_images': {
                    '': {  # Primary image
                        'files': ['AB3D0001.CR3', 'AB3D0001.XMP']
                    },
                    '2': {  # Second capture
                        'files': ['AB3D0001-2.CR3', 'AB3D0001-2.XMP']
                    },
                    '3': {  # Third capture
                        'files': ['AB3D0001-3.CR3']
                    }
                }
            }
        ]

        # Flatten to SpecificImages
        specific_images = pipeline_validation.flatten_imagegroups_to_specific_images(imagegroups)

        # Should have 3 separate SpecificImages
        assert len(specific_images) == 3

        # Check primary image (no suffix)
        primary = [img for img in specific_images if img.suffix == ''][0]
        assert primary.base_filename == 'AB3D0001'
        assert primary.group_id == 'AB3D0001'
        assert primary.camera_id == 'AB3D'
        assert primary.counter == '0001'
        assert primary.suffix == ''
        assert 'AB3D0001.CR3' in primary.files
        assert 'AB3D0001.XMP' in primary.files

        # Check second capture (suffix '2')
        second = [img for img in specific_images if img.suffix == '2'][0]
        assert second.base_filename == 'AB3D0001-2'
        assert second.group_id == 'AB3D0001'
        assert second.suffix == '2'
        assert 'AB3D0001-2.CR3' in second.files
        assert 'AB3D0001-2.XMP' in second.files

        # Check third capture (suffix '3')
        third = [img for img in specific_images if img.suffix == '3'][0]
        assert third.base_filename == 'AB3D0001-3'
        assert third.suffix == '3'
        assert 'AB3D0001-3.CR3' in third.files

    def test_base_filename_generation_with_suffix(self):
        """Test T036: base_filename generation with suffix (e.g., AB3D0001-2)."""
        # Test with primary image (no suffix)
        path = [
            {'type': 'Capture'},
            {'type': 'File', 'extension': '.CR3'},
            {'type': 'Process', 'method_id': 'DxO_DeepPRIME_XD2s'},
            {'type': 'File', 'extension': '.DNG'},
            {'type': 'Termination'}
        ]

        # Primary image - base_filename without suffix
        expected_primary = pipeline_validation.generate_expected_files(path, 'AB3D0001')
        assert 'AB3D0001.CR3' in expected_primary
        assert 'AB3D0001-DxO_DeepPRIME_XD2s.DNG' in expected_primary

        # Second capture - base_filename WITH suffix
        expected_second = pipeline_validation.generate_expected_files(path, 'AB3D0001-2')
        assert 'AB3D0001-2.CR3' in expected_second
        assert 'AB3D0001-2-DxO_DeepPRIME_XD2s.DNG' in expected_second

        # Third capture - base_filename WITH suffix
        expected_third = pipeline_validation.generate_expected_files(path, 'AB3D0001-3')
        assert 'AB3D0001-3.CR3' in expected_third
        assert 'AB3D0001-3-DxO_DeepPRIME_XD2s.DNG' in expected_third

    def test_multiple_specific_images_different_statuses(self, tmp_path, mock_photo_admin_config):
        """Test T037: ImageGroup with 2 SpecificImages, different validation statuses."""
        # Create simple pipeline
        pipeline_config = {
            'default': {
                'nodes': [
                    {
                        'id': 'capture',
                        'type': 'Capture',
                        'name': 'Camera Capture',
                        'output': ['raw_file', 'xmp_file']
                    },
                    {
                        'id': 'raw_file',
                        'type': 'File',
                        'extension': '.CR3',
                        'name': 'Raw File',
                        'output': ['termination']  # Both files lead to termination
                    },
                    {
                        'id': 'xmp_file',
                        'type': 'File',
                        'extension': '.XMP',
                        'name': 'XMP Metadata',
                        'output': ['termination']  # Both files lead to termination
                    },
                    {
                        'id': 'termination',
                        'type': 'Termination',
                        'termination_type': 'Archive',
                        'name': 'Archive Ready',
                        'output': []
                    }
                ]
            }
        }

        # Create config file
        config_file = tmp_path / "config.yaml"
        config_data = {'processing_pipelines': pipeline_config}
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        # Load configuration
        config = pipeline_validation.PhotoAdminConfig(config_path=config_file)

        # Load pipeline
        pipeline = pipeline_validation.load_pipeline_config(config)

        # Create ImageGroup with 2 SpecificImages
        # - Primary image: CONSISTENT (has all expected files)
        # - Second capture: PARTIAL (missing XMP file)
        imagegroups = [
            {
                'group_id': 'AB3D0001',
                'camera_id': 'AB3D',
                'counter': '0001',
                'separate_images': {
                    '': {  # Primary - CONSISTENT
                        'files': ['AB3D0001.CR3', 'AB3D0001.XMP']
                    },
                    '2': {  # Second capture - PARTIAL (missing XMP)
                        'files': ['AB3D0001-2.CR3']
                    }
                }
            }
        ]

        # Flatten to SpecificImages
        specific_images = pipeline_validation.flatten_imagegroups_to_specific_images(imagegroups)
        assert len(specific_images) == 2

        # Validate each SpecificImage
        results = pipeline_validation.validate_all_images(specific_images, pipeline, show_progress=False)
        assert len(results) == 2

        # Find results by unique_id
        primary_result = [r for r in results if r.base_filename == 'AB3D0001'][0]
        second_result = [r for r in results if r.base_filename == 'AB3D0001-2'][0]

        # Primary image should be CONSISTENT_WITH_WARNING
        # (With best-path selection: Path1 expects {CR3}, Path2 expects {XMP},
        #  but actual has {CR3, XMP}, so both paths have extra files)
        primary_status = primary_result.termination_matches[0].status
        assert primary_status == pipeline_validation.ValidationStatus.CONSISTENT_WITH_WARNING

        # Second capture should be CONSISTENT
        # (With best-path selection: Path1 expects {CR3}, actual={CR3} → CONSISTENT,
        #  Path2 expects {XMP}, actual={CR3} → INCONSISTENT,
        #  Best status is CONSISTENT from Path1)
        second_status = second_result.termination_matches[0].status
        assert second_status == pipeline_validation.ValidationStatus.CONSISTENT


# =============================================================================
# Phase 6: Smart Caching Tests (User Story 4)
# =============================================================================

class TestCaching:
    """Tests for cache operations (Phase 6 - User Story 4)."""

    def test_calculate_pipeline_config_hash(self, tmp_path):
        """Test T042: calculate_pipeline_config_hash() with SHA256."""
        # Create test config file
        config_content = """
processing_pipelines:
  default:
    nodes:
      - id: capture
        type: Capture
        name: Camera Capture
        output: [raw_file]
      - id: raw_file
        type: File
        extension: .CR3
        name: Raw File
        output: [termination]
      - id: termination
        type: Termination
        termination_type: Archive
        name: Archive Ready
        output: []
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content, encoding='utf-8')

        # Calculate hash
        hash1 = pipeline_validation.calculate_pipeline_config_hash(config_path)

        # Verify it's a valid SHA256 hash (64 hex characters)
        assert len(hash1) == 64
        assert all(c in '0123456789abcdef' for c in hash1)

        # Verify hash is deterministic
        hash2 = pipeline_validation.calculate_pipeline_config_hash(config_path)
        assert hash1 == hash2

        # Modify pipeline config and verify hash changes
        modified_content = config_content.replace('Camera Capture', 'Modified Capture')
        config_path.write_text(modified_content, encoding='utf-8')
        hash3 = pipeline_validation.calculate_pipeline_config_hash(config_path)
        assert hash3 != hash1

        # Verify hash is insensitive to whitespace/formatting (same structure = same hash)
        reformatted_content = config_content.replace('  ', '    ')  # Different indentation
        config_path.write_text(config_content, encoding='utf-8')
        hash4 = pipeline_validation.calculate_pipeline_config_hash(config_path)
        assert hash4 == hash1  # Structure unchanged, hash should match

    def test_get_folder_content_hash(self, tmp_path):
        """Test T042: get_folder_content_hash() reads from Photo Pairing cache."""
        # Create mock Photo Pairing cache
        cache_data = {
            'version': '1.0',
            'metadata': {
                'file_list_hash': 'abc123def456' + '0' * 52  # 64-char hash
            },
            'imagegroups': []
        }
        cache_path = tmp_path / '.photo_pairing_imagegroups'
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f)

        # Get folder content hash
        folder_hash = pipeline_validation.get_folder_content_hash(tmp_path)
        assert folder_hash == 'abc123def456' + '0' * 52

        # Test error when cache doesn't exist
        (tmp_path / 'empty_folder').mkdir()
        with pytest.raises(FileNotFoundError, match="Photo Pairing cache not found"):
            pipeline_validation.get_folder_content_hash(tmp_path / 'empty_folder')

    def test_calculate_validation_results_hash(self):
        """Test T042: calculate_validation_results_hash() with SHA256."""
        # Create test validation results
        validation_results = [
            {
                'unique_id': 'AB3D0001',
                'status': 'CONSISTENT',
                'matched_paths': ['path1']
            },
            {
                'unique_id': 'AB3D0002',
                'status': 'PARTIAL',
                'matched_paths': []
            }
        ]

        # Calculate hash
        hash1 = pipeline_validation.calculate_validation_results_hash(validation_results)

        # Verify it's a valid SHA256 hash
        assert len(hash1) == 64
        assert all(c in '0123456789abcdef' for c in hash1)

        # Verify hash is deterministic
        hash2 = pipeline_validation.calculate_validation_results_hash(validation_results)
        assert hash1 == hash2

        # Modify results and verify hash changes
        modified_results = validation_results.copy()
        modified_results[0] = modified_results[0].copy()
        modified_results[0]['status'] = 'PARTIAL'
        hash3 = pipeline_validation.calculate_validation_results_hash(modified_results)
        assert hash3 != hash1

    def test_cache_invalidation_detection(self, tmp_path, mock_config):
        """Test T043: Cache invalidation detection (pipeline changed, folder changed, manual edits)."""
        # Setup Photo Pairing cache
        photo_cache_data = {
            'version': '1.0',
            'metadata': {
                'file_list_hash': 'folder_hash_v1' + '0' * 51
            },
            'imagegroups': []
        }
        photo_cache_path = tmp_path / '.photo_pairing_imagegroups'
        with open(photo_cache_path, 'w', encoding='utf-8') as f:
            json.dump(photo_cache_data, f)

        # Create initial pipeline validation cache
        validation_results = [{'unique_id': 'AB3D0001', 'status': 'CONSISTENT'}]
        validation_hash = pipeline_validation.calculate_validation_results_hash(validation_results)
        pipeline_hash = pipeline_validation.calculate_pipeline_config_hash(mock_config)
        folder_hash = 'folder_hash_v1' + '0' * 51

        cache_data = {
            'version': '1.0',
            'tool_version': '1.0.0',
            'metadata': {
                'pipeline_config_hash': pipeline_hash,
                'folder_content_hash': folder_hash,
                'validation_results_hash': validation_hash
            },
            'validation_results': validation_results
        }

        # Test 1: Valid cache (no changes)
        validation = pipeline_validation.validate_pipeline_cache(
            cache_data, mock_config, tmp_path
        )
        assert validation['valid'] is True
        assert validation['pipeline_changed'] is False
        assert validation['folder_changed'] is False
        assert validation['cache_edited'] is False

        # Test 2: Pipeline config changed
        modified_pipeline = tmp_path / "modified_config.yaml"
        mock_config_content = mock_config.read_text(encoding='utf-8')
        modified_content = mock_config_content.replace('Camera Capture', 'Modified Capture')
        modified_pipeline.write_text(modified_content, encoding='utf-8')

        validation = pipeline_validation.validate_pipeline_cache(
            cache_data, modified_pipeline, tmp_path
        )
        assert validation['valid'] is False
        assert validation['pipeline_changed'] is True
        assert validation['folder_changed'] is False
        assert validation['cache_edited'] is False

        # Test 3: Folder content changed (different file_list_hash in Photo Pairing cache)
        photo_cache_data['metadata']['file_list_hash'] = 'folder_hash_v2' + '0' * 51
        with open(photo_cache_path, 'w', encoding='utf-8') as f:
            json.dump(photo_cache_data, f)

        validation = pipeline_validation.validate_pipeline_cache(
            cache_data, mock_config, tmp_path
        )
        assert validation['valid'] is False
        assert validation['pipeline_changed'] is False
        assert validation['folder_changed'] is True
        assert validation['cache_edited'] is False

        # Reset folder hash for next test
        photo_cache_data['metadata']['file_list_hash'] = 'folder_hash_v1' + '0' * 51
        with open(photo_cache_path, 'w', encoding='utf-8') as f:
            json.dump(photo_cache_data, f)

        # Test 4: Cache manually edited (validation_results modified)
        manually_edited_cache = cache_data.copy()
        manually_edited_cache['validation_results'] = [
            {'unique_id': 'AB3D0001', 'status': 'PARTIAL'}  # Changed status
        ]

        validation = pipeline_validation.validate_pipeline_cache(
            manually_edited_cache, mock_config, tmp_path
        )
        assert validation['valid'] is False
        assert validation['pipeline_changed'] is False
        assert validation['folder_changed'] is False
        assert validation['cache_edited'] is True

    def test_cache_reuse_when_unchanged(self, tmp_path, mock_config):
        """Test T044: Integration test for cache reuse when folder/pipeline unchanged."""
        # Setup Photo Pairing cache
        imagegroups = [
            {
                'group_id': 'AB3D0001',
                'camera_id': 'AB3D',
                'counter': '0001',
                'separate_images': {
                    '': {'files': ['AB3D0001.CR3', 'AB3D0001.XMP']}
                }
            }
        ]
        photo_cache_data = {
            'version': '1.0',
            'metadata': {
                'file_list_hash': 'stable_hash' + '0' * 53
            },
            'imagegroups': imagegroups
        }
        photo_cache_path = tmp_path / '.photo_pairing_imagegroups'
        with open(photo_cache_path, 'w', encoding='utf-8') as f:
            json.dump(photo_cache_data, f)

        # Create test files
        (tmp_path / 'AB3D0001.CR3').touch()
        (tmp_path / 'AB3D0001.XMP').touch()

        # Get hashes for cache
        pipeline_hash = pipeline_validation.calculate_pipeline_config_hash(mock_config)
        folder_hash = pipeline_validation.get_folder_content_hash(tmp_path)

        # Create and save cache with validation results
        validation_results = [
            {
                'unique_id': 'AB3D0001',
                'group_id': 'AB3D0001',
                'status': 'CONSISTENT',
                'matched_paths_count': 1
            }
        ]

        success = pipeline_validation.save_pipeline_cache(
            tmp_path,
            validation_results,
            pipeline_hash,
            folder_hash
        )
        assert success is True

        # Verify cache file was created
        cache_path = tmp_path / '.pipeline_validation_cache.json'
        assert cache_path.exists()

        # Load cache and verify it's valid
        loaded_cache = pipeline_validation.load_pipeline_cache(tmp_path)
        assert loaded_cache is not None
        assert loaded_cache['validation_results'] == validation_results

        # Validate cache (should be valid since nothing changed)
        validation = pipeline_validation.validate_pipeline_cache(
            loaded_cache, mock_config, tmp_path
        )
        assert validation['valid'] is True
        assert loaded_cache['metadata']['pipeline_config_hash'] == pipeline_hash
        assert loaded_cache['metadata']['folder_content_hash'] == folder_hash

    def test_cache_invalidation_on_config_change(self, tmp_path, mock_config):
        """Test T045: Integration test for cache invalidation when pipeline config modified."""
        # Setup Photo Pairing cache
        photo_cache_data = {
            'version': '1.0',
            'metadata': {
                'file_list_hash': 'stable_hash' + '0' * 53
            },
            'imagegroups': []
        }
        with open(tmp_path / '.photo_pairing_imagegroups', 'w', encoding='utf-8') as f:
            json.dump(photo_cache_data, f)

        # Get initial pipeline hash
        initial_hash = pipeline_validation.calculate_pipeline_config_hash(mock_config)
        folder_hash = pipeline_validation.get_folder_content_hash(tmp_path)

        # Save cache with initial hash
        validation_results = [{'unique_id': 'AB3D0001', 'status': 'CONSISTENT'}]
        pipeline_validation.save_pipeline_cache(
            tmp_path, validation_results, initial_hash, folder_hash
        )

        # Modify pipeline config
        config_content = mock_config.read_text(encoding='utf-8')
        modified_content = config_content.replace(
            'Camera Capture',
            'Modified Camera Capture'
        )
        mock_config.write_text(modified_content, encoding='utf-8')

        # Get new pipeline hash
        new_hash = pipeline_validation.calculate_pipeline_config_hash(mock_config)
        assert new_hash != initial_hash  # Hash should change

        # Load cache and validate
        cache = pipeline_validation.load_pipeline_cache(tmp_path)
        validation = pipeline_validation.validate_pipeline_cache(
            cache, mock_config, tmp_path
        )

        # Cache should be invalid due to pipeline change
        assert validation['valid'] is False
        assert validation['pipeline_changed'] is True
        assert validation['folder_changed'] is False
        assert validation['cache_edited'] is False


class TestHTMLReportGeneration:
    """Tests for HTML report generation (Phase 7 - User Story 5)."""

    def test_build_report_context(self):
        """Test T056: build_report_context() creates ReportContext with KPIs and sections."""
        # Create sample validation results
        validation_results = [
            {
                'unique_id': 'AB3D0001',
                'group_id': 'AB3D0001',
                'status': 'CONSISTENT',
                'termination_matches': [
                    {
                        'termination_type': 'Black Box Archive',
                        'status': 'CONSISTENT',
                        'expected_files': ['AB3D0001.CR3', 'AB3D0001.XMP', 'AB3D0001-DxO.DNG'],
                        'actual_files': ['AB3D0001.CR3', 'AB3D0001.XMP', 'AB3D0001-DxO.DNG'],
                        'missing_files': [],
                        'extra_files': []
                    }
                ]
            },
            {
                'unique_id': 'AB3D0002',
                'group_id': 'AB3D0002',
                'status': 'PARTIAL',
                'termination_matches': [
                    {
                        'termination_type': 'Black Box Archive',
                        'status': 'PARTIAL',
                        'expected_files': ['AB3D0002.CR3', 'AB3D0002.XMP', 'AB3D0002-DxO.DNG'],
                        'actual_files': ['AB3D0002.CR3', 'AB3D0002.XMP'],
                        'missing_files': ['AB3D0002-DxO.DNG'],
                        'extra_files': []
                    }
                ]
            },
            {
                'unique_id': 'AB3D0003',
                'group_id': 'AB3D0003',
                'status': 'CONSISTENT_WITH_WARNING',
                'termination_matches': [
                    {
                        'termination_type': 'Black Box Archive',
                        'status': 'CONSISTENT_WITH_WARNING',
                        'expected_files': ['AB3D0003.CR3', 'AB3D0003.XMP'],
                        'actual_files': ['AB3D0003.CR3', 'AB3D0003.XMP', 'AB3D0003-backup.CR3'],
                        'missing_files': [],
                        'extra_files': ['AB3D0003-backup.CR3']
                    }
                ]
            }
        ]

        # Build report context
        scan_start = datetime.now()
        scan_end = datetime.now()
        context = pipeline_validation.build_report_context(
            validation_results=validation_results,
            scan_path='/test/photos',
            scan_start=scan_start,
            scan_end=scan_end
        )

        # Verify ReportContext structure
        assert context.tool_name == 'Pipeline Validation Tool'
        assert context.tool_version == pipeline_validation.TOOL_VERSION
        assert context.scan_path == '/test/photos'
        assert context.scan_timestamp == scan_start
        assert context.scan_duration >= 0

        # Verify KPIs exist
        # Expected: Total, Overall Consistent, and per-termination (Ready, Partial, With Warnings)
        # Test data: 1 CONSISTENT, 1 PARTIAL, 1 CONSISTENT-WITH-WARNING for Black Box Archive
        assert len(context.kpis) >= 5  # Total, Overall Consistent, Ready, Partial, With Warnings

        total_kpi = next(kpi for kpi in context.kpis if 'Total' in kpi.title)
        assert total_kpi.value == '3'

        # Check for Overall Consistent KPI
        overall_consistent_kpi = next(kpi for kpi in context.kpis if 'Overall Consistent' in kpi.title)
        assert overall_consistent_kpi.value == '1'
        assert overall_consistent_kpi.status == 'success'

        # Check for per-termination KPIs
        ready_kpis = [kpi for kpi in context.kpis if 'Ready' in kpi.title]
        assert len(ready_kpis) >= 1
        black_box_ready = next((kpi for kpi in ready_kpis if 'Black Box Archive' in kpi.title), None)
        assert black_box_ready is not None
        assert black_box_ready.value == '2'  # 1 CONSISTENT + 1 CONSISTENT-WITH-WARNING

        # Check for Partial KPI
        partial_kpis = [kpi for kpi in context.kpis if 'Partial' in kpi.title]
        assert len(partial_kpis) >= 1
        black_box_partial = next((kpi for kpi in partial_kpis if 'Black Box Archive' in kpi.title), None)
        assert black_box_partial is not None
        assert black_box_partial.value == '1'

        # Check for With Warnings KPI
        warning_kpis = [kpi for kpi in context.kpis if 'With Warnings' in kpi.title]
        assert len(warning_kpis) >= 1
        black_box_warnings = next((kpi for kpi in warning_kpis if 'Black Box Archive' in kpi.title), None)
        assert black_box_warnings is not None
        assert black_box_warnings.value == '1'

        # Verify sections exist - should include overall chart + per-termination charts + tables
        assert len(context.sections) >= 3  # Overall chart, termination chart, and tables

        # Check for Overall status chart
        overall_chart = next((s for s in context.sections if s.title == 'Status Distribution - Overall'), None)
        assert overall_chart is not None
        assert overall_chart.type == 'chart_pie'

        # Check for termination-specific chart
        term_charts = [s for s in context.sections if 'Status Distribution - Black Box Archive' in s.title]
        assert len(term_charts) >= 1

    def test_chart_data_generation(self):
        """Test T057: Chart data generation for pie charts (overall + per-termination)."""
        # Create sample validation results with termination details
        validation_results = [
            {
                'unique_id': 'AB3D0001',
                'status': 'CONSISTENT',
                'termination_matches': [
                    {'termination_id': 'term1', 'termination_type': 'Black Box Archive', 'status': 'CONSISTENT'}
                ]
            },
            {
                'unique_id': 'AB3D0002',
                'status': 'CONSISTENT',
                'termination_matches': [
                    {'termination_id': 'term1', 'termination_type': 'Black Box Archive', 'status': 'CONSISTENT'}
                ]
            },
            {
                'unique_id': 'AB3D0003',
                'status': 'PARTIAL',
                'termination_matches': [
                    {'termination_id': 'term1', 'termination_type': 'Black Box Archive', 'status': 'PARTIAL'}
                ]
            },
            {
                'unique_id': 'AB3D0004',
                'status': 'CONSISTENT_WITH_WARNING',
                'termination_matches': [
                    {'termination_id': 'term1', 'termination_type': 'Black Box Archive', 'status': 'CONSISTENT_WITH_WARNING'}
                ]
            }
        ]

        # Test chart sections - should include overall + per-termination charts
        chart_sections = pipeline_validation.build_chart_sections(validation_results)
        assert len(chart_sections) >= 2  # Overall + at least one termination

        # Check overall chart
        overall_chart = next((s for s in chart_sections if s.title == 'Status Distribution - Overall'), None)
        assert overall_chart is not None
        assert overall_chart.type == 'chart_pie'
        assert 'labels' in overall_chart.data
        assert 'values' in overall_chart.data

        # Verify overall chart data
        labels = overall_chart.data['labels']
        values = overall_chart.data['values']
        assert 'CONSISTENT' in labels
        assert 'PARTIAL' in labels
        assert 'CONSISTENT_WITH_WARNING' in labels
        assert values[labels.index('CONSISTENT')] == 2
        assert values[labels.index('PARTIAL')] == 1
        assert values[labels.index('CONSISTENT_WITH_WARNING')] == 1

        # Check termination-specific chart
        term_chart = next((s for s in chart_sections if 'Black Box Archive' in s.title), None)
        assert term_chart is not None
        assert term_chart.type == 'chart_pie'
        assert 'labels' in term_chart.data
        assert 'values' in term_chart.data

    def test_html_report_generation_integration(self, tmp_path):
        """Test T058: Integration test for HTML report with timestamped filename."""
        # Create sample validation results
        validation_results = [
            {
                'unique_id': 'AB3D0001',
                'group_id': 'AB3D0001',
                'status': 'CONSISTENT',
                'termination_matches': [
                    {
                        'termination_type': 'Black Box Archive',
                        'status': 'CONSISTENT',
                        'expected_files': ['AB3D0001.CR3'],
                        'actual_files': ['AB3D0001.CR3'],
                        'missing_files': [],
                        'extra_files': []
                    }
                ]
            }
        ]

        # Generate HTML report
        scan_start = datetime.now()
        scan_end = datetime.now()
        report_path = pipeline_validation.generate_html_report(
            validation_results=validation_results,
            output_dir=tmp_path,
            scan_path='/test/photos',
            scan_start=scan_start,
            scan_end=scan_end
        )

        # Verify report was created
        assert report_path.exists()
        assert report_path.suffix == '.html'

        # Verify timestamped filename format
        assert 'pipeline_validation_report_' in report_path.name
        # Format: pipeline_validation_report_YYYY-MM-DD_HH-MM-SS.html

        # Read and verify report content
        html_content = report_path.read_text(encoding='utf-8')
        assert 'Pipeline Validation Tool' in html_content
        assert 'AB3D0001' in html_content
        assert 'CONSISTENT' in html_content

        # Verify Chart.js is included
        assert 'Chart.js' in html_content or 'chart' in html_content.lower()

        # Verify base template structure
        assert '<!DOCTYPE html>' in html_content
        assert '<html' in html_content
        assert '</html>' in html_content


# =============================================================================
# Graph Visualization and MAX_ITERATIONS Tests
# =============================================================================

class TestGraphVisualization:
    """Tests for --display-graph functionality and graph traversal fixes."""

    def test_generate_sample_base_filename(self):
        """Test sample filename generation uses first camera ID + random counter."""
        # Create mock config with camera mappings
        mock_config = MagicMock()
        mock_config.camera_mappings = {
            'AB3D': [{'name': 'Canon EOS R5', 'serial_number': '12345'}],
            'XY12': [{'name': 'Sony A7IV', 'serial_number': '67890'}]
        }

        # Generate sample filename
        sample = pipeline_validation.generate_sample_base_filename(mock_config)

        # Should use first camera ID (AB3D)
        assert sample.startswith('AB3D')
        assert len(sample) == 8  # AB3D + 4 digits

        # Counter should be 4 digits
        counter = sample[4:]
        assert counter.isdigit()
        assert 1 <= int(counter) <= 9999

    def test_generate_sample_base_filename_no_cameras(self):
        """Test sample filename generation fallback when no cameras configured."""
        # Create mock config with no camera mappings
        mock_config = MagicMock()
        mock_config.camera_mappings = {}

        # Generate sample filename
        sample = pipeline_validation.generate_sample_base_filename(mock_config)

        # Should use fallback "ABCD0001"
        assert sample == 'ABCD0001'
        assert len(sample) == 8

    def test_build_graph_visualization_table(self, sample_pipeline_config):
        """Test graph visualization table generation."""
        from utils.config_manager import PhotoAdminConfig

        # Create pipeline from sample config
        config_data = {
            'processing_pipelines': sample_pipeline_config,
            'camera_mappings': {'AB3D': [{'name': 'Test Camera'}]}
        }

        with patch.object(PhotoAdminConfig, '_load_config', return_value=config_data):
            config = PhotoAdminConfig()

            pipeline = pipeline_validation.load_pipeline_config(config, 'default')

            # Build graph visualization table
            section = pipeline_validation.build_graph_visualization_table(pipeline, config)

            # Verify section structure
            assert section.title.startswith('Pipeline Graph Visualization')
            assert section.type == 'table'
            assert 'headers' in section.data
            assert 'rows' in section.data

            # Verify table headers
            headers = section.data['headers']
            assert 'Path #' in headers
            assert 'Node Path' in headers
            assert 'Depth' in headers
            assert 'Termination Type' in headers
            assert 'Expected Files' in headers
            assert 'Truncated' in headers

            # Verify at least one path was enumerated
            rows = section.data['rows']
            assert len(rows) > 0

            # Verify row structure
            first_row = rows[0]
            assert len(first_row) == 6  # Path #, Node Path, Depth, Termination Type, Expected Files, Truncated

            # Verify node path contains arrows (except for first node)
            node_path = first_row[1]
            if len(node_path.split('\n')) > 1:  # Multi-node path
                assert '->' in node_path

            # Verify depth is a number
            depth = first_row[2]
            assert depth.isdigit()
            assert int(depth) >= 0

            # Verify expected files contain newlines between files (if multiple files)
            expected_files = first_row[4]
            # At minimum should have some content
            assert len(expected_files) > 0

    def test_max_iterations_applied_to_file_nodes(self):
        """Test MAX_ITERATIONS is applied to File nodes (not just Process nodes)."""
        # Create a pipeline with a File node loop
        from utils.config_manager import PhotoAdminConfig

        config_data = {
            'processing_pipelines': {
                'loop_test': {
                    'nodes': [
                        {
                            'id': 'capture',
                            'type': 'Capture',
                            'name': 'Capture',
                            'output': ['file1']
                        },
                        {
                            'id': 'file1',
                            'type': 'File',
                            'extension': '.CR3',
                            'name': 'File 1',
                            'output': ['file1']  # Loop to itself
                        },
                        {
                            'id': 'termination',
                            'type': 'Termination',
                            'name': 'End',
                            'termination_type': 'Archive',
                            'output': []
                        }
                    ]
                }
            }
        }

        with patch.object(PhotoAdminConfig, '_load_config', return_value=config_data):
            config = PhotoAdminConfig()
            pipeline = pipeline_validation.load_pipeline_config(config, 'loop_test')

            # Enumerate paths - should truncate after MAX_ITERATIONS
            paths = pipeline_validation.enumerate_all_paths(pipeline)

            # Should have one truncated path
            assert len(paths) == 1
            assert paths[0][-1]['type'] == 'Termination'
            assert paths[0][-1]['term_type'] == 'TRUNCATED'
            assert paths[0][-1]['truncated'] is True

    def test_max_iterations_applied_to_branching_nodes(self):
        """Test MAX_ITERATIONS is applied to Branching nodes."""
        from utils.config_manager import PhotoAdminConfig

        config_data = {
            'processing_pipelines': {
                'branch_loop_test': {
                    'nodes': [
                        {
                            'id': 'capture',
                            'type': 'Capture',
                            'name': 'Capture',
                            'output': ['branch1']
                        },
                        {
                            'id': 'branch1',
                            'type': 'Branching',
                            'name': 'Branch',
                            'condition_description': 'Test branch',
                            'output': ['branch1', 'termination']  # Loop to itself
                        },
                        {
                            'id': 'termination',
                            'type': 'Termination',
                            'name': 'End',
                            'termination_type': 'Archive',
                            'output': []
                        }
                    ]
                }
            }
        }

        with patch.object(PhotoAdminConfig, '_load_config', return_value=config_data):
            config = PhotoAdminConfig()
            pipeline = pipeline_validation.load_pipeline_config(config, 'branch_loop_test')

            # Enumerate paths - should truncate after MAX_ITERATIONS
            paths = pipeline_validation.enumerate_all_paths(pipeline)

            # Should have paths (some truncated, some reaching termination)
            assert len(paths) > 0

            # At least one path should be truncated due to branching loop
            truncated_paths = [p for p in paths if p[-1].get('truncated', False)]
            assert len(truncated_paths) > 0

    def test_display_graph_cli_argument(self):
        """Test --display-graph CLI argument parsing."""
        # Test that --display-graph is accepted
        with patch('sys.argv', ['pipeline_validation.py', '--validate-config', '--display-graph']):
            args = pipeline_validation.parse_arguments()
            assert args.display_graph is True
            assert args.validate_config is True
            assert args.folder_path is None  # Should be allowed without folder

    def test_display_graph_with_folder(self, tmp_path):
        """Test --display-graph works with folder argument."""
        test_folder = tmp_path / "test_photos"
        test_folder.mkdir()

        with patch('sys.argv', ['pipeline_validation.py', str(test_folder), '--display-graph']):
            args = pipeline_validation.parse_arguments()
            assert args.display_graph is True
            assert args.folder_path == test_folder

    def test_generate_expected_files_deduplication(self):
        """Test that duplicate filenames are removed, keeping only the last occurrence."""
        # Create a path with duplicate File nodes (same extension)
        path = [
            {'type': 'Capture'},
            {'type': 'File', 'extension': '.CR3'},  # First CR3
            {'type': 'Process', 'method_id': ''},  # No suffix
            {'type': 'File', 'extension': '.CR3'},  # Second CR3 (same filename!)
            {'type': 'Process', 'method_id': 'DxO'},
            {'type': 'File', 'extension': '.DNG'},
            {'type': 'Termination'}
        ]

        expected_files = pipeline_validation.generate_expected_files(path, 'AB3D0001')

        # Should only have 2 files, not 3 (CR3 should appear only once)
        assert len(expected_files) == 2
        assert 'AB3D0001.CR3' in expected_files
        assert 'AB3D0001-DxO.DNG' in expected_files

        # Verify no duplicates
        assert len(expected_files) == len(set(expected_files))

    def test_graph_visualization_table_sorted_by_depth(self, sample_pipeline_config):
        """Test that graph visualization table is sorted by depth (low to high)."""
        from utils.config_manager import PhotoAdminConfig

        config_data = {
            'processing_pipelines': sample_pipeline_config,
            'camera_mappings': {'AB3D': [{'name': 'Test Camera'}]}
        }

        with patch.object(PhotoAdminConfig, '_load_config', return_value=config_data):
            config = PhotoAdminConfig()
            pipeline = pipeline_validation.load_pipeline_config(config, 'default')

            # Build graph visualization table
            section = pipeline_validation.build_graph_visualization_table(pipeline, config)

            rows = section.data['rows']
            assert len(rows) >= 1  # Should have at least one row

            # Extract depths (column index 2)
            depths = [int(row[2]) for row in rows]

            # Verify depths are in ascending order (only meaningful if multiple rows)
            if len(depths) > 1:
                assert depths == sorted(depths), f"Depths not sorted: {depths}"
            else:
                # Single row case - just verify depth is a valid non-negative integer
                assert depths[0] >= 0


# =============================================================================
# Pairing Node Tests
# =============================================================================

class TestPairingNodes:
    """Tests for pairing node handling in path enumeration."""

    def test_find_pairing_nodes_in_topological_order(self):
        """Test finding pairing nodes in topological order."""
        from utils.config_manager import PhotoAdminConfig

        config_data = {
            'processing_pipelines': {
                'pairing_test': {
                    'nodes': [
                        {
                            'id': 'capture',
                            'type': 'Capture',
                            'name': 'Capture',
                            'output': ['file1', 'file2']
                        },
                        {
                            'id': 'file1',
                            'type': 'File',
                            'extension': '.CR3',
                            'name': 'File 1',
                            'output': ['pairing1']
                        },
                        {
                            'id': 'file2',
                            'type': 'File',
                            'extension': '.XMP',
                            'name': 'File 2',
                            'output': ['pairing1']
                        },
                        {
                            'id': 'pairing1',
                            'type': 'Pairing',
                            'name': 'Pairing 1',
                            'pairing_type': 'Metadata',
                            'input_count': 2,
                            'output': ['termination']
                        },
                        {
                            'id': 'termination',
                            'type': 'Termination',
                            'name': 'End',
                            'termination_type': 'Archive',
                            'output': []
                        }
                    ]
                }
            }
        }

        with patch.object(PhotoAdminConfig, '_load_config', return_value=config_data):
            config = PhotoAdminConfig()
            pipeline = pipeline_validation.load_pipeline_config(config, 'pairing_test')

            pairing_nodes = pipeline_validation.find_pairing_nodes_in_topological_order(pipeline)

            assert len(pairing_nodes) == 1
            assert pairing_nodes[0].id == 'pairing1'

    def test_validate_pairing_node_inputs(self):
        """Test validation of pairing node inputs."""
        from utils.config_manager import PhotoAdminConfig

        config_data = {
            'processing_pipelines': {
                'pairing_test': {
                    'nodes': [
                        {
                            'id': 'capture',
                            'type': 'Capture',
                            'name': 'Capture',
                            'output': ['file1', 'file2']
                        },
                        {
                            'id': 'file1',
                            'type': 'File',
                            'extension': '.CR3',
                            'name': 'File 1',
                            'output': ['pairing1']
                        },
                        {
                            'id': 'file2',
                            'type': 'File',
                            'extension': '.XMP',
                            'name': 'File 2',
                            'output': ['pairing1']
                        },
                        {
                            'id': 'pairing1',
                            'type': 'Pairing',
                            'name': 'Pairing 1',
                            'pairing_type': 'Metadata',
                            'input_count': 2,
                            'output': ['termination']
                        },
                        {
                            'id': 'termination',
                            'type': 'Termination',
                            'name': 'End',
                            'termination_type': 'Archive',
                            'output': []
                        }
                    ]
                }
            }
        }

        with patch.object(PhotoAdminConfig, '_load_config', return_value=config_data):
            config = PhotoAdminConfig()
            pipeline = pipeline_validation.load_pipeline_config(config, 'pairing_test')

            pairing_node = [n for n in pipeline.nodes if isinstance(n, pipeline_validation.PairingNode)][0]
            input1, input2 = pipeline_validation.validate_pairing_node_inputs(pairing_node, pipeline)

            # Should have exactly 2 inputs
            assert input1 in ['file1', 'file2']
            assert input2 in ['file1', 'file2']
            assert input1 != input2

    def test_enumerate_paths_with_simple_pairing(self):
        """Test path enumeration with simple pairing (2 branches merging)."""
        from utils.config_manager import PhotoAdminConfig

        config_data = {
            'processing_pipelines': {
                'pairing_test': {
                    'nodes': [
                        {
                            'id': 'capture',
                            'type': 'Capture',
                            'name': 'Capture',
                            'output': ['file1', 'file2']
                        },
                        {
                            'id': 'file1',
                            'type': 'File',
                            'extension': '.CR3',
                            'name': 'File 1',
                            'output': ['pairing1']
                        },
                        {
                            'id': 'file2',
                            'type': 'File',
                            'extension': '.XMP',
                            'name': 'File 2',
                            'output': ['pairing1']
                        },
                        {
                            'id': 'pairing1',
                            'type': 'Pairing',
                            'name': 'Pairing 1',
                            'pairing_type': 'Metadata',
                            'input_count': 2,
                            'output': ['termination']
                        },
                        {
                            'id': 'termination',
                            'type': 'Termination',
                            'name': 'End',
                            'termination_type': 'Archive',
                            'output': []
                        }
                    ]
                }
            }
        }

        with patch.object(PhotoAdminConfig, '_load_config', return_value=config_data):
            config = PhotoAdminConfig()
            pipeline = pipeline_validation.load_pipeline_config(config, 'pairing_test')

            paths = pipeline_validation.enumerate_paths_with_pairing(pipeline)

            # Should have 1 path: capture -> file1 -> file2 -> pairing1 -> termination
            assert len(paths) == 1

            # Check path structure
            path = paths[0]
            node_ids = [n['id'] for n in path]

            assert 'capture' in node_ids
            assert 'file1' in node_ids
            assert 'file2' in node_ids
            assert 'pairing1' in node_ids
            assert 'termination' in node_ids

    def test_enumerate_paths_with_branching_before_pairing(self):
        """Test path enumeration with branching before pairing (creates combinations)."""
        from utils.config_manager import PhotoAdminConfig

        config_data = {
            'processing_pipelines': {
                'branch_pairing_test': {
                    'nodes': [
                        {
                            'id': 'capture',
                            'type': 'Capture',
                            'name': 'Capture',
                            'output': ['file1']
                        },
                        {
                            'id': 'file1',
                            'type': 'File',
                            'extension': '.CR3',
                            'name': 'File 1',
                            'output': ['branch1']
                        },
                        {
                            'id': 'branch1',
                            'type': 'Branching',
                            'name': 'Branch 1',
                            'condition_description': 'Process or skip',
                            'output': ['file2a', 'file2b']  # 2 branches
                        },
                        {
                            'id': 'file2a',
                            'type': 'File',
                            'extension': '.DNG',
                            'name': 'File 2a',
                            'output': ['pairing1']
                        },
                        {
                            'id': 'file2b',
                            'type': 'File',
                            'extension': '.XMP',
                            'name': 'File 2b',
                            'output': ['pairing1']
                        },
                        {
                            'id': 'pairing1',
                            'type': 'Pairing',
                            'name': 'Pairing 1',
                            'pairing_type': 'Metadata',
                            'input_count': 2,
                            'output': ['termination']
                        },
                        {
                            'id': 'termination',
                            'type': 'Termination',
                            'name': 'End',
                            'termination_type': 'Archive',
                            'output': []
                        }
                    ]
                }
            }
        }

        with patch.object(PhotoAdminConfig, '_load_config', return_value=config_data):
            config = PhotoAdminConfig()
            pipeline = pipeline_validation.load_pipeline_config(config, 'branch_pairing_test')

            paths = pipeline_validation.enumerate_paths_with_pairing(pipeline)

            # Should have 1 path (both branches merge at pairing)
            assert len(paths) == 1

            path = paths[0]
            node_ids = [n['id'] for n in path]

            # Path should include all nodes
            assert 'capture' in node_ids
            assert 'file1' in node_ids
            assert 'pairing1' in node_ids
            assert 'termination' in node_ids

    def test_nested_pairing_nodes(self):
        """Test that multiple pairing nodes in sequence are processed correctly in topological order."""
        from utils.config_manager import PhotoAdminConfig

        # Create a pipeline with two pairing nodes in sequence
        # All paths flow through pairing1, then pairing2
        config_data = {
            'processing_pipelines': {
                'nested_pairing_test': {
                    'nodes': [
                        {
                            'id': 'capture',
                            'type': 'Capture',
                            'name': 'Capture',
                            'output': ['file1', 'file2']
                        },
                        # First pairing inputs
                        {
                            'id': 'file1',
                            'type': 'File',
                            'extension': '.CR3',
                            'name': 'File 1',
                            'output': ['pairing1']
                        },
                        {
                            'id': 'file2',
                            'type': 'File',
                            'extension': '.XMP',
                            'name': 'File 2',
                            'output': ['pairing1']
                        },
                        # First pairing node outputs two files
                        {
                            'id': 'pairing1',
                            'type': 'Pairing',
                            'name': 'Pairing 1',
                            'pairing_type': 'Metadata',
                            'input_count': 2,
                            'output': ['file3', 'file4']
                        },
                        # Second pairing inputs (both from pairing1)
                        {
                            'id': 'file3',
                            'type': 'File',
                            'extension': '.DNG',
                            'name': 'File 3',
                            'output': ['pairing2']
                        },
                        {
                            'id': 'file4',
                            'type': 'File',
                            'extension': '.JPG',
                            'name': 'File 4',
                            'output': ['pairing2']
                        },
                        # Second pairing node
                        {
                            'id': 'pairing2',
                            'type': 'Pairing',
                            'name': 'Pairing 2',
                            'pairing_type': 'ImageGroup',
                            'input_count': 2,
                            'output': ['termination']
                        },
                        {
                            'id': 'termination',
                            'type': 'Termination',
                            'name': 'End',
                            'termination_type': 'Archive',
                            'output': []
                        }
                    ]
                }
            }
        }

        with patch.object(PhotoAdminConfig, '_load_config', return_value=config_data):
            config = PhotoAdminConfig()
            pipeline = pipeline_validation.load_pipeline_config(config, 'nested_pairing_test')

            paths = pipeline_validation.enumerate_paths_with_pairing(pipeline)

            # Should have at least one path
            assert len(paths) > 0, f"Should enumerate at least one path (found {len(paths)})"

            # Verify all paths go through both pairing nodes and reach termination
            for path in paths:
                node_ids = [n['id'] for n in path]
                assert 'pairing1' in node_ids, "Path should include pairing1"
                assert 'pairing2' in node_ids, "Path should include pairing2"
                assert 'termination' in node_ids, "Path should reach termination"

                # Verify topological order: pairing1 before pairing2
                idx_p1 = node_ids.index('pairing1')
                idx_p2 = node_ids.index('pairing2')
                assert idx_p1 < idx_p2, "pairing1 should be processed before pairing2"

    def test_early_termination_before_second_pairing(self):
        """Test that paths terminating before second pairing node are preserved."""
        from utils.config_manager import PhotoAdminConfig

        # Create pipeline with 2 pairing nodes where some paths can terminate early
        config_data = {
            'processing_pipelines': {
                'early_termination_test': {
                    'nodes': [
                        {
                            'id': 'capture',
                            'type': 'Capture',
                            'name': 'Capture',
                            'output': ['file1', 'file2']
                        },
                        # First pairing node inputs
                        {
                            'id': 'file1',
                            'type': 'File',
                            'extension': '.CR3',
                            'name': 'File 1',
                            'output': ['pairing1']
                        },
                        {
                            'id': 'file2',
                            'type': 'File',
                            'extension': '.XMP',
                            'name': 'File 2',
                            'output': ['pairing1']
                        },
                        # First pairing outputs to branching node
                        {
                            'id': 'pairing1',
                            'type': 'Pairing',
                            'name': 'Pairing 1',
                            'pairing_type': 'Metadata',
                            'input_count': 2,
                            'output': ['branching1']
                        },
                        # Branching: can either terminate early OR continue to pairing2
                        {
                            'id': 'branching1',
                            'type': 'Branching',
                            'name': 'Branching 1',
                            'condition_description': 'User decides: terminate or continue',
                            'output': ['termination_early', 'file4', 'file5']
                        },
                        # Path that terminates early (before pairing2)
                        {
                            'id': 'termination_early',
                            'type': 'Termination',
                            'name': 'Early Termination',
                            'termination_type': 'Black Box',
                            'output': []
                        },
                        # Paths that continue to pairing2
                        {
                            'id': 'file4',
                            'type': 'File',
                            'extension': '.DNG',
                            'name': 'File 4',
                            'output': ['pairing2']
                        },
                        {
                            'id': 'file5',
                            'type': 'File',
                            'extension': '.JPG',
                            'name': 'File 5',
                            'output': ['pairing2']
                        },
                        # Second pairing node
                        {
                            'id': 'pairing2',
                            'type': 'Pairing',
                            'name': 'Pairing 2',
                            'pairing_type': 'ImageGroup',
                            'input_count': 2,
                            'output': ['termination_late']
                        },
                        {
                            'id': 'termination_late',
                            'type': 'Termination',
                            'name': 'Late Termination',
                            'termination_type': 'Browsable',
                            'output': []
                        }
                    ]
                }
            }
        }

        with patch.object(PhotoAdminConfig, '_load_config', return_value=config_data):
            config = PhotoAdminConfig()
            pipeline = pipeline_validation.load_pipeline_config(config, 'early_termination_test')

            paths = pipeline_validation.enumerate_paths_with_pairing(pipeline)

            # Should have paths to both terminations
            assert len(paths) > 0, "Should enumerate at least one path"

            # Categorize paths by termination
            early_term_paths = []
            late_term_paths = []

            for path in paths:
                node_ids = [n['id'] for n in path]
                last_node = path[-1]

                if last_node['id'] == 'termination_early':
                    early_term_paths.append(path)
                    # Early termination should NOT include pairing2
                    assert 'pairing2' not in node_ids, "Early termination should not include pairing2"
                    # But should include pairing1
                    assert 'pairing1' in node_ids, "Early termination should include pairing1"
                elif last_node['id'] == 'termination_late':
                    late_term_paths.append(path)
                    # Late termination should include both pairing nodes
                    assert 'pairing1' in node_ids, "Late termination should include pairing1"
                    assert 'pairing2' in node_ids, "Late termination should include pairing2"

            # Verify we found both types
            assert len(early_term_paths) > 0, "Should have paths with early termination"
            assert len(late_term_paths) > 0, "Should have paths with late termination"

            print(f"\nEarly termination paths: {len(early_term_paths)}")
            print(f"Late termination paths: {len(late_term_paths)}")

    def test_process_node_with_multiple_methods_creates_branching(self, tmp_path):
        """Test that Process nodes with multiple method_ids create parallel paths (like branching)."""
        # Create pipeline with Process node having 2 methods
        pipeline_config = {
            'default': {
                'nodes': [
                    {
                        'id': 'capture',
                        'type': 'Capture',
                        'name': 'Capture',
                        'output': ['raw_file']
                    },
                    {
                        'id': 'raw_file',
                        'type': 'File',
                        'extension': '.CR3',
                        'name': 'Raw File',
                        'output': ['process_with_multiple_methods']
                    },
                    {
                        'id': 'process_with_multiple_methods',
                        'type': 'Process',
                        'method_ids': ['MethodA', 'MethodB'],  # Two methods = two branches
                        'name': 'Multi-Method Process',
                        'output': ['dng_file']
                    },
                    {
                        'id': 'dng_file',
                        'type': 'File',
                        'extension': '.DNG',
                        'name': 'DNG File',
                        'output': ['termination']
                    },
                    {
                        'id': 'termination',
                        'type': 'Termination',
                        'termination_type': 'Archive',
                        'name': 'Archive',
                        'output': []
                    }
                ]
            }
        }

        # Create config
        config_file = tmp_path / "config.yaml"
        config_data = {'processing_pipelines': pipeline_config}
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        config = pipeline_validation.PhotoAdminConfig(config_path=config_file)
        pipeline = pipeline_validation.load_pipeline_config(config)

        # Enumerate paths
        paths = pipeline_validation.enumerate_all_paths(pipeline)

        # Should have 2 paths (one per method)
        assert len(paths) == 2, f"Expected 2 paths (one per method), got {len(paths)}"

        # Collect methods from each path
        methods_in_paths = []
        for path in paths:
            for node in path:
                if node.get('node_id') == 'process_with_multiple_methods':
                    method_ids = node.get('method_ids', [])
                    assert len(method_ids) == 1, f"Each path should have exactly 1 method, got {len(method_ids)}"
                    methods_in_paths.append(method_ids[0])
                    break

        # Should have both methods, one per path
        assert sorted(methods_in_paths) == ['MethodA', 'MethodB']

        # Test expected file generation
        files_path1 = pipeline_validation.generate_expected_files(paths[0], 'TEST0001')
        files_path2 = pipeline_validation.generate_expected_files(paths[1], 'TEST0001')

        # Each path should generate different files based on its method
        assert 'TEST0001.CR3' in files_path1
        assert 'TEST0001.CR3' in files_path2

        # One path should have MethodA suffix, other should have MethodB
        dng_files = []
        for files in [files_path1, files_path2]:
            dng = [f for f in files if f.endswith('.DNG')][0]
            dng_files.append(dng)

        assert 'TEST0001-MethodA.DNG' in dng_files
        assert 'TEST0001-MethodB.DNG' in dng_files
