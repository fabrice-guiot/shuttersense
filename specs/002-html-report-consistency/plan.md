# Implementation Plan: HTML Report Consistency & Tool Improvements

**Branch**: `002-html-report-consistency` | **Date**: 2025-12-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-html-report-consistency/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature introduces three major improvements to the photo-admin toolbox:

1. **Centralized HTML Template System**: Migrate both PhotoStats and Photo Pairing tools to use Jinja2 templates stored in `templates/` directory, ensuring consistent visual design across all reports (colors, typography, layout, KPI cards, charts, warnings, errors)

2. **Help Option Support**: Add `--help` and `-h` flags to all tools with comprehensive usage information including description, arguments, examples, and configuration notes

3. **Graceful CTRL+C Handling**: Implement signal handlers for clean interruption with user-friendly messages, proper exit codes (130), and prevention of partial report generation

**Technical Approach**: Use Jinja2 templating engine with shared base templates containing visual styling variables and Chart.js color configurations. Implement argument parsing with help text before tool initialization. Add signal handlers that catch SIGINT and perform clean shutdown.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: PyYAML (>=6.0), Jinja2 (new dependency)
**Storage**: File system (HTML reports, Jinja2 templates)
**Testing**: pytest (>=7.4.0), pytest-cov, pytest-mock
**Target Platform**: Cross-platform CLI (macOS, Linux, Windows)
**Project Type**: Single project with standalone CLI tools
**Performance Goals**: <1 second CTRL+C response time, maintain current report generation speed
**Constraints**: Tools must remain standalone scripts, backward compatibility with existing config, template failure must not break analysis
**Scale/Scope**: 2 existing tools (PhotoStats, Photo Pairing), 1 new shared template infrastructure

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Independent CLI Tools**: Both PhotoStats and Photo Pairing remain standalone Python scripts at repo root. They will use shared template infrastructure from `templates/` and new `utils/report_renderer.py` but can run independently. No cross-tool dependencies introduced.

- [x] **Testing & Quality**: pytest configured. Will add tests for: template rendering, help text display, signal handling, template error fallback. Target >80% coverage for new template infrastructure code.

- [x] **User-Centric Design**:
  - [x] HTML report generation is central to this feature with improved consistency
  - [x] Error messages will be clear (template missing/corrupted shows actionable console message)
  - [x] Implementation follows YAGNI (Jinja2 is sufficient, no complex framework)
  - [x] Structured logging remains (existing tools already have logging)
  - [x] **NEW**: `--help` and `-h` flags added to all tools with comprehensive usage info (Constitution v1.1.0 requirement)
  - [x] **NEW**: CTRL+C (SIGINT) handled gracefully with exit code 130 (Constitution v1.1.0 requirement)

- [x] **Shared Infrastructure**:
  - [x] Tools continue using PhotoAdminConfig from `utils/config_manager.py`
  - [x] New shared infrastructure: `templates/` directory and `utils/report_renderer.py`
  - [x] **NEW**: Centralized HTML templating with consistent styling (Constitution v1.1.0 requirement)
  - [x] Standard config locations maintained
  - [x] Report filename format preserved: `tool_name_report_YYYY-MM-DD_HH-MM-SS.html`

- [x] **Simplicity**:
  - [x] Jinja2 is industry-standard, not over-engineered
  - [x] Template structure kept simple with base template + tool-specific extensions
  - [x] Signal handling uses standard Python `signal` module
  - [x] Argument parsing uses standard `argparse` module
  - [x] No premature abstractions (single ReportRenderer helper class)

**Violations/Exceptions**: None. This feature actually implements new constitutional requirements added in v1.1.0.

## Project Structure

### Documentation (this feature)

```text
specs/002-html-report-consistency/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (Jinja2 best practices, signal handling patterns)
├── data-model.md        # Phase 1 output (Template context structure)
├── quickstart.md        # Phase 1 output (Migration guide for future tools)
├── contracts/           # Phase 1 output (Template context schema)
│   └── template-context.schema.json
├── checklists/          # Phase 2 output (/speckit.tasks command)
│   └── requirements.md  # Already created during spec
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
photo-admin/
├── photo_stats.py           # Existing - MODIFIED: add help, signal handling, Jinja2 rendering
├── photo_pairing.py         # Existing - MODIFIED: add help, signal handling, Jinja2 rendering
├── utils/                   # Existing directory
│   ├── config_manager.py   # Existing - NO CHANGES
│   ├── filename_parser.py  # Existing - NO CHANGES
│   └── report_renderer.py  # NEW: Jinja2 template rendering helper
├── templates/               # NEW directory
│   ├── base.html.j2        # NEW: Base template with common structure
│   ├── photo_stats.html.j2 # NEW: PhotoStats-specific template (extends base)
│   └── photo_pairing.html.j2 # NEW: Photo Pairing-specific template (extends base)
├── tests/
│   ├── test_photo_stats.py # Existing - MODIFIED: add help/signal/template tests
│   ├── test_photo_pairing.py # Existing - MODIFIED: add help/signal/template tests
│   └── test_report_renderer.py # NEW: Test template rendering
├── requirements.txt         # MODIFIED: add Jinja2>=3.1.0
└── README.md               # MODIFIED: update with regeneration notice
```

**Structure Decision**: Single project structure maintained. All tools remain standalone scripts at repository root per constitution. New shared infrastructure (`templates/`, `utils/report_renderer.py`) follows existing pattern where `utils/` contains reusable code but tools don't depend on each other.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. Feature aligns with all constitutional principles and implements newly ratified requirements from Constitution v1.1.0.

---

## Phase 0: Research (✅ Complete)

**Artifact**: [research.md](./research.md)

Key decisions made:
- **Jinja2 Templates**: Embedded in Python code for tool self-containment
- **Template Inheritance**: Base template + tool-specific extensions
- **Signal Handling**: Standard Python `signal` module with atomic file writes
- **Argument Parsing**: `argparse` with RawDescriptionHelpFormatter
- **Color Theme**: Shared constants in template variables

All technical unknowns resolved. Ready for Phase 1 design.

---

## Phase 1: Design & Contracts (✅ Complete)

**Artifacts**:
- [data-model.md](./data-model.md) - ReportContext and related entities
- [contracts/template-context.schema.json](./contracts/template-context.schema.json) - JSON Schema validation
- [quickstart.md](./quickstart.md) - Developer migration guide

### Data Model Summary

**Core Entity**: `ReportContext` - Unified data structure for template rendering

**Key Entities**:
- `KPICard` - Summary metrics with status colors
- `ReportSection` - Modular content (charts, tables, HTML)
- `WarningMessage` - Non-critical issues
- `ErrorMessage` - Critical problems
- `HelpTextSpec` - Standardized CLI help format

**State Transitions**:
- Normal flow: Scan → Build Context → Render → Write Report
- Interruption flow: SIGINT → Check write status → Complete/Skip → Exit 130

### Constitutional Re-check

After completing design phase, re-validated against constitution:

- ✅ **Independent CLI Tools**: Design maintains tool independence. Shared infrastructure (`utils/report_renderer.py`, `templates/`) is imported but tools remain standalone scripts
- ✅ **Testing & Quality**: Test strategy defined in quickstart.md covering context building, template rendering, and signal handling
- ✅ **User-Centric Design**: Template system improves report clarity, error handling provides actionable messages, YAGNI applied (no over-engineering)
- ✅ **Shared Infrastructure**: Extends existing pattern (utils/) with new `report_renderer.py` and `templates/` directory
- ✅ **Simplicity**: Industry-standard Jinja2, minimal abstractions (single ReportRenderer class), no premature optimization

**Agent Context**: Updated CLAUDE.md with Jinja2 dependency and file system usage

---

## Next Steps

Phase 0 (Research) and Phase 1 (Design) are complete. The planning workflow stops here per specification.

**To proceed with implementation**:

1. Run `/speckit.tasks` to generate the task breakdown (tasks.md)
2. Run `/speckit.implement` to execute the implementation plan
3. Reference `quickstart.md` for migration patterns when modifying tools

**Design Artifacts Ready**:
- ✅ Technical decisions documented
- ✅ Data structures defined with JSON Schema
- ✅ Migration guide available for developers
- ✅ Constitution compliance verified
- ✅ All research questions resolved
