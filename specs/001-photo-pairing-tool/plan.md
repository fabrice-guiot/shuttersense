# Implementation Plan: Photo Pairing Tool

**Branch**: `001-photo-pairing-tool` | **Date**: 2025-12-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-photo-pairing-tool/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

The Photo Pairing Tool analyzes photo filenames to group related files, extract camera IDs and processing methods, and generate comprehensive HTML reports with analytics. The tool operates as an independent Python CLI application that shares configuration infrastructure with existing photo-admin tools through PhotoAdminConfig. Users run the tool on a folder, provide one-time configuration for new camera IDs and processing methods discovered, then receive an interactive HTML report showing image groups, camera usage, and processing method breakdowns.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: PyYAML (>=6.0), shared PhotoAdminConfig class from config_manager.py
**Storage**: YAML configuration files (camera_mappings and processing_methods in shared config)
**Testing**: pytest (>=7.4.0) with pytest-cov and pytest-mock for comprehensive test coverage
**Target Platform**: Cross-platform CLI (macOS, Linux, Windows) - runs locally on user's machine
**Project Type**: Single CLI tool (independent Python script at repository root)
**Performance Goals**: Analyze 1000+ photos in under 60 seconds; Real-time user interaction for configuration prompts
**Constraints**: Must work offline; No external API dependencies; Minimal memory footprint for large photo collections
**Scale/Scope**: Single-folder analysis; Handles collections from hundreds to tens of thousands of photos; Interactive terminal UI with HTML report output

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Independent CLI Tools**: Is this tool a standalone Python script? Does it use PhotoAdminConfig? Can it run without other tools?
  - ✅ Standalone `photo_pairing.py` script at repository root
  - ✅ Uses shared PhotoAdminConfig from config_manager.py
  - ✅ No dependencies on PhotoStats or other tools - runs completely independently

- [x] **Testing & Quality**: Are tests planned? Is pytest configured? Is test coverage addressed?
  - ✅ Comprehensive test suite planned in `tests/test_photo_pairing.py`
  - ✅ pytest already configured (pytest.ini exists)
  - ✅ Target: >80% test coverage as specified in PRD acceptance criteria

- [x] **User-Centric Design**:
  - For analysis tools: Is HTML report generation included?
    - ✅ Interactive HTML reports with statistics, charts, and breakdowns (FR-010)
  - Are error messages clear and actionable?
    - ✅ Clear validation messages for invalid filenames with specific reasons (FR-013)
  - Is the implementation simple (YAGNI)?
    - ✅ Version 1.0 scope limited to filename analysis, no sidecar file processing
    - ✅ Simple file grouping by 8-character prefix without complex algorithms
  - Is structured logging included for observability?
    - ✅ Progress indicators and status messages planned for scanning, analysis, report generation

- [x] **Shared Infrastructure**: Does it use PhotoAdminConfig? Does it respect shared config schema? Are standard file locations used?
  - ✅ Uses PhotoAdminConfig for all configuration (FR-014)
  - ✅ Extends config schema with new top-level keys: camera_mappings, processing_methods
  - ✅ Respects photo_extensions and metadata_extensions from shared config
  - ✅ HTML reports use standard timestamped naming: `photo_pairing_report_YYYY-MM-DD_HH-MM-SS.html`

- [x] **Simplicity**: Is this the simplest approach? Have premature abstractions been avoided?
  - ✅ Direct filename parsing with regex/string operations
  - ✅ No framework dependencies beyond PyYAML
  - ✅ Simple dictionary-based data structures for grouping and tracking
  - ✅ No premature optimization - straightforward linear file scanning

**Violations/Exceptions**: None - full constitution compliance

## Project Structure

### Documentation (this feature)

```text
specs/001-photo-pairing-tool/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification (completed)
├── research.md          # Phase 0 output (filename parsing patterns, HTML reporting)
├── data-model.md        # Phase 1 output (entities: ImageGroup, CameraMapping, etc.)
├── quickstart.md        # Phase 1 output (quick start guide for users)
├── contracts/           # Phase 1 output (not applicable - CLI tool, no API)
│   └── filename-validation.md  # Filename pattern specifications
├── checklists/
│   └── requirements.md  # Spec quality checklist (completed)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
photo-admin/
├── photo_pairing.py          # Main CLI script (NEW)
├── config_manager.py          # Shared config (EXISTING - will extend config schema)
├── config/
│   ├── template-config.yaml   # Will be updated with camera_mappings and processing_methods
│   └── config.yaml            # User config (auto-updated by tool)
├── tests/
│   ├── test_photo_pairing.py  # Test suite for new tool (NEW)
│   ├── test_photo_stats.py    # Existing PhotoStats tests
│   └── conftest.py            # Shared test fixtures (may extend)
├── docs/
│   └── prd/
│       └── photo-pairing-tool.md  # Original PRD (EXISTING)
├── requirements.txt           # Python dependencies (EXISTING - no changes needed)
└── pytest.ini                # Pytest configuration (EXISTING)
```

**Structure Decision**: Single project structure - the tool is a standalone script at the repository root, consistent with existing PhotoStats architecture. This matches the Independent CLI Tools principle and keeps the codebase simple. No subdirectories needed for a single-file CLI tool. Tests go in the existing `tests/` directory following established patterns.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations - this section intentionally left empty.

## Phase 0: Research & Design Decisions

See [research.md](research.md) for detailed research findings.

**Key Decisions**:
1. **Filename parsing strategy**: Regular expressions vs string operations
2. **HTML report generation**: Template engine vs direct HTML string building
3. **Interactive prompts**: Input handling for camera/method configuration
4. **Configuration updates**: In-place YAML modification approach

## Phase 1: Data Model & Contracts

See [data-model.md](data-model.md) for complete entity definitions.

**Core Entities**:
- ImageGroup: Collection of files sharing 8-character prefix
- CameraMapping: 4-char ID → (name, serial_number)
- ProcessingMethod: keyword → description
- SeparateImage: Numeric suffix identification within group
- InvalidFile: Validation failure tracking

See [contracts/](contracts/) for filename validation specifications.

## Phase 2: Implementation Tasks

Tasks will be generated by `/speckit.tasks` command and written to [tasks.md](tasks.md).
