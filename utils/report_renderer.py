"""
HTML Report Renderer using Jinja2 templates.

This module provides centralized HTML report generation for all photo-admin tools,
ensuring consistent visual design across the toolbox.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import os
import sys
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateError
except ImportError:
    print("ERROR: Jinja2 is required. Install it with: pip install Jinja2>=3.1.0")
    sys.exit(1)


@dataclass
class KPICard:
    """A summary metric displayed prominently at the top of reports."""
    title: str
    value: str
    status: str  # "success", "info", "warning", "danger"
    unit: Optional[str] = None
    icon: Optional[str] = None
    tooltip: Optional[str] = None


@dataclass
class ReportSection:
    """A content block within the report (chart, table, or custom HTML)."""
    title: str
    type: str  # "chart_bar", "chart_pie", "chart_line", "table", "html"
    data: Optional[Dict[str, Any]] = None
    html_content: Optional[str] = None
    description: Optional[str] = None
    collapsible: bool = False


@dataclass
class WarningMessage:
    """A non-critical issue or concern found during analysis."""
    message: str
    details: Optional[List[str]] = None
    severity: str = "medium"  # "low", "medium", "high"


@dataclass
class ErrorMessage:
    """A critical issue that prevented full analysis or indicates data corruption."""
    message: str
    details: Optional[List[str]] = None
    actionable_fix: Optional[str] = None


@dataclass
class ReportContext:
    """Unified data structure passed to Jinja2 templates for rendering HTML reports."""
    tool_name: str
    tool_version: str
    scan_path: str
    scan_timestamp: datetime
    scan_duration: float
    kpis: List[KPICard]
    sections: List[ReportSection]
    warnings: List[WarningMessage] = field(default_factory=list)
    errors: List[ErrorMessage] = field(default_factory=list)
    footer_note: Optional[str] = None


class ReportRenderer:
    """
    Renders HTML reports using Jinja2 templates.

    This class provides a centralized way to generate consistent HTML reports
    across all photo-admin tools.
    """

    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize the ReportRenderer.

        Args:
            template_dir: Path to template directory. If None, uses 'templates/'
                         at repository root.
        """
        if template_dir is None:
            # Default to templates/ directory at repository root
            repo_root = Path(__file__).parent.parent
            template_dir = repo_root / "templates"

        if not Path(template_dir).exists():
            raise FileNotFoundError(
                f"Template directory not found: {template_dir}\n"
                f"Please ensure templates/ directory exists at repository root."
            )

        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )

    def render_report(
        self,
        context: ReportContext,
        template_name: str,
        output_path: str
    ) -> None:
        """
        Render an HTML report using a Jinja2 template.

        Args:
            context: ReportContext containing all data for the report
            template_name: Name of the template file (e.g., 'photo_stats.html.j2')
            output_path: Path where the HTML report should be saved

        Raises:
            TemplateNotFound: If the template file doesn't exist
            TemplateError: If template rendering fails
        """
        try:
            # Load template
            template = self.env.get_template(template_name)

            # Render template with context
            html_content = template.render(
                tool_name=context.tool_name,
                tool_version=context.tool_version,
                scan_path=context.scan_path,
                scan_timestamp=context.scan_timestamp,
                scan_duration=context.scan_duration,
                kpis=context.kpis,
                sections=context.sections,
                warnings=context.warnings,
                errors=context.errors,
                footer_note=context.footer_note
            )

            # Atomic file write: write to temp file first, then rename
            temp_path = f"{output_path}.tmp"
            try:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                # Atomic rename
                os.replace(temp_path, output_path)

            except Exception as e:
                # Clean up temp file if write failed
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise

        except TemplateNotFound as e:
            raise TemplateNotFound(
                f"Template '{template_name}' not found in templates/ directory.\n"
                f"Available templates: {self._list_available_templates()}"
            )
        except TemplateError as e:
            raise TemplateError(
                f"Error rendering template '{template_name}': {e}\n"
                f"Please check template syntax and data structure."
            )

    def _list_available_templates(self) -> List[str]:
        """List available templates in the template directory."""
        template_dir = Path(self.env.loader.searchpath[0])
        return [f.name for f in template_dir.glob("*.j2") if f.is_file()]
