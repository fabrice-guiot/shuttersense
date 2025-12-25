<!--
SYNC IMPACT REPORT (Constitution v1.1.1 - Cross-Platform Encoding Standard)

Version change: 1.1.0 → 1.1.1 (PATCH)
Modified principles:
  - Shared Infrastructure Standards: Added Cross-Platform File Encoding requirement

Added requirements:
  - All file read/write operations MUST explicitly specify encoding='utf-8' for text files
  - Never rely on platform default encodings (prevents Windows cp1252 failures)

Rationale:
  - Recurring Windows CI failures due to missing UTF-8 encoding specification
  - Windows defaults to cp1252, which fails on UTF-8 content from templates
  - Explicit encoding ensures consistent behavior across all platforms (Windows, macOS, Linux)
  - Prevents test failures and runtime errors in production

Impact:
  - Code reviews MUST check for explicit encoding parameters
  - All text file operations need encoding='utf-8' parameter
  - Applies to: open(), Path.read_text(), Path.write_text(), json.load(), etc.

Templates requiring updates:
  ✅ No template changes needed - this is a coding standard

Previous Amendment (v1.1.0 - CLI Standards):
  - User-Centric Design: Added requirements for --help option and CTRL+C handling
  - Shared Infrastructure Standards: Added HTML Report Consistency requirement
  - Issues #13, #14, and #16 identified gaps in professional CLI behavior
-->

# photo-admin Constitution

## Core Principles

### I. Independent CLI Tools

Every tool in the photo-admin toolbox MUST be an independent Python script that can run standalone. Tools MUST use the shared `PhotoAdminConfig` class from `config_manager.py` for configuration management. Tools MAY share modules, utilities, and libraries but MUST NOT require other tools to function.

**Rationale**: This architecture enables users to adopt individual tools without installing the entire toolbox, simplifies testing, and allows tools to evolve independently while maintaining consistency through shared infrastructure.

### II. Testing & Quality

All features MUST have test coverage. Tests SHOULD be written before or alongside implementation. The project uses pytest for testing. New tools MUST achieve reasonable test coverage before being considered complete. Tests MUST be independently runnable and well-organized.

**Rationale**: Quality through testing ensures reliability and maintainability. A flexible approach (rather than strict TDD) allows developers to choose the testing workflow that best fits each feature while maintaining the quality bar.

### III. User-Centric Design

Analysis tools MUST generate interactive HTML reports with visualizations and clear presentation of results. All tools MUST provide helpful, actionable error messages. Code MUST prioritize simplicity over cleverness (YAGNI principle). Tools MUST include structured logging for observability and debugging.

All tools MUST provide `--help` and `-h` options that display comprehensive usage information without performing operations. All tools MUST handle CTRL+C (SIGINT) gracefully with user-friendly messages and appropriate exit codes (130).

**Rationale**: Users deserve clear, visual insights into their photo collections. Simplicity reduces maintenance burden and makes the codebase accessible to contributors. Good observability enables users to understand what's happening and troubleshoot issues effectively. Standard CLI conventions (help flags, interruption handling) create professional user experiences and meet established user expectations.

## Shared Infrastructure Standards

- **Configuration Management**: All tools MUST use `PhotoAdminConfig` from `config_manager.py` for loading and managing YAML configuration
- **Config File Location**: Standard locations are `./config/config.yaml` or `~/.photo-admin/config.yaml`
- **Interactive Setup**: Tools MUST prompt users to create configuration from template on first run if config is missing
- **Config Schema**: New tools MAY extend the shared config schema by adding top-level keys; existing keys MUST NOT be redefined
- **File Type Support**: Tools MUST respect `photo_extensions` and `metadata_extensions` from shared config
- **Report Output**: HTML reports MUST be timestamped (format: `tool_name_report_YYYY-MM-DD_HH-MM-SS.html`)
- **HTML Report Consistency**: All tools MUST use a centralized HTML templating approach with consistent styling for common elements (headers, footers, metadata sections, KPI cards, charts, warnings, errors). Tools MAY have tool-specific content sections but MUST maintain consistent visual design and user experience
- **Cross-Platform File Encoding**: All file read and write operations MUST explicitly specify `encoding='utf-8'` for text files. This includes `open()`, `Path.read_text()`, `Path.write_text()`, and similar operations. Never rely on platform default encodings (Windows defaults to cp1252, which causes failures on UTF-8 content)

## Development Philosophy

- **Simplicity First**: Start with the simplest implementation that solves the problem. Avoid premature abstraction or optimization.
- **YAGNI**: Implement only what is needed now. Future requirements will be addressed when they become actual requirements.
- **Clear Over Clever**: Code readability and maintainability trump cleverness. Prefer explicit over implicit.
- **No Over-Engineering**: Resist the urge to build frameworks, abstractions, or utilities until they are clearly needed by multiple features.
- **Incremental Improvement**: Small, focused changes are preferred over large rewrites. Refactor when there's clear benefit.

## Governance

**Constitution Authority**: This constitution defines the core principles and standards for the photo-admin project. All design decisions, code reviews, and feature implementations MUST comply with these principles.

**Amendment Process**:
- Amendments require documentation of rationale and impact analysis
- Version must be incremented according to semantic versioning (see below)
- Significant changes should be discussed before adoption
- Updates to constitution MUST trigger review of dependent templates

**Versioning Policy**:
- **MAJOR**: Backward-incompatible changes to principles, removal of core standards, or fundamental governance changes
- **MINOR**: New principles added, material expansions to existing guidance, or new governance sections
- **PATCH**: Clarifications, wording improvements, typo fixes, or non-semantic refinements

**Compliance**: All pull requests MUST verify compliance with this constitution. Any violations MUST be explicitly justified in the implementation plan's "Complexity Tracking" section. The Constitution Check in `plan-template.md` enforces this gate.

**Review Cycle**: Constitution should be reviewed when:
- A new major tool is added to the toolbox
- Repeated exceptions to a principle suggest it needs revision
- Project direction or scope changes significantly

**Version**: 1.1.1 | **Ratified**: 2025-12-23 | **Last Amended**: 2025-12-25
