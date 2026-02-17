"""
Unit tests for path_stats feature in pipeline_analyzer module.

Tests the _determine_image_path helper and the path_stats output
from run_pipeline_validation.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # For utils

from src.remote.base import FileInfo
from src.analysis.pipeline_analyzer import (
    run_pipeline_validation,
    _determine_image_path,
    flatten_imagegroups_to_specific_images,
)
from utils.pipeline_processor import (
    SpecificImage,
    ValidationResult,
    ValidationStatus,
    PipelineConfig,
    TerminationMatchResult,
)


# =============================================================================
# Fixtures
# =============================================================================

def _make_file_info(name: str, size: int = 1000) -> FileInfo:
    """Helper to create a FileInfo with sensible defaults."""
    return FileInfo(path=name, size=size)


def _make_specific_image(
    camera_id: str = "AB3D",
    counter: str = "0001",
    suffix: str = "",
    properties: list = None,
    files: list = None,
) -> SpecificImage:
    """Helper to create a SpecificImage with sensible defaults."""
    props = properties if properties is not None else []
    base = f"{camera_id}{counter}"
    if suffix:
        base = f"{base}-{suffix}"
    fls = files if files is not None else [f"{base}.dng"]
    return SpecificImage(
        base_filename=base,
        camera_id=camera_id,
        counter=counter,
        suffix=suffix,
        properties=props,
        files=fls,
    )


def _make_validation_result(
    specific_image: SpecificImage,
    overall_status: ValidationStatus = ValidationStatus.CONSISTENT,
    termination_matches: list = None,
) -> ValidationResult:
    """Helper to create a ValidationResult with sensible defaults."""
    if termination_matches is None:
        termination_matches = []
    return ValidationResult(
        base_filename=specific_image.base_filename,
        camera_id=specific_image.camera_id,
        counter=specific_image.counter,
        suffix=specific_image.suffix,
        properties=specific_image.properties,
        actual_files=specific_image.files,
        termination_matches=termination_matches,
        overall_status=overall_status,
        overall_archival_ready=(overall_status in (
            ValidationStatus.CONSISTENT,
            ValidationStatus.CONSISTENT_WITH_WARNING,
        )),
    )


def _make_term_match(
    termination_type: str = "Done",
    status: ValidationStatus = ValidationStatus.CONSISTENT,
    expected_files: list = None,
) -> TerminationMatchResult:
    """Helper to create a TerminationMatchResult."""
    exp = expected_files if expected_files is not None else ["AB3D0001.dng"]
    return TerminationMatchResult(
        termination_type=termination_type,
        status=status,
        expected_files=exp,
        missing_files=[],
        extra_files=[],
        actual_files=exp,
        completion_percentage=100.0,
        is_archival_ready=True,
    )


@pytest.fixture
def simple_pipeline_config():
    """
    A mock PipelineConfig for a simple Capture -> Raw(.dng) -> Done pipeline.
    The actual config object is mocked since we patch the functions that use it.
    """
    config = MagicMock(spec=PipelineConfig)
    config.nodes = []
    config.capture_nodes = []
    config.file_nodes = []
    config.process_nodes = []
    config.pairing_nodes = []
    config.branching_nodes = []
    config.termination_nodes = []
    return config


@pytest.fixture
def branching_pipeline_config():
    """
    A mock PipelineConfig for a pipeline with two branches:
    Capture -> Raw(.dng) -> TermA  (Done)
    Capture -> XMP(.xmp) -> TermB  (Archive)
    """
    config = MagicMock(spec=PipelineConfig)
    config.nodes = []
    config.capture_nodes = []
    config.file_nodes = []
    config.process_nodes = []
    config.pairing_nodes = []
    config.branching_nodes = []
    config.termination_nodes = []
    return config


@pytest.fixture
def sample_dng_files():
    """Five .dng FileInfo objects."""
    return [
        _make_file_info(f"AB3D{str(i).zfill(4)}.dng")
        for i in range(1, 6)
    ]


# Path data for a simple single-path pipeline:
#   Capture(cap1) -> File(file1, .dng) -> Termination(term1, Done)
SINGLE_PATH = [
    {"id": "cap1", "type": "Capture", "name": "Capture"},
    {"id": "file1", "type": "File", "name": "Raw", "extension": ".dng"},
    {"id": "term1", "type": "Termination", "name": "Done", "term_type": "Done"},
]

# Path data for a branching pipeline with two termination types:
BRANCH_PATH_A = [
    {"id": "cap1", "type": "Capture", "name": "Capture"},
    {"id": "file1", "type": "File", "name": "Raw", "extension": ".dng"},
    {"id": "termA", "type": "Termination", "name": "Done", "term_type": "Done"},
]

BRANCH_PATH_B = [
    {"id": "cap1", "type": "Capture", "name": "Capture"},
    {"id": "file2", "type": "File", "name": "XMP", "extension": ".xmp"},
    {"id": "termB", "type": "Termination", "name": "Archive", "term_type": "Archive"},
]


# Common patch base for mocking pipeline_analyzer dependencies
PATCH_BASE = "src.analysis.pipeline_analyzer"


# =============================================================================
# Tests for _determine_image_path
# =============================================================================


class TestDetermineImagePath:
    """Tests for the _determine_image_path helper function."""

    def test_returns_none_when_no_termination_matches(self):
        """When validation has no termination matches, returns None."""
        si = _make_specific_image()
        vr = _make_validation_result(si, termination_matches=[])
        paths_by_term = {}
        path_cache = {}

        result = _determine_image_path(si, vr, paths_by_term, path_cache)

        assert result is None

    def test_single_path_returns_node_ids(self):
        """When there is exactly one path for the termination type, returns its node IDs."""
        si = _make_specific_image()
        term = _make_term_match(termination_type="Done", expected_files=["AB3D0001.dng"])
        vr = _make_validation_result(si, termination_matches=[term])

        node_ids = ("cap1", "file1", "term1")
        paths_by_term = {"Done": [(node_ids, SINGLE_PATH)]}
        path_cache = {}

        result = _determine_image_path(si, vr, paths_by_term, path_cache)

        assert result == node_ids

    def test_returns_none_when_term_type_not_in_paths(self):
        """When the best termination type has no matching paths, returns None."""
        si = _make_specific_image()
        term = _make_term_match(termination_type="Unknown")
        vr = _make_validation_result(si, termination_matches=[term])

        paths_by_term = {"Done": [(("cap1", "file1", "term1"), SINGLE_PATH)]}
        path_cache = {}

        result = _determine_image_path(si, vr, paths_by_term, path_cache)

        assert result is None

    def test_cache_hit_avoids_recomputation(self):
        """Cached results are returned directly for identical (properties, suffix, term_type)."""
        si = _make_specific_image(properties=["HDR"])
        term = _make_term_match(termination_type="Done", expected_files=["AB3D0001.dng"])
        vr = _make_validation_result(si, termination_matches=[term])

        path_a = ("cap1", "file1", "termA")
        path_b = ("cap1", "file2", "termB")
        paths_by_term = {
            "Done": [(path_a, BRANCH_PATH_A), (path_b, BRANCH_PATH_B)]
        }
        # Pre-populate cache
        cache_key = (("HDR",), "", "Done")
        path_cache = {cache_key: path_a}

        result = _determine_image_path(si, vr, paths_by_term, path_cache)

        assert result == path_a

    def test_multiple_paths_selects_by_expected_files(self):
        """When multiple paths exist, selects by matching expected files."""
        si = _make_specific_image(files=["AB3D0001.dng"])
        term = _make_term_match(
            termination_type="Done",
            expected_files=["AB3D0001.dng"],
        )
        vr = _make_validation_result(si, termination_matches=[term])

        path_a_ids = ("cap1", "file1", "termA")
        path_b_ids = ("cap1", "file2", "termB")

        # Path A expects AB3D0001.dng, path B expects AB3D0001.xmp
        path_a_data = [
            {"id": "cap1", "type": "Capture", "name": "Capture"},
            {"id": "file1", "type": "File", "name": "Raw", "extension": ".dng"},
            {"id": "termA", "type": "Termination", "name": "Done", "term_type": "Done"},
        ]
        path_b_data = [
            {"id": "cap1", "type": "Capture", "name": "Capture"},
            {"id": "file2", "type": "File", "name": "XMP", "extension": ".xmp"},
            {"id": "termB", "type": "Termination", "name": "Done", "term_type": "Done"},
        ]

        paths_by_term = {
            "Done": [(path_a_ids, path_a_data), (path_b_ids, path_b_data)]
        }
        path_cache = {}

        # generate_expected_files is called inside _determine_image_path for multi-path.
        # We need to patch it so it returns deterministic results.
        with patch(f"{PATCH_BASE}.generate_expected_files") as mock_gen:
            def side_effect(path_data, base, suffix):
                last = path_data[-1]
                if last["id"] == "termA":
                    return ["AB3D0001.dng"]
                else:
                    return ["AB3D0001.xmp"]

            mock_gen.side_effect = side_effect

            result = _determine_image_path(si, vr, paths_by_term, path_cache)

        assert result == path_a_ids
        # Cache should be populated (key includes expected files signature)
        assert ((), "", "Done", ("ab3d0001.dng",)) in path_cache


# =============================================================================
# Tests for path_stats in run_pipeline_validation
# =============================================================================


class TestPathStats:
    """Tests for path_stats in pipeline validation output."""

    @patch(f"{PATCH_BASE}.build_imagegroups")
    @patch(f"{PATCH_BASE}.validate_specific_image")
    @patch(f"{PATCH_BASE}.enumerate_paths_with_pairing")
    def test_path_stats_included_in_output(
        self,
        mock_enumerate,
        mock_validate,
        mock_build,
        simple_pipeline_config,
    ):
        """Verify that run_pipeline_validation returns a path_stats key."""
        # Setup: one image group producing one specific image
        mock_build.return_value = {
            "imagegroups": [
                {
                    "group_id": "AB3D0001",
                    "camera_id": "AB3D",
                    "counter": "0001",
                    "separate_images": {
                        "": {"files": ["AB3D0001.dng"], "properties": []},
                    },
                }
            ],
            "invalid_files": [],
        }

        # Pipeline has one path: cap1 -> file1 -> term1
        mock_enumerate.return_value = [SINGLE_PATH]

        # Validation returns consistent for the single image
        si = _make_specific_image()
        term = _make_term_match(termination_type="Done", expected_files=["AB3D0001.dng"])
        vr = _make_validation_result(si, termination_matches=[term])
        mock_validate.return_value = vr

        files = [_make_file_info("AB3D0001.dng")]
        result = run_pipeline_validation(
            files, simple_pipeline_config, {".dng"}, {".xmp"}
        )

        assert "path_stats" in result
        assert isinstance(result["path_stats"], list)

    @patch(f"{PATCH_BASE}.build_imagegroups")
    @patch(f"{PATCH_BASE}.validate_specific_image")
    @patch(f"{PATCH_BASE}.enumerate_paths_with_pairing")
    def test_single_path_all_images_same_path(
        self,
        mock_enumerate,
        mock_validate,
        mock_build,
        simple_pipeline_config,
        sample_dng_files,
    ):
        """Five images all following the same single path produce one path_stats entry with count 5."""
        # Build 5 image groups (one per file)
        imagegroups = []
        for i in range(1, 6):
            counter = str(i).zfill(4)
            name = f"AB3D{counter}"
            imagegroups.append({
                "group_id": name,
                "camera_id": "AB3D",
                "counter": counter,
                "separate_images": {
                    "": {"files": [f"{name}.dng"], "properties": []},
                },
            })

        mock_build.return_value = {
            "imagegroups": imagegroups,
            "invalid_files": [],
        }

        # Single path through pipeline
        mock_enumerate.return_value = [SINGLE_PATH]

        # Each validation returns consistent with a Done termination
        def validate_side_effect(specific_image, pipeline, show_progress=False):
            term = _make_term_match(
                termination_type="Done",
                expected_files=[f"{specific_image.base_filename}.dng"],
            )
            return _make_validation_result(specific_image, termination_matches=[term])

        mock_validate.side_effect = validate_side_effect

        result = run_pipeline_validation(
            sample_dng_files, simple_pipeline_config, {".dng"}, {".xmp"}
        )

        path_stats = result["path_stats"]
        assert len(path_stats) == 1
        assert path_stats[0]["image_count"] == 5
        assert path_stats[0]["path"] == ["cap1", "file1", "term1"]

    @patch(f"{PATCH_BASE}.build_imagegroups")
    @patch(f"{PATCH_BASE}.validate_specific_image")
    @patch(f"{PATCH_BASE}.enumerate_paths_with_pairing")
    def test_branching_pipeline_separate_counts(
        self,
        mock_enumerate,
        mock_validate,
        mock_build,
        branching_pipeline_config,
    ):
        """
        Branching pipeline: 3 images go to path A (Done), 2 images go to path B (Archive).
        path_stats should have 2 entries with counts 3 and 2.
        """
        # Create 5 image groups: first 3 have .dng files, last 2 have .xmp files
        imagegroups = []
        all_files = []
        for i in range(1, 6):
            counter = str(i).zfill(4)
            name = f"AB3D{counter}"
            if i <= 3:
                ext = ".dng"
            else:
                ext = ".xmp"
            fname = f"{name}{ext}"
            imagegroups.append({
                "group_id": name,
                "camera_id": "AB3D",
                "counter": counter,
                "separate_images": {
                    "": {"files": [fname], "properties": []},
                },
            })
            all_files.append(_make_file_info(fname))

        mock_build.return_value = {
            "imagegroups": imagegroups,
            "invalid_files": [],
        }

        # Two paths in the pipeline
        mock_enumerate.return_value = [BRANCH_PATH_A, BRANCH_PATH_B]

        # Validation: images 1-3 match "Done" termination, images 4-5 match "Archive"
        def validate_side_effect(specific_image, pipeline, show_progress=False):
            counter_int = int(specific_image.counter)
            if counter_int <= 3:
                term = _make_term_match(
                    termination_type="Done",
                    expected_files=[f"{specific_image.base_filename}.dng"],
                )
            else:
                term = _make_term_match(
                    termination_type="Archive",
                    expected_files=[f"{specific_image.base_filename}.xmp"],
                )
            return _make_validation_result(specific_image, termination_matches=[term])

        mock_validate.side_effect = validate_side_effect

        result = run_pipeline_validation(
            all_files, branching_pipeline_config, {".dng", ".xmp"}, set()
        )

        path_stats = result["path_stats"]
        assert len(path_stats) == 2

        # Build a lookup by path for easier assertions
        stats_by_path = {tuple(ps["path"]): ps["image_count"] for ps in path_stats}

        path_a = ("cap1", "file1", "termA")
        path_b = ("cap1", "file2", "termB")

        assert stats_by_path[path_a] == 3
        assert stats_by_path[path_b] == 2

    @patch(f"{PATCH_BASE}.build_imagegroups")
    @patch(f"{PATCH_BASE}.validate_specific_image")
    @patch(f"{PATCH_BASE}.enumerate_paths_with_pairing")
    def test_existing_fields_unchanged(
        self,
        mock_enumerate,
        mock_validate,
        mock_build,
        simple_pipeline_config,
        sample_dng_files,
    ):
        """
        Verify that existing output fields (status_counts, by_termination,
        validation_results, total_images, invalid_files) remain present and correct.
        """
        imagegroups = []
        for i in range(1, 6):
            counter = str(i).zfill(4)
            name = f"AB3D{counter}"
            imagegroups.append({
                "group_id": name,
                "camera_id": "AB3D",
                "counter": counter,
                "separate_images": {
                    "": {"files": [f"{name}.dng"], "properties": []},
                },
            })

        mock_build.return_value = {
            "imagegroups": imagegroups,
            "invalid_files": ["bad_file.txt"],
        }

        mock_enumerate.return_value = [SINGLE_PATH]

        # 3 consistent, 1 partial, 1 inconsistent
        call_count = [0]

        def validate_side_effect(specific_image, pipeline, show_progress=False):
            call_count[0] += 1
            idx = call_count[0]

            if idx <= 3:
                status = ValidationStatus.CONSISTENT
                term_status = ValidationStatus.CONSISTENT
            elif idx == 4:
                status = ValidationStatus.PARTIAL
                term_status = ValidationStatus.PARTIAL
            else:
                status = ValidationStatus.INCONSISTENT
                term_status = ValidationStatus.INCONSISTENT

            term = _make_term_match(
                termination_type="Done",
                status=term_status,
                expected_files=[f"{specific_image.base_filename}.dng"],
            )
            return _make_validation_result(
                specific_image,
                overall_status=status,
                termination_matches=[term],
            )

        mock_validate.side_effect = validate_side_effect

        result = run_pipeline_validation(
            sample_dng_files, simple_pipeline_config, {".dng"}, {".xmp"}
        )

        # Check all expected keys are present
        assert "total_images" in result
        assert "total_groups" in result
        assert "status_counts" in result
        assert "by_termination" in result
        assert "validation_results" in result
        assert "invalid_files_count" in result
        assert "invalid_files" in result
        assert "path_stats" in result

        # Check values
        assert result["total_images"] == 5
        assert result["total_groups"] == 5

        assert result["status_counts"]["consistent"] == 3
        assert result["status_counts"]["partial"] == 1
        assert result["status_counts"]["inconsistent"] == 1
        assert result["status_counts"]["consistent_with_warning"] == 0

        assert result["invalid_files_count"] == 1
        assert result["invalid_files"] == ["bad_file.txt"]

        assert len(result["validation_results"]) == 5

        # by_termination merges CONSISTENT_WITH_WARNING into CONSISTENT
        assert "Done" in result["by_termination"]
        term_done = result["by_termination"]["Done"]
        assert term_done["CONSISTENT"] == 3  # 3 consistent (no warnings to merge)
        assert term_done["PARTIAL"] == 1
        assert term_done["INCONSISTENT"] == 1

    @patch(f"{PATCH_BASE}.build_imagegroups")
    @patch(f"{PATCH_BASE}.enumerate_paths_with_pairing")
    def test_empty_collection_empty_path_stats(
        self,
        mock_enumerate,
        mock_build,
        simple_pipeline_config,
    ):
        """When no files are provided, path_stats should be an empty list."""
        mock_build.return_value = {
            "imagegroups": [],
            "invalid_files": [],
        }
        mock_enumerate.return_value = [SINGLE_PATH]

        result = run_pipeline_validation(
            [], simple_pipeline_config, {".dng"}, {".xmp"}
        )

        assert result["path_stats"] == []
        assert result["total_images"] == 0
        assert result["total_groups"] == 0
        assert result["validation_results"] == []
