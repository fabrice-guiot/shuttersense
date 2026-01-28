# Feature Specification: Remove CLI Direct Usage

**Feature Branch**: `108-remove-cli-direct-usage`
**Created**: 2026-01-28
**Status**: Draft
**Input**: User description: "Github issue #93, based on the full PRD: docs/prd/000-remove-cli-direct-usage.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Test Local Path Before Collection Creation (Priority: P0)

A user setting up a new photo collection needs to verify that a local directory is accessible and contains valid files before registering it with the server. The user runs a test command through the agent, specifying a path on their local machine. The agent checks the path exists, is readable, counts and categorizes files, and optionally runs analysis tools against the contents. The user sees a summary of results including file counts, any issues found, and whether the path is ready for collection creation.

**Why this priority**: This is the foundational capability that replaces the most common CLI tool workflow. Without path testing, users cannot validate their setup before committing to collection creation. It also serves as the entry point for the test-then-create workflow that all subsequent stories depend on.

**Independent Test**: Can be fully tested by running the agent test command against a local directory with known photo files and verifying the output summary matches expected file counts and analysis results. Delivers immediate value: users can validate paths without any server interaction.

**Acceptance Scenarios**:

1. **Given** a user has the agent installed and a directory containing photo files, **When** they run the test command specifying that directory path, **Then** the agent displays accessibility status, file count breakdown (photos, sidecars), and a readiness summary.
2. **Given** a user specifies a non-existent or unreadable path, **When** they run the test command, **Then** the agent displays a clear error explaining the path is not accessible with a remediation suggestion.
3. **Given** a user wants to test with a specific analysis tool, **When** they run the test command with a tool filter, **Then** only the specified tool runs and results are displayed.
4. **Given** a user wants only to check path accessibility without running analysis, **When** they run the test command with a check-only option, **Then** the agent validates accessibility and file listing without executing analysis tools.
5. **Given** a user wants to save results locally, **When** they run the test command with an output file option, **Then** the analysis report is saved as an HTML file at the specified location.
6. **Given** a successful test completes, **When** the agent finishes, **Then** the test results are cached locally for use by subsequent collection creation within 24 hours.

---

### User Story 2 - Create Collection from Tested Path (Priority: P0)

After testing a local path, the user wants to register it as a Collection on the server so they can schedule recurring analysis jobs and view results in the web application. The user runs a collection creation command through the agent, which verifies test results exist (or runs a test automatically), prompts for a collection name if not provided, and creates the Collection on the server. The new Collection is automatically bound to the creating agent, and the user receives a unique identifier and a link to view it in the web UI.

**Why this priority**: Collection creation via agent is the second half of the critical test-then-create workflow. Without it, users must still go to the web UI to create collections manually, defeating the purpose of agent-based local setup.

**Independent Test**: Can be tested by running the test command on a known directory followed by the collection create command, then verifying the collection appears on the server with the correct name, path, and agent binding.

**Acceptance Scenarios**:

1. **Given** a user has previously tested a local path within the last 24 hours, **When** they run the collection create command for that path, **Then** the agent uses cached test results, prompts for a name (suggesting the folder name), creates the Collection on the server, and displays the Collection identifier and web UI link.
2. **Given** a user has NOT previously tested the path, **When** they run the collection create command, **Then** the agent automatically runs a test first before proceeding with creation.
3. **Given** a user provides a name via command option, **When** they run the collection create command with the name flag, **Then** no interactive prompt is shown and the provided name is used.
4. **Given** a user wants to skip the test step, **When** they run the collection create command with a skip-test option, **Then** the agent creates the Collection without testing (for advanced users).
5. **Given** a user wants an immediate analysis after creation, **When** they run the collection create command with an analyze option, **Then** the agent creates the Collection and immediately queues an analysis job.
6. **Given** the server is unreachable, **When** the user attempts to create a Collection, **Then** the agent displays a clear error indicating server connectivity is required for collection creation.

---

### User Story 3 - Run Analysis Offline and Sync Results Later (Priority: P1)

A user with intermittent connectivity wants to run analysis tools against a local collection without requiring a server connection, then upload results when connectivity is restored. The user runs analysis in offline mode against a cached local Collection (identified by its unique identifier), and results are stored locally. When back online, the user runs a sync command to upload all pending results to the server, where they become visible in the web UI.

**Why this priority**: Offline capability is important for photographers working in the field or with NAS storage on isolated networks. However, it depends on collections already existing (US1/US2) and is a secondary workflow compared to the primary online path.

**Independent Test**: Can be tested by syncing collection cache while online, disconnecting from the server, running analysis in offline mode against a local collection, verifying local result files are created, reconnecting, and running sync to confirm results appear on the server.

**Acceptance Scenarios**:

1. **Given** a user has a synced collection cache with local collections, **When** they run analysis in offline mode specifying a local collection identifier and tool, **Then** the analysis runs locally and results are saved to local storage.
2. **Given** a user attempts offline analysis on a remote collection (cloud storage), **When** they run the command, **Then** the agent rejects the request with an error explaining remote collections require network connectivity.
3. **Given** a user has pending offline results, **When** they run the sync command while online, **Then** all pending results are uploaded to the server and local result files are cleaned up on success.
4. **Given** a user wants to preview what would be uploaded, **When** they run the sync command with a dry-run option, **Then** the agent lists pending results without uploading.
5. **Given** a sync is interrupted mid-upload, **When** the user runs sync again, **Then** the agent resumes from where it left off without duplicating already-uploaded results.
6. **Given** a user runs analysis in default (online) mode, **When** the command executes, **Then** a job is created on the server, executed locally, and results reported back - equivalent to the web UI "Run Tool" action.

---

### User Story 4 - List and Manage Bound Collections (Priority: P1)

An agent operator wants to see which Collections are assigned to their agent, including their current accessibility status and whether they support offline execution. The user runs a collections list command that displays all bound collections in a tabular format. The user can filter by type (local vs remote) and status, and can refresh the local cache from the server.

**Why this priority**: Collection management is essential for users with multiple collections, especially for understanding which collections can run offline. It supports US3 by providing the cache mechanism needed for offline operations.

**Independent Test**: Can be tested by creating several collections bound to an agent, running the list command, and verifying all collections appear with correct metadata. Offline mode can be tested by using cached data without server connectivity.

**Acceptance Scenarios**:

1. **Given** an agent has bound collections, **When** the user runs the collections list command, **Then** all bound collections are displayed with identifier, type, name, location, accessibility status, last analysis date, and offline capability.
2. **Given** the user is offline or uses an offline flag, **When** they run the collections list command, **Then** cached collection data is displayed with a timestamp showing when the cache was last synced.
3. **Given** the collection cache is older than 7 days, **When** the user views it, **Then** a warning is displayed recommending a cache refresh.
4. **Given** the user wants to refresh the cache, **When** they run the collections sync command, **Then** the cache is updated from the server with current collection data.
5. **Given** the user wants to re-test a collection's accessibility, **When** they run the collections test command with a collection identifier, **Then** the agent checks the path and updates the status on the server.
6. **Given** the user wants to see only local collections, **When** they run the list command with a type filter, **Then** only collections matching the specified type are shown.

---

### User Story 5 - Remove Standalone CLI Tools and Update Project Constitution (Priority: P2)

A security-conscious maintainer preparing for production deployment needs to remove the standalone CLI tools from the repository entirely. These tools bypass authentication, tenant isolation, job tracking, and audit logging. The removal includes deleting the tool scripts, updating the project's architectural constitution to reflect agent-only execution, and revising all documentation to reference agent-based workflows instead of CLI tools.

**Why this priority**: While critical for production readiness, this story depends on US1-US4 being complete so that all CLI tool functionality has an agent-based replacement. It is a cleanup and hardening task rather than new capability.

**Independent Test**: Can be tested by verifying the deleted files no longer exist in the repository, checking that all documentation references point to agent commands, confirming the constitution reflects agent-only principles, and ensuring shared analysis modules still function correctly through the agent.

**Acceptance Scenarios**:

1. **Given** all agent commands are implemented (US1-US4), **When** the maintainer removes standalone CLI tools, **Then** photo_stats.py, photo_pairing.py, and pipeline_validation.py are deleted from the repository root.
2. **Given** CLI tools are removed, **When** the project constitution is reviewed, **Then** the "Independent CLI Tools" principle has been replaced with an "Agent-Only Tool Execution" principle.
3. **Given** CLI tools are removed, **When** project documentation (README, development guidelines, docs/) is reviewed, **Then** all CLI tool references have been replaced with agent command references.
4. **Given** CLI tools are removed, **When** analysis is run through the agent, **Then** shared analysis modules continue to function correctly (the CLI tools were thin wrappers; core logic is preserved).
5. **Given** CLI-specific test files exist, **When** cleanup is performed, **Then** CLI-specific tests are removed while analysis module tests are preserved.
6. **Given** historical documentation (PRD and specs directories), **When** cleanup is performed, **Then** these directories are preserved unchanged for historical reference.

---

### User Story 6 - Agent Self-Test Command (Priority: P2)

A user installing a new agent wants to verify the agent is correctly configured and can communicate with the server. The user runs a self-test command that checks server connectivity, agent registration validity, tool availability, and authorized roots accessibility. The output clearly indicates pass/fail status for each check and provides remediation suggestions for any failures.

**Why this priority**: Self-test is a diagnostic tool that improves the setup experience but is not required for core functionality. Users can set up and use the agent without it, but it greatly reduces troubleshooting time.

**Independent Test**: Can be tested by running the self-test command on a correctly configured agent and verifying all checks pass, then by introducing configuration errors (invalid API key, unreachable server, missing authorized root) and verifying each produces the expected failure message with remediation advice.

**Acceptance Scenarios**:

1. **Given** a correctly configured agent, **When** the user runs the self-test command, **Then** all checks pass and a success summary is displayed.
2. **Given** an agent with an invalid or expired API key, **When** the user runs self-test, **Then** the registration check fails with a message to re-register the agent.
3. **Given** an agent with an unreachable server, **When** the user runs self-test, **Then** the connectivity check fails with the server URL and a suggestion to verify network settings.
4. **Given** an agent with an inaccessible authorized root (e.g., unmounted drive), **When** the user runs self-test, **Then** a warning is displayed for that root with a suggestion to mount it or remove it from configuration.
5. **Given** self-test completes with warnings but no failures, **When** results are displayed, **Then** the summary indicates the warning count and lists specific recommendations.

---

### Edge Cases

- What happens when a user tries to create a Collection for a path that is already registered as a Collection on the server? The system informs the user and suggests using the existing Collection.
- What happens when the test cache expires between testing and collection creation? The agent detects the stale cache and automatically re-runs the test.
- What happens when the collection cache is empty and the user attempts offline operations? The agent informs the user that a cache sync is required first and provides the sync command.
- What happens when offline results reference a collection that has been deleted on the server? The sync command reports the mismatch and allows the user to discard or re-assign the results.
- What happens when multiple agents are bound to the same collection? Each agent manages its own cache and results independently; the system handles this gracefully.
- What happens when the user specifies a path outside the agent's authorized roots during testing? The test issues a warning (advisory, not blocking) and proceeds, since test mode is for exploration.
- What happens when the local storage for offline results runs out of space? The agent detects write failures and informs the user with the storage location and size of pending results.

## Requirements *(mandatory)*

### Functional Requirements

#### Agent Test Command
- **FR-001**: System MUST provide an agent command to test a local path for accessibility, file enumeration, and optional analysis tool execution without server communication.
- **FR-002**: System MUST validate that the specified path exists, is readable, and contains files.
- **FR-003**: System MUST support filtering test execution to a specific analysis tool.
- **FR-004**: System MUST support an accessibility-only check mode that skips analysis execution.
- **FR-005**: System MUST support saving analysis results as a local HTML report file.
- **FR-006**: System MUST cache test results locally with a 24-hour expiration for use by collection creation.
- **FR-007**: System MUST display clear, actionable error messages for path accessibility failures.
- **FR-008**: System MUST issue an advisory warning (not a block) if the tested path is outside configured authorized roots.

#### Collection Creation via Agent
- **FR-010**: System MUST provide an agent command to create a Collection on the server from a local path.
- **FR-011**: System MUST use cached test results when available, or automatically run a test if no valid cache exists.
- **FR-012**: System MUST prompt for a Collection name interactively if not provided via command option, suggesting the folder name as default.
- **FR-013**: System MUST automatically bind the created Collection to the creating agent.
- **FR-014**: System MUST display the Collection identifier and web UI link upon successful creation.
- **FR-015**: System MUST support a skip-test option for advanced users who want to bypass validation.
- **FR-016**: System MUST support an analyze option that queues an initial analysis job immediately after creation.
- **FR-017**: System MUST require server connectivity for Collection creation and display a clear error if unreachable.

#### Offline Execution and Sync
- **FR-020**: System MUST provide an agent command to run analysis tools against a Collection identified by its unique identifier.
- **FR-021**: System MUST support offline mode that runs analysis locally without server communication, restricted to local Collections only.
- **FR-022**: System MUST reject offline execution requests for remote Collections (cloud storage) with a clear explanation.
- **FR-023**: System MUST store offline analysis results locally with collection identifier, tool name, timestamp, and agent metadata.
- **FR-024**: System MUST provide a sync command that uploads all pending offline results to the server.
- **FR-025**: System MUST support a dry-run option for sync that previews pending uploads without executing them.
- **FR-026**: System MUST support partial sync recovery, resuming interrupted uploads without duplicating results.
- **FR-027**: System MUST clean up local result files after successful upload.
- **FR-028**: System MUST support online mode (default) that creates a server job, executes locally, and reports results.

#### Collection Management
- **FR-030**: System MUST provide an agent command to list all Collections bound to the agent, displaying identifier, type, name, location, status, last analysis date, and offline capability.
- **FR-031**: System MUST support offline collection listing using locally cached data.
- **FR-032**: System MUST maintain a local collection cache that stores metadata for all agent-bound Collections.
- **FR-033**: System MUST set collection cache expiration to 7 days and display a warning when cache is stale.
- **FR-034**: System MUST provide a collection sync command to refresh the cache from the server.
- **FR-035**: System MUST auto-refresh the collection cache when listing collections in online mode.
- **FR-036**: System MUST provide a collection test command to re-verify a specific Collection's accessibility and update status on the server.
- **FR-037**: System MUST support filtering collection listings by type (local, remote, all) and status.

#### Server API Extensions
- **FR-040**: System MUST provide a server endpoint for agent-initiated Collection creation with automatic agent binding and team scoping.
- **FR-041**: System MUST provide a server endpoint for listing Collections bound to the requesting agent.
- **FR-042**: System MUST provide a server endpoint for uploading offline analysis results, validated against agent ownership and Collection existence.
- **FR-043**: System MUST provide a server endpoint for updating Collection accessibility status.

#### CLI Tool Removal
- **FR-050**: System MUST remove photo_stats.py, photo_pairing.py, and pipeline_validation.py from the repository root.
- **FR-051**: System MUST update the project constitution to replace the "Independent CLI Tools" principle with an "Agent-Only Tool Execution" principle.
- **FR-052**: System MUST update all project documentation (README, development guidelines, installation guide, configuration guide, tool-specific guides) to reference agent-based workflows exclusively.
- **FR-053**: System MUST preserve shared analysis modules and utilities that are used by the agent.
- **FR-054**: System MUST remove CLI-specific test files while preserving analysis module tests.
- **FR-055**: System MUST preserve historical documentation (PRD and specs directories) without modification.

#### Agent Self-Test
- **FR-060**: System MUST provide a self-test command that validates server connectivity, agent registration, tool availability, and authorized roots accessibility.
- **FR-061**: System MUST display pass/fail status for each check with clear remediation suggestions for failures.
- **FR-062**: System MUST display a summary indicating total warnings and failures.

### Key Entities

- **Test Cache Entry**: A cached record of a local path test result, containing the tested path, timestamp, file counts (total, photos, sidecars), tools tested, issues found, and expiration (24 hours). Used to avoid redundant testing during the test-then-create workflow.
- **Collection Cache**: A locally stored snapshot of all Collections bound to the agent, including each Collection's identifier, name, type, location, connector info, accessibility status, and last analysis date. Expires after 7 days. Enables offline collection listing and offline execution.
- **Offline Result**: An analysis result produced during offline execution, stored locally with the Collection identifier, tool name, execution timestamp, agent metadata, full analysis data, and optional HTML report. Pending upload to the server via the sync command.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can validate a local path and see file count and analysis summary within 30 seconds for collections of up to 10,000 files.
- **SC-002**: Users can create a Collection from a tested path in under 5 seconds (excluding test time), receiving a unique identifier and web link.
- **SC-003**: 95% of test-then-create workflows complete successfully on first attempt without errors.
- **SC-004**: Users can run analysis tools offline against local Collections and upload results when reconnected, with zero data loss during sync.
- **SC-005**: Offline results uploaded via sync are indistinguishable from online job results when viewed in the web application.
- **SC-006**: After CLI tool removal, zero unauthenticated tool executions are possible - all executions require agent authentication.
- **SC-007**: 100% of tool executions produce tracked job records with agent identity, timestamps, and result data.
- **SC-008**: All existing CLI tool functionality (analysis, reporting) remains available through agent commands.
- **SC-009**: Updated documentation covers 100% of workflows previously served by CLI tools, with agent-based equivalents.
- **SC-010**: Self-test command correctly identifies and reports all configuration issues with actionable remediation advice.

## Assumptions

- The distributed agent architecture (PRD-021) is fully implemented and agents can register, authenticate, and execute jobs.
- Analysis modules are decoupled from CLI tool scripts and can be invoked programmatically by the agent.
- The product is pre-release; backward compatibility with standalone CLI tools is not required.
- Users have the agent binary installed on machines where photo collections reside.
- Local Collections are stored on filesystems directly accessible to the agent process.
- Remote Collections (S3, GCS, SMB) always require network connectivity and cannot operate in offline mode.
- The agent's local storage directory has sufficient disk space for caching and offline results.
- Agent API keys provide sufficient authorization for Collection creation within the agent's team scope.

## Dependencies

- Distributed Agent Architecture (PRD-021 / Issue #90) must be implemented.
- Existing Collection API endpoints must support agent-authenticated requests.
- Analysis modules must be importable by the agent without CLI tool wrapper dependencies.
- Server job system must support agent-initiated job creation.
