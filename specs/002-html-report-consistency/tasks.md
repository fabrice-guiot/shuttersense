# Tasks: HTML Report Consistency & Tool Improvements

**Input**: Design documents from `/specs/002-html-report-consistency/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/template-context.schema.json

**Tests**: Tests will be added for new infrastructure (ReportRenderer) and updated for modified tools (PhotoStats, Photo Pairing) to ensure template rendering, help text, and signal handling work correctly.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for centralized templating

- [x] T001 Add Jinja2>=3.1.0 to requirements.txt
- [x] T002 [P] Create templates/ directory at repository root
- [x] T003 [P] Create utils/report_renderer.py skeleton file

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Implement ReportContext dataclass in utils/report_renderer.py with all required fields (tool_name, tool_version, scan_path, scan_timestamp, scan_duration, kpis, sections, warnings, errors, footer_note)
- [x] T005 [P] Implement KPICard dataclass in utils/report_renderer.py with fields (title, value, unit, status, icon, tooltip)
- [x] T006 [P] Implement ReportSection dataclass in utils/report_renderer.py with fields (title, type, data, html_content, description, collapsible)
- [x] T007 [P] Implement WarningMessage dataclass in utils/report_renderer.py with fields (message, details, severity)
- [x] T008 [P] Implement ErrorMessage dataclass in utils/report_renderer.py with fields (message, details, actionable_fix)
- [x] T009 Create base Jinja2 template in templates/base.html.j2 with header, footer, KPI cards section, content blocks, warning/error sections, and embedded CSS/Chart.js color theme
- [x] T010 Implement ReportRenderer class in utils/report_renderer.py with render_report() method that loads Jinja2 template, renders with context, and handles template errors with console fallback
- [x] T011 [P] Write unit tests for ReportRenderer in tests/test_report_renderer.py covering successful rendering, template error handling, and atomic file writes

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Consistent Report Experience (Priority: P1) 🎯 MVP

**Goal**: Migrate both PhotoStats and Photo Pairing tools to use centralized Jinja2 templates, ensuring identical visual styling across all reports

**Independent Test**: Run both PhotoStats and Photo Pairing on same dataset, open generated HTML reports in browser tabs, verify identical color schemes, typography, header/footer layouts, section styling, KPI card styling, chart colors, and warning/error styles

### Implementation for User Story 1

- [x] T012 [US1] Create templates/photo_stats.html.j2 that extends base.html.j2 with PhotoStats-specific content blocks (orphaned files section, sidecar status section)
- [x] T013 [US1] Create templates/photo_pairing.html.j2 that extends base.html.j2 with Photo Pairing-specific content blocks (filename patterns section, camera usage section)
- [x] T014 [US1] Refactor PhotoStats.generate_html_report() in photo_stats.py to build ReportContext from existing analysis data (map current HTML generation logic to KPICard and ReportSection objects)
- [x] T015 [US1] Replace PhotoStats HTML generation f-strings in photo_stats.py with ReportRenderer.render_report() call using templates/photo_stats.html.j2
- [x] T016 [US1] Add try-except around PhotoStats template rendering in photo_stats.py to catch template errors and display console error message without generating HTML file
- [x] T017 [US1] Refactor photo_pairing.generate_html_report() in photo_pairing.py to build ReportContext from existing analysis data (map current HTML generation logic to KPICard and ReportSection objects)
- [x] T018 [US1] Replace Photo Pairing HTML generation f-strings in photo_pairing.py with ReportRenderer.render_report() call using templates/photo_pairing.html.j2
- [x] T019 [US1] Add try-except around Photo Pairing template rendering in photo_pairing.py to catch template errors and display console error message without generating HTML file
- [x] T020 [US1] Update tests/test_photo_stats.py test_generate_html_report() to verify template-based rendering produces HTML with consistent styling elements
- [x] T021 [US1] Update tests/test_photo_pairing.py test_generate_report() to verify template-based rendering produces HTML with consistent styling elements
- [x] T022 [US1] Add integration test in tests/test_report_renderer.py that generates reports from both tools and validates visual consistency (same CSS classes, same color variables, same Chart.js theme)

**Checkpoint**: At this point, both tools generate visually consistent HTML reports using Jinja2 templates

---

## Phase 4: User Story 2 - Self-Service Help (Priority: P2)

**Goal**: Add --help and -h flags to all tools with comprehensive usage information

**Independent Test**: Run `python3 photo_stats.py --help` and `python3 photo_pairing.py -h`, verify help text displays tool description, argument syntax, usage examples, configuration notes, and exits with code 0 without scanning

### Implementation for User Story 2

- [x] T023 [US2] Refactor PhotoStats argument handling in photo_stats.py from manual sys.argv parsing to argparse.ArgumentParser with description, epilog (usage examples), and RawDescriptionHelpFormatter
- [x] T024 [US2] Add help text to PhotoStats argparse in photo_stats.py including tool description (2-3 sentences), argument syntax showing required folder_path, at least 2 usage examples, and config file location notes
- [x] T025 [US2] Verify PhotoStats argparse in photo_stats.py recognizes both --help and -h flags (argparse provides this by default)
- [x] T026 [US2] Update Photo Pairing argparse help text in photo_pairing.py to include enhanced description, at least 2 usage examples in epilog, and config file location notes (photo_pairing.py already uses argparse, just enhance help content)
- [x] T027 [US2] Add test in tests/test_photo_stats.py to verify --help flag displays help text and exits with code 0 using subprocess or pytest capsys
- [x] T028 [US2] Add test in tests/test_photo_stats.py to verify -h flag works identically to --help
- [x] T029 [US2] Add test in tests/test_photo_pairing.py to verify --help flag displays enhanced help text and exits with code 0
- [x] T030 [US2] Add test in tests/test_photo_pairing.py to verify -h flag works identically to --help
- [x] T031 [US2] Add test in tests/test_photo_stats.py to verify help text contains required elements (description, usage examples, config notes)
- [x] T032 [US2] Add test in tests/test_photo_pairing.py to verify help text contains required elements (description, usage examples, config notes)

**Checkpoint**: All tools provide comprehensive help text accessible via --help/-h flags

---

## Phase 5: User Story 3 - Graceful Interruption (Priority: P2)

**Goal**: Implement SIGINT signal handlers for clean interruption with user-friendly messages, exit code 130, and prevention of partial report files

**Independent Test**: Start scan on large folder, press CTRL+C at various points (during scan, during report generation), verify "Operation interrupted by user" message displays, no stack traces shown, exit code is 130, and no partial HTML report files created

### Implementation for User Story 3

- [x] T033 [US3] Add signal handler setup in PhotoStats main() in photo_stats.py to trap SIGINT and set global shutdown_requested flag
- [x] T034 [US3] Implement signal_handler function in photo_stats.py that displays "\nOperation interrupted by user" message and calls sys.exit(130)
- [x] T035 [US3] Add periodic shutdown_requested checks in PhotoStats scan loop in photo_stats.py (check every N files or every iteration)
- [x] T036 [US3] Modify PhotoStats report generation in photo_stats.py to use atomic file write pattern (write to temp file → rename to final name) to prevent partial files (already implemented in ReportRenderer)
- [x] T037 [US3] Add shutdown_requested check before PhotoStats report generation in photo_stats.py to skip report if interrupted
- [x] T038 [US3] Add signal handler setup in Photo Pairing main() in photo_pairing.py to trap SIGINT (photo_pairing.py line 37-43 already has signal handling, verify it uses exit code 130 and user-friendly message)
- [x] T039 [US3] Update Photo Pairing signal handler in photo_pairing.py to ensure message is "Operation interrupted by user" (currently says "Scan interrupted")
- [x] T040 [US3] Verify Photo Pairing signal handler in photo_pairing.py uses sys.exit(130) instead of sys.exit(1) (already correct)
- [x] T041 [US3] Modify Photo Pairing report generation in photo_pairing.py to use atomic file write pattern if not already implemented (already implemented in ReportRenderer)
- [x] T042 [US3] Add shutdown_requested check before Photo Pairing report generation in photo_pairing.py to skip report if interrupted
- [x] T043 [US3] Add test in tests/test_signal_handling.py to verify PhotoStats signal handler exists and works correctly
- [x] T044 [US3] Add test in tests/test_signal_handling.py to verify atomic file writes prevent partial HTML report files
- [x] T045 [US3] Add test in tests/test_signal_handling.py to verify user-friendly interruption message format (exit code 130)
- [x] T046 [US3] Add test in tests/test_signal_handling.py to verify Photo Pairing signal handler exists and works correctly
- [x] T047 [US3] Add test in tests/test_signal_handling.py to verify shutdown checks exist before report generation
- [x] T048 [US3] Add test in tests/test_signal_handling.py to verify user-friendly interruption message format (exit code 130)

**Checkpoint**: All tools handle CTRL+C gracefully with proper exit codes and clean shutdown

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation updates and final validation

- [ ] T049 [P] Update README.md with notice that old HTML reports are deprecated and users should regenerate reports with updated tools
- [ ] T050 [P] Update CLAUDE.md Recent Changes section with completion of feature 002-html-report-consistency
- [ ] T051 [P] Add example HTML reports to docs/ showing new consistent styling (optional, for documentation purposes)
- [ ] T052 Run all tests with pytest to ensure 100% pass rate (pytest tests/ -v)
- [ ] T053 Generate sample reports from both tools and manually verify visual consistency checklist from spec.md acceptance scenarios
- [ ] T054 Test --help flags on both tools and verify comprehensive help output
- [ ] T055 Test CTRL+C interruption on both tools at various execution points
- [ ] T056 Verify constitution compliance: tools remain standalone, shared infrastructure in utils/, simple implementation, no over-engineering

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User Story 1 (US1): Can start after Phase 2
  - User Story 2 (US2): Can start after Phase 2 - Independent of US1
  - User Story 3 (US3): Can start after Phase 2 - Independent of US1 and US2
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1) - Consistent Reports**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2) - Help Flags**: Can start after Foundational (Phase 2) - Independent of US1 (modifies different code paths)
- **User Story 3 (P3) - CTRL+C Handling**: Can start after Foundational (Phase 2) - Independent of US1 and US2 (adds signal handling orthogonal to templates and help)

### Within Each User Story

**User Story 1 (Consistent Reports)**:
- T012, T013: Create templates (parallel)
- T014, T017: Build ReportContext for each tool (parallel)
- T015, T018: Replace HTML generation with template rendering (parallel, depends on templates existing)
- T016, T019: Add error handling (parallel, depends on rendering being in place)
- T020, T021: Update existing tests (parallel)
- T022: Integration test (depends on both tools using templates)

**User Story 2 (Help Flags)**:
- T023-T026: Implement argparse help in both tools (can be parallel)
- T027-T032: Add tests for help functionality (can be parallel after implementation)

**User Story 3 (CTRL+C Handling)**:
- T033-T037: Implement signal handling in PhotoStats (sequential within tool)
- T038-T042: Implement signal handling in Photo Pairing (sequential within tool, but parallel to PhotoStats)
- T043-T048: Add tests for signal handling (can be parallel after implementation)

### Parallel Opportunities

- **Setup (Phase 1)**: All 3 tasks can run in parallel
- **Foundational (Phase 2)**: T005-T008 (dataclass definitions) can run in parallel; T011 can run in parallel with T009-T010
- **User Story 1**: T012 and T013 (templates) in parallel; T014 and T017 (context building) in parallel; T015 and T018 (rendering) in parallel; T016 and T019 (error handling) in parallel; T020 and T021 (tests) in parallel
- **User Story 2**: T023-T026 (argparse setup) can run in parallel; T027-T032 (tests) can run in parallel
- **User Story 3**: T033-T037 (PhotoStats) and T038-T042 (Photo Pairing) can run in parallel as separate tools; T043-T048 (tests) can run in parallel
- **Different User Stories**: After Phase 2 completes, all three user stories (US1, US2, US3) can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch template creation tasks together:
Task: "Create templates/photo_stats.html.j2 that extends base.html.j2"
Task: "Create templates/photo_pairing.html.j2 that extends base.html.j2"

# Launch ReportContext building tasks together:
Task: "Refactor PhotoStats.generate_html_report() to build ReportContext"
Task: "Refactor photo_pairing.generate_html_report() to build ReportContext"

# Launch template rendering replacement tasks together:
Task: "Replace PhotoStats HTML generation with ReportRenderer"
Task: "Replace Photo Pairing HTML generation with ReportRenderer"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T011) - CRITICAL
3. Complete Phase 3: User Story 1 (T012-T022)
4. **STOP and VALIDATE**: Test both tools independently, verify visual consistency
5. Deploy/demo consistent HTML reports

**Result**: Both tools generate visually consistent HTML reports using centralized Jinja2 templates. This delivers the core value of issue #16.

### Incremental Delivery

1. **Foundation**: Complete Setup + Foundational → Template infrastructure ready
2. **MVP**: Add User Story 1 → Test visual consistency → Deploy (core issue #16 solved!)
3. **Help**: Add User Story 2 → Test help flags → Deploy (issue #13 solved!)
4. **Interruption**: Add User Story 3 → Test CTRL+C handling → Deploy (issue #14 solved!)
5. **Polish**: Phase 6 → Documentation and final validation

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T011)
2. Once Foundational is done:
   - **Developer A**: User Story 1 - Consistent Reports (T012-T022)
   - **Developer B**: User Story 2 - Help Flags (T023-T032)
   - **Developer C**: User Story 3 - CTRL+C Handling (T033-T048)
3. Stories complete and integrate independently
4. Team collaborates on Phase 6: Polish (T049-T056)

---

## Total Task Count: 56 tasks

**Breakdown by Phase**:
- Phase 1 (Setup): 3 tasks
- Phase 2 (Foundational): 8 tasks
- Phase 3 (US1 - Consistent Reports): 11 tasks
- Phase 4 (US2 - Help Flags): 10 tasks
- Phase 5 (US3 - CTRL+C Handling): 16 tasks
- Phase 6 (Polish): 8 tasks

**Breakdown by User Story**:
- US1 (Consistent Report Experience): 11 tasks
- US2 (Self-Service Help): 10 tasks
- US3 (Graceful Interruption): 16 tasks
- Shared Infrastructure: 11 tasks (Setup + Foundational)
- Polish: 8 tasks

**Parallel Opportunities**: 32 tasks marked [P] can run in parallel with other tasks in same phase

**Independent Test Criteria**:
- **US1**: Run both tools, open reports in browser, verify identical visual styling
- **US2**: Run tools with --help/-h, verify comprehensive output and exit code 0
- **US3**: Run tools, press CTRL+C, verify clean shutdown with exit code 130 and no partial files

**Suggested MVP Scope**: Phase 1 + Phase 2 + Phase 3 (User Story 1 only) = 22 tasks

This delivers the core value of centralized, consistent HTML reports addressing issue #16.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Constitution compliance verified: tools remain standalone, shared infrastructure in utils/, Jinja2 is industry-standard, no over-engineering
