"""
Unit tests for the ReportRenderer and related data structures.
"""

import pytest
from datetime import datetime
from pathlib import Path
import os

from utils.report_renderer import (
    ReportRenderer,
    ReportContext,
    KPICard,
    ReportSection,
    WarningMessage,
    ErrorMessage
)


class TestDataClasses:
    """Test the data class structures."""

    def test_kpi_card_creation(self):
        """Test KPICard dataclass initialization."""
        kpi = KPICard(
            title="Total Photos",
            value="1,234",
            status="success",
            unit="files",
            tooltip="Total number of photos found"
        )
        assert kpi.title == "Total Photos"
        assert kpi.value == "1,234"
        assert kpi.status == "success"
        assert kpi.unit == "files"

    def test_report_section_chart(self):
        """Test ReportSection with chart data."""
        section = ReportSection(
            title="File Distribution",
            type="chart_bar",
            data={"labels": ["DNG", "CR3"], "values": [100, 50]}
        )
        assert section.title == "File Distribution"
        assert section.type == "chart_bar"
        assert section.data["labels"] == ["DNG", "CR3"]

    def test_warning_message_defaults(self):
        """Test WarningMessage with default values."""
        warning = WarningMessage(message="Test warning")
        assert warning.message == "Test warning"
        assert warning.severity == "medium"
        assert warning.details is None

    def test_error_message_with_fix(self):
        """Test ErrorMessage with actionable fix."""
        error = ErrorMessage(
            message="Invalid filename",
            details=["file1.dng", "file2.cr3"],
            actionable_fix="Rename files using correct pattern"
        )
        assert error.message == "Invalid filename"
        assert len(error.details) == 2
        assert error.actionable_fix is not None


class TestReportRenderer:
    """Test the ReportRenderer class."""

    @pytest.fixture
    def sample_context(self):
        """Create a sample ReportContext for testing."""
        return ReportContext(
            tool_name="Test Tool",
            tool_version="1.0.0",
            scan_path="/test/path",
            scan_timestamp=datetime(2025, 12, 25, 10, 30, 0),
            scan_duration=12.5,
            kpis=[
                KPICard(
                    title="Total Files",
                    value="100",
                    status="success",
                    unit="files"
                ),
                KPICard(
                    title="Issues Found",
                    value="5",
                    status="warning",
                    unit="issues"
                )
            ],
            sections=[
                ReportSection(
                    title="File Distribution",
                    type="chart_bar",
                    data={
                        "labels": ["DNG", "CR3", "XMP"],
                        "values": [50, 30, 20]
                    }
                ),
                ReportSection(
                    title="Issue List",
                    type="table",
                    data={
                        "headers": ["File", "Issue"],
                        "rows": [
                            ["test.dng", "Missing sidecar"],
                            ["test2.cr3", "Orphaned file"]
                        ]
                    }
                )
            ],
            warnings=[
                WarningMessage(
                    message="Minor issue detected",
                    details=["Detail 1", "Detail 2"]
                )
            ]
        )

    def test_renderer_initialization(self):
        """Test ReportRenderer initialization."""
        renderer = ReportRenderer()
        assert renderer.env is not None

    def test_successful_rendering(self, sample_context, tmp_path):
        """Test successful HTML report rendering."""
        renderer = ReportRenderer()
        output_file = tmp_path / "test_report.html"

        # Render report (will use base.html.j2)
        renderer.render_report(
            context=sample_context,
            template_name="base.html.j2",
            output_path=str(output_file)
        )

        # Verify file was created
        assert output_file.exists()

        # Verify content contains expected elements
        content = output_file.read_text(encoding='utf-8')
        assert "Test Tool" in content
        assert "Total Files" in content
        assert "100" in content
        assert "File Distribution" in content
        assert "Minor issue detected" in content

    def test_atomic_file_write(self, sample_context, tmp_path):
        """Test that file writing is atomic (temp file → rename)."""
        renderer = ReportRenderer()
        output_file = tmp_path / "test_report.html"

        renderer.render_report(
            context=sample_context,
            template_name="base.html.j2",
            output_path=str(output_file)
        )

        # Verify final file exists
        assert output_file.exists()

        # Verify no temp file remains
        temp_file = tmp_path / "test_report.html.tmp"
        assert not temp_file.exists()

    def test_template_not_found_error(self, sample_context, tmp_path):
        """Test error handling when template doesn't exist."""
        renderer = ReportRenderer()
        output_file = tmp_path / "test_report.html"

        with pytest.raises(Exception) as exc_info:
            renderer.render_report(
                context=sample_context,
                template_name="nonexistent.html.j2",
                output_path=str(output_file)
            )

        assert "not found" in str(exc_info.value).lower()

    def test_list_available_templates(self):
        """Test listing available templates."""
        renderer = ReportRenderer()
        templates = renderer._list_available_templates()

        # Should at least have base.html.j2
        assert "base.html.j2" in templates


class TestVisualConsistency:
    """Integration tests for visual consistency across tools."""

    @pytest.fixture
    def photostats_context(self):
        """Sample context mimicking PhotoStats data."""
        return ReportContext(
            tool_name="PhotoStats",
            tool_version="1.0.0",
            scan_path="/test/photos",
            scan_timestamp=datetime.now(),
            scan_duration=10.0,
            kpis=[
                KPICard("Total Photos", "500", "success", "files"),
                KPICard("Orphaned", "10", "warning", "files")
            ],
            sections=[
                ReportSection(
                    "File Types",
                    "chart_pie",
                    data={"labels": ["DNG", "CR3"], "values": [300, 200]}
                )
            ]
        )

    @pytest.fixture
    def photo_pairing_context(self):
        """Sample context mimicking Photo Pairing data."""
        return ReportContext(
            tool_name="Photo Pairing",
            tool_version="1.0.0",
            scan_path="/test/photos",
            scan_timestamp=datetime.now(),
            scan_duration=8.0,
            kpis=[
                KPICard("Cameras Found", "3", "info", "cameras"),
                KPICard("Invalid Names", "2", "danger", "files")
            ],
            sections=[
                ReportSection(
                    "Camera Usage",
                    "chart_bar",
                    data={"labels": ["Canon", "Nikon"], "values": [250, 250]}
                )
            ]
        )

    def test_consistent_css_classes(
        self,
        photostats_context,
        photo_pairing_context,
        tmp_path
    ):
        """Verify both tools use same CSS classes."""
        renderer = ReportRenderer()

        ps_file = tmp_path / "photostats.html"
        pp_file = tmp_path / "photopairing.html"

        renderer.render_report(photostats_context, "base.html.j2", str(ps_file))
        renderer.render_report(photo_pairing_context, "base.html.j2", str(pp_file))

        ps_content = ps_file.read_text(encoding='utf-8')
        pp_content = pp_file.read_text(encoding='utf-8')

        # Check for consistent CSS classes
        common_classes = [
            "kpi-card",
            "section-title",
            "chart-container",
            "metadata",
            "message-box"
        ]

        for css_class in common_classes:
            assert css_class in ps_content, f"{css_class} not in PhotoStats report"
            assert css_class in pp_content, f"{css_class} not in Photo Pairing report"

    def test_consistent_color_variables(
        self,
        photostats_context,
        photo_pairing_context,
        tmp_path
    ):
        """Verify both tools use same color theme variables."""
        renderer = ReportRenderer()

        ps_file = tmp_path / "photostats.html"
        pp_file = tmp_path / "photopairing.html"

        renderer.render_report(photostats_context, "base.html.j2", str(ps_file))
        renderer.render_report(photo_pairing_context, "base.html.j2", str(pp_file))

        ps_content = ps_file.read_text(encoding='utf-8')
        pp_content = pp_file.read_text(encoding='utf-8')

        # Check for consistent color theme
        color_vars = [
            "--color-primary",
            "--color-success",
            "--color-warning",
            "--color-danger",
            "--gradient-purple"
        ]

        for var in color_vars:
            assert var in ps_content
            assert var in pp_content

    def test_consistent_chart_colors(
        self,
        photostats_context,
        photo_pairing_context,
        tmp_path
    ):
        """Verify both tools use same Chart.js color palette."""
        renderer = ReportRenderer()

        ps_file = tmp_path / "photostats.html"
        pp_file = tmp_path / "photopairing.html"

        renderer.render_report(photostats_context, "base.html.j2", str(ps_file))
        renderer.render_report(photo_pairing_context, "base.html.j2", str(pp_file))

        ps_content = ps_file.read_text(encoding='utf-8')
        pp_content = pp_file.read_text(encoding='utf-8')

        # Check for Chart.js color constants
        assert "CHART_COLORS" in ps_content
        assert "CHART_COLORS" in pp_content

        # Check for specific colors in palette
        chart_color = "rgba(102, 126, 234, 0.8)"
        assert chart_color in ps_content
        assert chart_color in pp_content
