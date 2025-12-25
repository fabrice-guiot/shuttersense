# Feature Specification: HTML Report Consistency & Tool Improvements

**Feature Branch**: `002-html-report-consistency`
**Created**: 2025-12-25
**Status**: Draft
**Input**: User description: "Improve consistency between the different tools' HTML report by adopting a centralized template design. Also add --help option and graceful CTRL+C handling to all tools."

**Related Issues**: #16 (HTML Report Consistency), #14 (CTRL+C Handling), #13 (--help Option)

## Clarifications

### Session 2025-12-25

- Q: Should the implementation use Jinja2 as the HTML templating engine? → A: Use Jinja2 templating engine (mature, widely adopted, powerful features, mentioned in issue #16)
- Q: Where should Jinja2 template files be stored in the repository? → A: templates/ directory at repository root
- Q: When Jinja2 template is missing or corrupted, what should the fallback behavior include? → A: Console error message, no report file (tools already provide console summary output)
- Q: Should users be able to continue using existing HTML reports generated before this change, or will they need to regenerate reports? → A: Old reports deprecated, users must regenerate all reports with new templates
- Q: Where should the Chart.js color theme configuration be stored? → A: Embedded in Jinja2 templates as variables/constants (keeps all visual styling centralized)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consistent Report Experience (Priority: P1)

Users run different tools in the photo-admin toolbox and view their HTML reports. Currently, each tool generates reports with inconsistent styling, making it difficult to navigate between reports and understand the visual language of warnings, errors, and metrics.

Users need a unified visual experience across all reports so they can:
- Instantly recognize report sections and understand their meaning
- Compare metrics across different tools without visual confusion
- Know they're using tools from the same professional toolbox

**Why this priority**: This addresses the core issue #16 and provides the foundation for all other improvements. Without consistent templates, users face cognitive overhead when switching between tool reports.

**Independent Test**: Can be fully tested by running both PhotoStats and Photo Pairing tools on the same dataset and comparing the generated HTML reports for visual consistency (colors, fonts, layout, metadata presentation).

**Acceptance Scenarios**:

1. **Given** both PhotoStats and Photo Pairing have generated reports, **When** user opens both reports in browser tabs, **Then** both reports use identical color schemes, typography, header/footer layouts, and section styling
2. **Given** a user views any tool's report, **When** they examine the metadata section (folder path, timestamp, duration), **Then** the information is presented in the same format and location across all tools
3. **Given** a user views KPI summary cards in any report, **When** they compare cards across different tool reports, **Then** all cards use consistent styling for titles, values, units, and status indicators
4. **Given** a user views charts in any report, **When** they examine the color theme and styling, **Then** all Chart.js visualizations use the same color palette and styling conventions
5. **Given** a user encounters warnings or errors in any report, **When** they view these sections, **Then** warning and error styles are visually identical across all tools

---

### User Story 2 - Self-Service Help (Priority: P2)

Users want to quickly understand how to use the tools without consulting external documentation. Currently, running a tool with `--help` incorrectly treats it as a folder name, causing confusion and errors.

Users need accessible help text that explains:
- What the tool does
- Required and optional arguments
- Usage examples
- Configuration requirements

**Why this priority**: This is a common user expectation for CLI tools. Without it, users must hunt for documentation or experiment with errors. This addresses issue #13.

**Independent Test**: Can be tested by running each tool with `--help` or `-h` flags and verifying comprehensive help output is displayed without attempting folder scans.

**Acceptance Scenarios**:

1. **Given** a user types `python3 photo_stats.py --help`, **When** the command executes, **Then** the tool displays help text and exits without scanning any folder
2. **Given** a user reads the help output, **When** they examine the content, **Then** it includes tool description, argument syntax, usage examples, and configuration notes
3. **Given** a user types `python3 photo_pairing.py -h`, **When** the command executes, **Then** the short-form help flag works identically to `--help`
4. **Given** a new user runs the help command, **When** they review the output, **Then** they understand what the tool does and how to run their first scan

---

### User Story 3 - Graceful Interruption (Priority: P2)

Users run long-running analyses on large photo collections and need to interrupt operations cleanly when they realize they've targeted the wrong folder or need to stop for other reasons. Currently, pressing CTRL+C may leave the tool in an undefined state or produce confusing error messages.

Users need the ability to interrupt any tool cleanly, receiving:
- Acknowledgment that interruption was received
- Information about any partial progress
- Clean exit without stack traces or error noise

**Why this priority**: This improves user experience during error recovery and provides professional tool behavior. Users should feel in control of long operations. This addresses issue #14.

**Independent Test**: Can be tested by starting a scan on a large folder and pressing CTRL+C at various points in the execution, verifying clean shutdown and appropriate messaging.

**Acceptance Scenarios**:

1. **Given** a tool is scanning a large photo collection, **When** user presses CTRL+C, **Then** the tool displays "Operation interrupted by user" message and exits cleanly without stack traces
2. **Given** a tool is generating a report, **When** user interrupts with CTRL+C, **Then** the tool acknowledges interruption and indicates that the report was not completed
3. **Given** a tool has partial results when interrupted, **When** the interruption occurs, **Then** the tool mentions the interrupted state but does not create incomplete report files
4. **Given** any tool is running, **When** interrupted via CTRL+C, **Then** the exit code indicates user interruption (standard convention: exit code 130)

---

### Edge Cases

- What happens when a template file is missing or corrupted?
  - Tool should display clear error message in console explaining template issue and not generate HTML report file (users still see analysis summary in console output)
- What happens if CTRL+C is pressed during file I/O operations?
  - Tool should complete the current atomic operation (single file read/write) then exit cleanly
- What happens if help text includes special characters that could break terminal display?
  - Help text should be properly escaped and tested across different terminal types
- What happens when template rendering fails due to invalid data?
  - Tool should catch template errors and provide meaningful error message in console, not generate HTML report (console summary still available)
- What happens to HTML reports generated before this feature?
  - Pre-existing reports are deprecated; users should regenerate reports using updated tools to ensure visual consistency across all reports

## Requirements *(mandatory)*

### Functional Requirements

#### HTML Report Consistency (Issue #16)

- **FR-001**: All tools MUST use Jinja2 as the centralized HTML template engine for report generation
- **FR-002**: All tools MUST apply identical CSS styling for backgrounds, typography, section headers, and layout
- **FR-003**: All report metadata (scanned folder, timestamp, duration) MUST be presented in the same format and location across all tools
- **FR-004**: All KPI summary cards MUST use consistent styling for card backgrounds, titles, values, units, and status indicators
- **FR-005**: All Chart.js visualizations MUST use a shared color theme and styling configuration embedded as variables/constants in Jinja2 templates
- **FR-006**: All warning sections MUST use identical visual styling (colors, icons, borders, typography)
- **FR-007**: All error sections MUST use identical visual styling (colors, icons, borders, typography)
- **FR-008**: All invalid data sections (pairing issues, invalid filenames) MUST use consistent presentation styles
- **FR-009**: Template system MUST support tool-specific content sections while maintaining consistent chrome (header, footer, navigation)
- **FR-010**: Report footer MUST include consistent tool attribution, version information, and generation timestamp
- **FR-024**: Jinja2 template files MUST be stored in a `templates/` directory at the repository root for easy discovery and maintenance
- **FR-025**: When Jinja2 templates are missing or corrupted, tools MUST display a clear error message in console and NOT generate HTML report files (analysis summary remains available in console output)
- **FR-026**: HTML reports generated before this feature implementation are deprecated; users MUST regenerate reports with updated tools to ensure consistency

#### Help Option Support (Issue #13)

- **FR-011**: All tools MUST recognize `--help` flag and display comprehensive help text
- **FR-012**: All tools MUST recognize `-h` short flag as alias for `--help`
- **FR-013**: Help text MUST include tool description, purpose, and key features
- **FR-014**: Help text MUST show argument syntax with required and optional parameters clearly marked
- **FR-015**: Help text MUST include at least two usage examples demonstrating common scenarios
- **FR-016**: Help text MUST mention configuration file requirements and standard locations
- **FR-017**: Help text display MUST exit with code 0 (success) without performing any scanning operations

#### CTRL+C Interruption Handling (Issue #14)

- **FR-018**: All tools MUST trap SIGINT (CTRL+C) signal and handle it gracefully
- **FR-019**: Upon CTRL+C, tools MUST display user-friendly interruption message without stack traces
- **FR-020**: Upon CTRL+C, tools MUST exit with standard interruption exit code (130)
- **FR-021**: Tools MUST NOT create partial or incomplete report files when interrupted
- **FR-022**: Interruption handling MUST work at any point during tool execution (startup, scanning, processing, report generation)
- **FR-023**: If interruption occurs during file operations, tools MUST complete current atomic operation before exiting

### Key Entities

- **HTML Template**: Centralized Jinja2 template structure stored in `templates/` directory, containing header, footer, metadata section, content area, and styling that all tools use
- **Template Context**: Data structure passed to template containing tool name, metadata, KPIs, visualizations, warnings, and errors
- **Color Theme Configuration**: Shared palette embedded as Jinja2 template variables/constants, defining background colors, text colors, accent colors, chart colors, warning colors, and error colors
- **Help Text Specification**: Structured format for tool help including description, arguments, examples, and configuration notes

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can identify which tool generated a report within 2 seconds by looking at report header and branding (while experiencing consistent visual design)
- **SC-002**: Users viewing reports from two different tools observe identical styling for common elements (headers, cards, charts, warnings)
- **SC-003**: New users can understand how to run any tool correctly on first attempt after reading help text (measured by successful first execution)
- **SC-004**: All tools respond to CTRL+C within 1 second with clean interruption message
- **SC-005**: Zero stack traces or error noise displayed to users during normal CTRL+C interruptions
- **SC-006**: Users can compare KPI cards across different tool reports without visual confusion or misinterpretation
- **SC-007**: Chart.js visualizations in all reports use identical color palettes, enabling direct visual comparison
- **SC-008**: HTML template changes can be applied to all tools by updating a single centralized template file
