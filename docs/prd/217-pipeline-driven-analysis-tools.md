# PRD: Pipeline-Driven PhotoStats and Photo_Pairing Analysis Tools

**Issue**: [#217](https://github.com/fabrice-guiot/shuttersense/issues/217)
**Status**: Draft
**Created**: 2026-02-15
**Last Updated**: 2026-02-15 (v1.3)
**Related Documents**:
- [Domain Model](../domain-model.md)
- [Pipeline Validation Spec](../../specs/003-pipeline-validation/spec.md)
- [Photo Pairing Tool](./photo-pairing-tool.md)
- [Pipeline Visual Editor](./pipeline-visual-editor.md)

---

## Executive Summary

PhotoStats and Photo_Pairing currently derive their configuration (file extensions, camera mappings, processing suffixes) from the standalone `TeamConfigCache`, which mirrors the legacy `configurations` table. Meanwhile, the Pipeline definition already encodes the same information in its node parameters — Capture nodes define filename pattern matching, Processing nodes define recognized suffixes, and File nodes define expected extensions. Pipeline_Validation already consumes these Pipeline nodes directly, making it the most capable of the three analysis tools.

This PRD defines the migration of PhotoStats and Photo_Pairing from Config-based to Pipeline-based configuration, aligning all three tools on a single source of truth: the Pipeline assigned to (or defaulting for) the target Collection.

As a secondary outcome, this PRD introduces the **Camera entity** — a team-scoped repository of physical cameras. When analysis tools encounter a camera ID that matches a Capture node's pattern but has no corresponding Camera record, a new Camera is auto-created with a temporary status and name. This replaces the static `camera_mappings` dictionary in the Config with a living, discoverable registry.

### Key Design Decisions

1. **Pipeline is the single source of truth**: All three analysis tools derive extensions, suffixes, and pattern-matching rules from Pipeline nodes rather than the Config. The `configurations` table fields (`photo_extensions`, `metadata_extensions`, `processing_methods`, `camera_mappings`, `require_sidecar`) become obsolete for tool execution.
2. **Capture node drives filename parsing**: The Capture node's `filename_regex` and `camera_id_group` replace the hardcoded `FilenameParser` pattern for camera ID and counter extraction. PhotoStats and Photo_Pairing adopt the same regex-based parsing that Pipeline_Validation already uses.
3. **File nodes define extension lists**: The set of recognized image extensions and metadata extensions is derived from File nodes in the Pipeline graph, categorized by their position relative to the Capture node and their `extension` property.
4. **Processing nodes define suffixes**: Processing method names and suffixes come from Process node `method_ids` and node names, replacing the `processing_methods` dictionary in the Config.
5. **All-numeric suffixes remain hardcoded**: The "separate image" detection for all-numeric suffixes (e.g., `-2`, `-3`) remains a hardcoded convention, not configurable through the Pipeline.
6. **Camera auto-discovery**: New camera IDs detected during analysis trigger automatic Camera entity creation with `status: "temporary"` and a placeholder name, enabling progressive enrichment without blocking analysis.

---

## Background

### Current State

**Tool Configuration Sources:**

| Parameter | Config Source | Pipeline Equivalent | Currently Used By |
|-----------|-------------|---------------------|-------------------|
| Filename pattern | Hardcoded in `FilenameParser` (`[A-Z0-9]{4}[0-9]{4}`) | Capture node `filename_regex` | PhotoStats, Photo_Pairing |
| Camera ID extraction | Hardcoded (first 4 chars) | Capture node `camera_id_group` | Photo_Pairing |
| Photo extensions | `configurations.photo_extensions` | File nodes with image extensions | PhotoStats, Photo_Pairing |
| Metadata extensions | `configurations.metadata_extensions` | File nodes with `.xmp`/metadata extensions | PhotoStats |
| Require sidecar | `configurations.require_sidecar` | Pipeline path analysis (XMP pairing) | PhotoStats |
| Processing methods | `configurations.processing_methods` | Process node `method_ids` + node name | Photo_Pairing (currently passed `{}`) |
| Camera mappings | `configurations.cameras` | No Pipeline equivalent (→ Camera entity) | Photo_Pairing (currently passed `{}`) |

**Key Observations:**

1. **PhotoStats** (`agent/src/analysis/photostats_analyzer.py`) receives `photo_extensions`, `metadata_extensions`, and `require_sidecar` from `TeamConfigCache`. It does not use Pipeline data at all.

2. **Photo_Pairing** (`agent/src/analysis/photo_pairing_analyzer.py`) receives `photo_extensions` from `TeamConfigCache`. Its `calculate_analytics()` function is called with an empty dict `{}` as the config parameter (line 543 in `agent/cli/run.py`), meaning camera names and processing method descriptions are never resolved — a known gap.

3. **Pipeline_Validation** (`agent/src/analysis/pipeline_analyzer.py`) already derives its behavior entirely from the Pipeline definition via `build_pipeline_config()`. It does not reference the Config for pattern matching, extensions, or processing methods.

4. **Collection-Pipeline linkage** is already in place: `Collection.pipeline_id` (optional FK) and `Collection.pipeline_version` allow pinning a specific pipeline version. When `pipeline_id` is NULL, the team's default pipeline is used.

5. **Camera mappings** are static configuration entries. There is no Camera entity in the database yet, though one is defined in `docs/domain-model.md` with prefix `cam_` and planned for Phase 9.

### Problem Statement

PhotoStats and Photo_Pairing are limited compared to Pipeline_Validation because they rely on static Config entries rather than the richer, graph-structured Pipeline definition:

- **Rigid filename parsing**: The hardcoded `[A-Z0-9]{4}[0-9]{4}` pattern in `FilenameParser` cannot accommodate alternative naming conventions that the Capture node's configurable regex supports.
- **Static extension lists**: Adding a new file format requires updating the `configurations` table rather than being derived from the Pipeline's File nodes.
- **Missing processing method resolution**: Photo_Pairing currently passes an empty config, so camera IDs and processing suffixes appear as raw codes rather than human-readable names.
- **No sidecar inference**: PhotoStats uses a separate `require_sidecar` list in the Config, while Pipeline_Validation can infer sidecar requirements from path analysis (e.g., `.XMP` → `.CR3` pairing detected through connected File nodes).
- **Static camera registry**: Camera mappings are a flat dictionary in Config with no ability to auto-discover new cameras or track camera metadata over time.

### Strategic Context

Unifying all analysis tools on the Pipeline definition:
- **Single source of truth**: Teams configure their Pipeline once; all tools respect it consistently.
- **Progressive enrichment**: Camera auto-discovery builds a living equipment registry as collections are analyzed.
- **Pipeline adoption incentive**: Users who invest in defining their Pipeline get richer analysis from all tools, not just Pipeline_Validation.
- **Foundation for future tools**: New analysis tools (storage health, deduplication, etc.) can derive their configuration from the same Pipeline nodes.

---

## Goals

### Primary Goals

1. **Pipeline-derived extensions**: PhotoStats and Photo_Pairing derive image and metadata extension lists from the Pipeline's File nodes instead of Config entries.
2. **Pipeline-derived filename parsing**: PhotoStats and Photo_Pairing use the Capture node's `filename_regex` and `camera_id_group` for camera ID and counter extraction instead of the hardcoded `FilenameParser` pattern.
3. **Pipeline-derived processing suffixes**: Photo_Pairing resolves processing method names from Process node names and `method_ids` instead of the Config's `processing_methods` dictionary.
4. **Pipeline-derived sidecar requirements**: PhotoStats infers `require_sidecar` from Pipeline path analysis (File nodes connected through paths that include both image and metadata extensions).
5. **Camera entity auto-discovery**: When a previously unseen camera ID is encountered during analysis, a Camera record is auto-created in the team's Camera repository with `status: "temporary"`.
6. **Backward compatibility**: When no Pipeline is assigned to a Collection (and no team default exists), tools fall back to Config-based parameters, preserving existing behavior.

### Secondary Goals

7. **Camera name resolution in Photo_Pairing**: `calculate_analytics()` resolves camera IDs to Camera entity names (display_name or model) instead of showing raw 4-character codes.
8. **Processing method name from node name**: Processing method descriptions in Photo_Pairing reports use the Pipeline Process node's display name rather than the raw method_id code.
9. **Consistent tool behavior**: All three tools (PhotoStats, Photo_Pairing, Pipeline_Validation) produce consistent results when run against the same Collection and Pipeline.

### Non-Goals (v1)

1. **Config table removal**: The `configurations` table fields (`photo_extensions`, `metadata_extensions`, etc.) are not deleted. They serve as fallback and may still be used for non-Pipeline contexts.
2. **FilenameParser deprecation**: `FilenameParser` remains available as a utility but is no longer the primary parsing mechanism for Pipeline-aware tools.
3. **Camera EXIF enrichment**: Auto-discovering camera serial numbers, make, and model from EXIF metadata is out of scope. Camera records are created with minimal information (camera_id, temporary name).
4. **Camera merge/dedup UI**: Handling cases where the same physical camera has multiple camera IDs (firmware changes, etc.) is deferred.
5. **Pipeline editor changes**: No changes to the Pipeline visual editor or Pipeline validation rules. Existing node types and properties are sufficient.
6. **TeamConfigCache restructuring**: The agent's cache format may evolve in implementation but the overall caching mechanism is not redesigned.

---

## User Personas

### Primary: Team Administrator / Pipeline Author

- **Need**: Define the Pipeline once and have all analysis tools respect it consistently.
- **Pain Point**: Currently must maintain both Pipeline nodes and Config entries in sync. Adding a new file format means updating Config extensions even though the Pipeline already has the File node.
- **Goal**: Configuring a Pipeline is sufficient — PhotoStats and Photo_Pairing automatically adapt.

### Secondary: Photographer / Analyst

- **Need**: Run PhotoStats or Photo_Pairing on a Collection and get accurate, named results (camera names, processing method descriptions).
- **Pain Point**: Photo_Pairing reports show raw camera IDs (`AB3D`) and processing codes (`HDR`) instead of human-readable names (`Canon EOS R5`, `High Dynamic Range`).
- **Goal**: Reports display meaningful names drawn from the Camera repository and Pipeline Process nodes.

---

## Requirements

### Functional Requirements

#### FR-100: Pipeline Configuration Extraction

- **FR-100.1**: Create a `PipelineToolConfig` data structure that extracts tool-relevant configuration from a Pipeline definition:
  ```python
  class PipelineToolConfig:
      filename_regex: str           # From Capture node
      camera_id_group: int          # From Capture node (1 or 2)
      photo_extensions: Set[str]    # From File nodes (image types)
      metadata_extensions: Set[str] # From File nodes (metadata types)
      require_sidecar: Set[str]     # Inferred from path analysis
      processing_suffixes: Dict[str, str]  # method_id → node display name
  ```
- **FR-100.2**: `photo_extensions` MUST be derived by collecting the `extension` property from all File nodes whose extension is **not** a recognized metadata format. Implementations MUST NOT rely on a hardcoded list of image extensions — any File node extension that is not in the `METADATA_EXTENSIONS` set (currently `{".xmp"}`) is treated as an image extension. This ensures new image formats added to the Pipeline are automatically recognized without code changes. See FR-600.1/FR-600.2 for the complete categorization rules.
- **FR-100.3**: `metadata_extensions` MUST be derived from File nodes whose `extension` is in the recognized metadata formats set (`METADATA_EXTENSIONS`, currently `{".xmp"}`). When new metadata formats are introduced (e.g., `.mie`), they are added to this single set — no hardcoded image extension list needs updating.
- **FR-100.4**: `require_sidecar` MUST be inferred by analyzing Pipeline paths: if a path exists from the Capture node through File nodes where an image extension and a metadata extension appear in connected nodes (siblings — same parent Process or Capture node), then the image extension requires a sidecar. For example, if a Capture node outputs to both a `.cr3` File node and an `.xmp` File node, then `.cr3` requires a sidecar.
- **FR-100.5**: `processing_suffixes` MUST be derived from all Process nodes in the Pipeline. Each Process node's `method_ids` array provides the suffix codes; the node's `name` property provides the human-readable description. Example: Process node named "HDR Merge" with `method_ids: ["HDR"]` yields `{"HDR": "HDR Merge"}`.
- **FR-100.6**: `filename_regex` MUST be taken directly from the Capture node's properties and MUST NOT use a default fallback. The property is required by pipeline validation (`pipeline_service` appends a "missing filename_regex" error when absent), so a missing value indicates a pipeline validation bug and MUST raise an error during extraction. `camera_id_group` MAY default to `1` if not explicitly set, as this is the conventional first capture group.
- **FR-100.7**: If the Pipeline has no Capture node (invalid pipeline), the extraction MUST fail with a clear error. Tools MUST NOT proceed with an invalid Pipeline.

#### FR-200: PhotoStats — Pipeline Integration

- **FR-200.1**: `_run_photostats()` MUST accept a `PipelineToolConfig` (or None for fallback) in addition to its current parameters.
- **FR-200.2**: When `PipelineToolConfig` is provided, PhotoStats MUST use `pipeline_config.photo_extensions` instead of `team_config.photo_extensions`.
- **FR-200.3**: When `PipelineToolConfig` is provided, PhotoStats MUST use `pipeline_config.metadata_extensions` instead of `team_config.metadata_extensions`.
- **FR-200.4**: When `PipelineToolConfig` is provided, PhotoStats MUST use `pipeline_config.require_sidecar` instead of `team_config.require_sidecar`.
- **FR-200.5**: When `PipelineToolConfig` is None (no Pipeline available), PhotoStats MUST fall back to `TeamConfigCache` values, preserving current behavior.

#### FR-300: Photo_Pairing — Pipeline Integration

- **FR-300.1**: `_run_photo_pairing()` MUST accept a `PipelineToolConfig` (or None for fallback) in addition to its current parameters.
- **FR-300.2**: When `PipelineToolConfig` is provided, `build_imagegroups()` MUST use `pipeline_config.filename_regex` and `pipeline_config.camera_id_group` for filename parsing instead of the hardcoded `FilenameParser` pattern.
- **FR-300.3**: The all-numeric suffix detection for "separate image" grouping MUST remain hardcoded and unchanged. Only non-numeric suffixes are matched against `pipeline_config.processing_suffixes`.
- **FR-300.4**: When `PipelineToolConfig` is provided, `calculate_analytics()` MUST use `pipeline_config.processing_suffixes` for method name resolution instead of an empty dict.
- **FR-300.5**: When `PipelineToolConfig` is provided, Photo_Pairing MUST use `pipeline_config.photo_extensions` to filter photo files.
- **FR-300.6**: When `PipelineToolConfig` is None, Photo_Pairing MUST fall back to `TeamConfigCache` values and the hardcoded `FilenameParser`, preserving current behavior.

#### FR-400: Camera Entity & Auto-Discovery

- **FR-400.1**: Create a `Camera` database model with the following fields. The model MUST use `ExternalIdMixin` (not `GuidMixin`) to match the codebase pattern for GUID generation (prefix `cam_`):
  ```python
  class Camera(Base, ExternalIdMixin, AuditMixin):
      __tablename__ = "cameras"
      GUID_PREFIX = "cam"   # → cam_01hgw2bbg...
      team_id: int          # FK(teams.id), not null
      camera_id: str        # 4-char ID from filenames, not null
      status: str           # "temporary" | "confirmed", default "temporary"
      display_name: str     # User-assigned name, nullable
      make: str             # Manufacturer, nullable
      model: str            # Model name, nullable
      serial_number: str    # Serial number, nullable
      notes: str            # Free text, nullable
      metadata_json: JSONB  # Custom metadata, nullable
  ```
- **FR-400.2**: `Camera.camera_id` + `Camera.team_id` MUST have a unique constraint. Each team has at most one Camera record per camera ID.
- **FR-400.3**: Create a `GET /api/cameras` endpoint (team-scoped, paginated) for listing cameras.
- **FR-400.4**: Create a `GET /api/cameras/{guid}` endpoint for retrieving a single camera.
- **FR-400.5**: Create a `PUT /api/cameras/{guid}` endpoint for updating camera details (confirming status, adding make/model/serial, renaming).
- **FR-400.6**: Create a `DELETE /api/cameras/{guid}` endpoint for deleting a camera.
- **FR-400.7**: Create a `GET /api/cameras/stats` endpoint returning KPI statistics (total cameras, confirmed count, temporary count).
- **FR-400.8**: Create an **internal** (agent-facing) `POST /api/agent/v1/cameras/discover` endpoint that accepts an array of camera IDs discovered during analysis. For each camera ID not already in the team's Camera table, a new Camera record MUST be created with `status: "temporary"` and `display_name` set to the camera_id itself (e.g., `"AB3D"`). Already-existing camera IDs MUST be skipped (idempotent).
- **FR-400.9**: The discover endpoint MUST return the full list of Camera records (both existing and newly created) for the submitted camera IDs, so the agent can map camera_id → display_name for reporting.
- **FR-400.10**: Camera auto-discovery MUST occur during the analysis phase: after `build_imagegroups()` extracts unique camera IDs, the agent calls the discover endpoint before `calculate_analytics()`, then passes the resolved camera names to analytics.

#### FR-500: Agent — Pipeline Resolution for Tool Execution

- **FR-500.1**: When executing PhotoStats or Photo_Pairing, the agent MUST resolve the Pipeline for the target Collection:
  1. If `Collection.pipeline_id` is set, use that Pipeline (at `Collection.pipeline_version` if pinned).
  2. If `Collection.pipeline_id` is NULL, use the team's default Pipeline.
  3. If no default Pipeline exists, fall back to Config-based behavior.
- **FR-500.2**: The resolved Pipeline's nodes and edges MUST be passed through `PipelineToolConfig` extraction (FR-100) before being provided to the analysis tools.
- **FR-500.3**: The `TeamConfigCache` MUST continue to include Config-based parameters as a fallback. The cache MAY also include the Collection's assigned pipeline (if different from the team default).
- **FR-500.4**: If the assigned Pipeline is invalid (fails structure validation), the agent MUST log a warning and fall back to Config-based parameters rather than failing the analysis.

#### FR-600: Extension Categorization from File Nodes

- **FR-600.1**: File nodes MUST be categorized as "image" or "metadata" based on their `extension` property and the `METADATA_EXTENSIONS` set (currently `{".xmp"}`). The categorization rules are:
  - **Metadata**: Any extension present in `METADATA_EXTENSIONS` (case-insensitive)
  - **Image**: Any extension **not** in `METADATA_EXTENSIONS`
  Implementations MUST NOT use a hardcoded list of image extensions. The image category is defined by exclusion: everything that is not metadata is an image.
- **FR-600.2**: The categorization MUST NOT rely on a hardcoded list of image extensions. Any File node extension that is not in `METADATA_EXTENSIONS` is treated as an image extension. This ensures new image formats added to the Pipeline (e.g., `.heif`, `.jxl`) are automatically recognized without code changes. Only the `METADATA_EXTENSIONS` set needs to be maintained.
- **FR-600.3**: File nodes marked as `optional: true` MUST still be included in the extension sets. Optional files are valid extensions — their optionality affects validation, not recognition.

#### FR-700: Sidecar Requirement Inference

- **FR-700.1**: A `require_sidecar` relationship MUST be inferred when a **non-optional** image File node and a **non-optional** metadata File node share a common parent node (connected via edges from the same upstream node). Only non-optional (i.e., `optional: false` or `optional` not set) metadata File nodes create hard sidecar requirements.
- **FR-700.2**: Example: If a Capture node has edges to both a `.cr3` File node (non-optional) and a `.xmp` File node (non-optional), then `.cr3` is inferred to require a `.xmp` sidecar. However, if the `.xmp` File node has `optional: true`, no sidecar requirement is inferred for `.cr3`.
- **FR-700.3**: If multiple non-optional metadata File nodes exist (e.g., `.xmp` and a future `.mie`), each creates a separate sidecar requirement for sibling image File nodes. Optional metadata File nodes are excluded from sidecar inference.
- **FR-700.4**: The inference MUST handle Process nodes as intermediate parents. If a Process node outputs to both a `.tiff` File node and a non-optional `.xmp` File node, then `.tiff` requires a `.xmp` sidecar at that pipeline stage. If the `.xmp` node is optional, no requirement is created.
- **FR-700.5**: File nodes with `optional: true` MUST NOT create hard `require_sidecar` relationships for sibling image File nodes. Optional metadata is recognized as a valid extension (per FR-600.3) but its absence does not constitute an orphan or validation error. This ensures that Pipeline authors can mark metadata as "supported but not mandatory" without triggering false orphan reports in PhotoStats. Note: a future enhancement may introduce a soft/warning behavior where optional metadata absence produces a non-blocking warning rather than an error, but v1 treats optional metadata as fully non-binding for sidecar inference.

#### FR-800: Frontend — "Resources" Page Consolidation

The Camera management UI is introduced alongside an existing Pipelines page. Rather than adding a new top-level menu entry for Cameras, both are consolidated under a single **"Resources"** page with tabs — following the same pattern as the existing "Directory" page (which hosts Locations, Organizers, and Performers as tabs).

- **FR-800.1**: Create a new `ResourcesPage` component at `frontend/src/pages/ResourcesPage.tsx` using the tab pattern from `DirectoryPage.tsx` (URL-synced tabs via `useSearchParams`).
- **FR-800.2**: The Resources page MUST have two initial tabs:
  - **Cameras** (`?tab=cameras`) — Camera list with CRUD, status filtering, and auto-discovered camera management.
  - **Pipelines** (`?tab=pipelines`) — The existing `PipelinesPage` content refactored into a `PipelinesTab` component.
- **FR-800.3**: The sidebar menu entry MUST replace the current "Pipelines" entry:
  - **id**: `resources`
  - **icon**: `Box` (from lucide-react — represents equipment/resources; distinct from existing icons)
  - **label**: "Resources"
  - **href**: `/resources`
- **FR-800.4**: The route configuration in `App.tsx` MUST replace the `/pipelines` route:
  ```typescript
  {
    path: '/resources',
    element: <ResourcesPage />,
    pageTitle: 'Resources',
    pageIcon: Box,
    pageHelp: 'Manage cameras, pipelines, and other equipment resources',
  }
  ```
- **FR-800.5**: The old `/pipelines` route MUST redirect to `/resources?tab=pipelines` for backward compatibility (bookmarks, shared links).
- **FR-800.6**: The default tab when navigating to `/resources` (no `?tab` param) MUST be `cameras`.
- **FR-800.7**: The existing `PipelinesPage` component MUST be refactored into a `PipelinesTab` component. All Pipeline functionality (list, create, edit, delete, activate, validate, import/export) MUST be preserved in the tab form. The KPI stats (total pipelines, active count, default pipeline) MUST continue to be set in the TopHeader when the Pipelines tab is active.
- **FR-800.8**: When the Cameras tab is active, the TopHeader KPI stats MUST show Camera-specific stats (total cameras, confirmed count, temporary count) from the `GET /api/cameras/stats` endpoint.
- **FR-800.9**: Each tab MUST manage its own action buttons following the existing tabbed page pattern: tabs + action buttons on the same row, with responsive stacking on mobile.

### Non-Functional Requirements

#### NFR-100: Performance

- **NFR-100.1**: `PipelineToolConfig` extraction from a Pipeline definition MUST complete in under 10ms for pipelines with up to 100 nodes.
- **NFR-100.2**: Camera auto-discovery (batch endpoint) MUST handle up to 50 unique camera IDs in a single request within 200ms.
- **NFR-100.3**: Analysis tool execution time MUST NOT increase by more than 5% compared to Config-based execution (Pipeline extraction overhead is negligible).

#### NFR-200: Data Integrity

- **NFR-200.1**: Camera auto-creation MUST be idempotent. Concurrent analysis jobs discovering the same camera ID MUST NOT create duplicate Camera records. The implementation MUST use a DB-agnostic pattern (not PostgreSQL-specific `INSERT ... ON CONFLICT`): perform an explicit check-before-insert within the same transaction using `session.query(Camera).filter_by(team_id=..., camera_id=...)` and create only if not found, or use `session.merge()`. This ensures tests run on SQLite and production on PostgreSQL without dialect-specific SQL. The unique constraint on `(team_id, camera_id)` serves as a safety net for race conditions.
- **NFR-200.2**: Pipeline-derived extension sets MUST be case-insensitive. `.DNG` and `.dng` are treated as the same extension.
- **NFR-200.3**: `PipelineToolConfig` extraction MUST be deterministic — the same Pipeline definition always produces the same config.

#### NFR-300: Backward Compatibility

- **NFR-300.1**: Existing analysis results generated under Config-based parameters MUST remain valid and viewable. No migration of historical results is required.
- **NFR-300.2**: Collections without an assigned Pipeline (and no team default) MUST continue to work with Config-based parameters. No analysis tool may fail solely because no Pipeline is available.
- **NFR-300.3**: The `TeamConfigCache` format change MUST be backward-compatible. Agents with older cache files MUST gracefully handle missing Pipeline fields.
- **NFR-300.4**: The `FilenameParser` utility MUST NOT be modified or deleted. It remains available for non-Pipeline contexts (e.g., standalone validation utilities).

#### NFR-400: Testing

- **NFR-400.1**: Unit tests MUST verify `PipelineToolConfig` extraction for representative Pipeline definitions (simple linear, branching, looping, multi-file).
- **NFR-400.2**: Unit tests MUST verify PhotoStats produces identical results when given Pipeline-derived extensions vs. equivalent Config-based extensions.
- **NFR-400.3**: Unit tests MUST verify Photo_Pairing correctly uses Capture node regex for filename parsing.
- **NFR-400.4**: Unit tests MUST verify Camera auto-discovery creates records for new IDs and skips existing ones.
- **NFR-400.5**: Unit tests MUST verify fallback behavior when no Pipeline is available.
- **NFR-400.6**: Integration tests MUST verify the full flow: Collection → Pipeline resolution → config extraction → tool execution → Camera auto-discovery → result with resolved names.

---

## Technical Approach

### 1. PipelineToolConfig Extraction

**File**: `agent/src/analysis/pipeline_tool_config.py` (new)

```python
from dataclasses import dataclass, field
from typing import Dict, Optional, Set

from src.analysis.pipeline_config_builder import build_pipeline_config, PipelineConfig


METADATA_EXTENSIONS = {".xmp"}  # Recognized metadata formats


@dataclass
class PipelineToolConfig:
    """Tool-relevant configuration extracted from a Pipeline definition."""

    filename_regex: str
    camera_id_group: int
    photo_extensions: Set[str]
    metadata_extensions: Set[str]
    require_sidecar: Set[str]
    processing_suffixes: Dict[str, str]  # method_id → display name


def extract_tool_config(
    nodes_json: list,
    edges_json: list,
) -> PipelineToolConfig:
    """
    Extract tool-relevant configuration from Pipeline node/edge definitions.

    Args:
        nodes_json: Pipeline nodes as stored in DB
        edges_json: Pipeline edges as stored in DB

    Returns:
        PipelineToolConfig with extensions, regex, suffixes, and sidecar rules

    Raises:
        ValueError: If Pipeline has no Capture node or is structurally invalid
    """
    config = build_pipeline_config(nodes_json, edges_json)

    # --- Capture node ---
    if not config.capture_nodes:
        raise ValueError("Pipeline has no Capture node; cannot extract tool config")

    capture = config.capture_nodes[0]
    props = _get_node_properties(nodes_json, capture.id)

    # filename_regex is required — pipeline_service validates its presence
    # when saving a Pipeline (appends "missing filename_regex" error).
    # No default fallback: a missing value is a Pipeline validation bug
    # and must surface as a clear error rather than silently degrading.
    if "filename_regex" not in props:
        raise ValueError(
            f"Capture node '{capture.id}' is missing required "
            "'filename_regex' property"
        )
    filename_regex = props["filename_regex"]
    camera_id_group = int(props.get("camera_id_group", 1))

    # --- File nodes → extension sets ---
    photo_exts: Set[str] = set()
    metadata_exts: Set[str] = set()

    for file_node in config.file_nodes:
        ext = file_node.extension.lower()
        if ext in METADATA_EXTENSIONS:
            metadata_exts.add(ext)
        else:
            photo_exts.add(ext)

    # --- Process nodes → suffix map ---
    processing_suffixes: Dict[str, str] = {}
    for proc_node in config.process_nodes:
        for method_id in proc_node.method_ids:
            if method_id:  # Skip empty-string method_ids (no suffix)
                processing_suffixes[method_id] = proc_node.name or method_id

    # --- Sidecar inference ---
    require_sidecar = _infer_sidecar_requirements(
        nodes_json, edges_json, photo_exts, metadata_exts
    )

    return PipelineToolConfig(
        filename_regex=filename_regex,
        camera_id_group=camera_id_group,
        photo_extensions=photo_exts,
        metadata_extensions=metadata_exts,
        require_sidecar=require_sidecar,
        processing_suffixes=processing_suffixes,
    )
```

### 2. Sidecar Inference from Pipeline Paths

```python
def _infer_sidecar_requirements(
    nodes_json: list,
    edges_json: list,
    photo_exts: Set[str],
    metadata_exts: Set[str],
) -> Set[str]:
    """
    Infer which image extensions require a sidecar file.

    Rule: If a parent node (Capture or Process) has edges to both an image
    File node and a NON-OPTIONAL metadata File node, the image extension
    requires a sidecar. Optional metadata File nodes (optional: true) do
    NOT create sidecar requirements — their absence is not an error.
    """
    # Build parent → children map
    children_by_parent: Dict[str, list] = {}
    for edge in edges_json:
        parent = edge["from"]
        child = edge["to"]
        children_by_parent.setdefault(parent, []).append(child)

    # Build node lookup
    node_lookup = {n["id"]: n for n in nodes_json}

    require_sidecar: Set[str] = set()

    for parent_id, child_ids in children_by_parent.items():
        child_nodes = [node_lookup.get(cid) for cid in child_ids]
        child_file_nodes = [
            n for n in child_nodes
            if n and n.get("type") == "file"
        ]

        # Only non-optional metadata File nodes create sidecar requirements
        has_required_metadata = any(
            n["properties"].get("extension", "").lower() in metadata_exts
            and not n["properties"].get("optional", False)
            for n in child_file_nodes
        )

        if has_required_metadata:
            for n in child_file_nodes:
                ext = n["properties"].get("extension", "").lower()
                if ext in photo_exts:
                    require_sidecar.add(ext)

    return require_sidecar
```

### 3. Camera Entity Model

**File**: `backend/src/models/camera.py` (new)

```python
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from backend.src.models.base import Base
from backend.src.models.mixins.external_id import ExternalIdMixin
from backend.src.models.mixins.audit import AuditMixin


class Camera(Base, ExternalIdMixin, AuditMixin):
    """Physical camera equipment tracked per team."""

    __tablename__ = "cameras"
    GUID_PREFIX = "cam"

    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    camera_id = Column(String(10), nullable=False)  # e.g., "AB3D"
    status = Column(String(20), nullable=False, default="temporary")
    display_name = Column(String(100), nullable=True)
    make = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("team_id", "camera_id", name="uq_cameras_team_camera_id"),
    )

    team = relationship("Team", back_populates="cameras")
```

**Reciprocal relationship on Team model** (`backend/src/models/team.py` — existing file, add relationship):

```python
# Add to Team model
cameras = relationship("Camera", back_populates="team")
```

### 4. Camera Discovery Endpoint & Service (Agent-Facing)

**Endpoint** (`backend/src/api/agent/camera_routes.py` — new):

```python
@router.post("/cameras/discover")
async def discover_cameras(
    request: CameraDiscoverRequest,
    agent: Agent = Depends(get_authenticated_agent),
    db: Session = Depends(get_db),
) -> CameraDiscoverResponse:
    """
    Register newly discovered camera IDs from analysis.
    Idempotent: existing camera IDs are skipped.
    """
    service = CameraService(db)
    cameras = service.discover_cameras(
        camera_ids=request.camera_ids,
        team_id=agent.team_id,
        user_id=agent.system_user_id,
    )
    return CameraDiscoverResponse(cameras=cameras)
```

**Service** (`backend/src/services/camera_service.py` — discover method, DB-agnostic):

```python
def discover_cameras(
    self,
    camera_ids: List[str],
    team_id: int,
    user_id: Optional[int] = None,
) -> List[Camera]:
    """
    Idempotent camera discovery: create records for new IDs, skip existing.

    Uses DB-agnostic check-before-insert (no INSERT ON CONFLICT) so tests
    run on SQLite and production on PostgreSQL without dialect-specific SQL.
    """
    results: List[Camera] = []
    for camera_id in camera_ids:
        existing = (
            self.db.query(Camera)
            .filter_by(team_id=team_id, camera_id=camera_id)
            .first()
        )
        if existing:
            results.append(existing)
        else:
            try:
                camera = Camera(
                    team_id=team_id,
                    camera_id=camera_id,
                    status="temporary",
                    display_name=camera_id,
                    created_by_user_id=user_id,
                    updated_by_user_id=user_id,
                )
                self.db.add(camera)
                self.db.flush()  # Triggers unique constraint check
                results.append(camera)
            except IntegrityError:
                # Race condition: another request created it concurrently
                self.db.rollback()
                existing = (
                    self.db.query(Camera)
                    .filter_by(team_id=team_id, camera_id=camera_id)
                    .first()
                )
                if existing:
                    results.append(existing)
    return results
```

### 5. Modified Tool Execution Flow

**File**: `agent/cli/run.py` (modified)

```python
def _execute_tool(
    tool: str,
    file_infos: list,
    location: str,
    team_config: TeamConfigCache,
    pipeline_tool_config: Optional[PipelineToolConfig] = None,
    http_client: Optional[AgentApiClient] = None,
) -> tuple[Dict[str, Any], Optional[str]]:
    """Execute analysis tool with Pipeline-derived or Config-based parameters.

    Args:
        http_client: AgentApiClient for online operations (camera discovery).
            None when running in offline mode.
    """

    if pipeline_tool_config:
        photo_extensions = pipeline_tool_config.photo_extensions
        metadata_extensions = pipeline_tool_config.metadata_extensions
        require_sidecar = pipeline_tool_config.require_sidecar
    else:
        photo_extensions = set(team_config.photo_extensions)
        metadata_extensions = set(team_config.metadata_extensions)
        require_sidecar = set(team_config.require_sidecar)

    if tool == "photostats":
        return _run_photostats(
            file_infos, photo_extensions, metadata_extensions,
            require_sidecar, location
        )
    elif tool == "photo_pairing":
        return _run_photo_pairing(
            file_infos, photo_extensions, location,
            pipeline_tool_config=pipeline_tool_config,
            http_client=http_client,
        )
    elif tool == "pipeline_validation":
        # Pipeline_Validation already derives its config from the Pipeline
        # definition internally via build_pipeline_config(). It does NOT use
        # PipelineToolConfig because it requires the full PipelineConfig graph
        # structure (nodes, edges, paths) rather than the simplified extraction.
        # The photo_extensions and metadata_extensions passed here are used
        # only for file filtering before the pipeline graph is applied.
        return _run_pipeline_validation(
            file_infos, photo_extensions, metadata_extensions,
            team_config, location
        )
    else:
        raise ValueError(f"Unknown tool: {tool}")
```

**Design note on Pipeline_Validation**: `_run_pipeline_validation()` invokes `build_pipeline_config()` directly on `team_config.default_pipeline.nodes` and `team_config.default_pipeline.edges` to obtain the full `PipelineConfig` graph structure. This is intentionally different from how PhotoStats and Photo_Pairing consume the Pipeline: those tools use the simplified `PipelineToolConfig` extraction (extensions, regex, suffixes) while Pipeline_Validation needs the complete graph for path traversal and validation. The `photo_extensions` and `metadata_extensions` parameters forwarded to Pipeline_Validation are used only for initial file filtering (which files to analyze), and these are already derived from `PipelineToolConfig` when a Pipeline is available, ensuring consistency across all three tools at the file-selection level.

### 6. Photo_Pairing with Pipeline-Driven Parsing

```python
def _run_photo_pairing(
    file_infos: list,
    photo_extensions: set[str],
    location: str,
    pipeline_tool_config: Optional[PipelineToolConfig] = None,
    http_client: Optional[AgentApiClient] = None,
) -> tuple[Dict[str, Any], Optional[str]]:
    """Run Photo Pairing with Pipeline or Config parameters.

    Args:
        file_infos: Pre-loaded list of FileInfo objects.
        photo_extensions: Set of recognized photo file extensions.
        location: Local filesystem path (for report display).
        pipeline_tool_config: Pipeline-derived config, or None for fallback.
        http_client: AgentApiClient for online camera discovery. When None
            (offline mode), camera discovery falls back to identity mapping.
    """

    photo_files = [f for f in file_infos if f.extension in photo_extensions]

    # Use Pipeline regex if available, otherwise fall back to FilenameParser
    group_result = build_imagegroups(
        photo_files,
        filename_regex=pipeline_tool_config.filename_regex if pipeline_tool_config else None,
        camera_id_group=pipeline_tool_config.camera_id_group if pipeline_tool_config else None,
    )

    imagegroups = group_result.get("imagegroups", [])
    invalid_files = group_result.get("invalid_files", [])

    # Camera auto-discovery — passes http_client for online lookup;
    # falls back to identity mapping when http_client is None (offline)
    camera_names = _discover_cameras(imagegroups, http_client=http_client)

    # Build analytics config from Pipeline or empty dict
    analytics_config = {}
    if pipeline_tool_config:
        analytics_config["processing_methods"] = pipeline_tool_config.processing_suffixes
    if camera_names:
        analytics_config["camera_mappings"] = {
            cid: [{"name": name}] for cid, name in camera_names.items()
        }

    analytics = calculate_analytics(imagegroups, analytics_config)
    # ... (rest of reporting unchanged)
```

### 7. Camera Auto-Discovery Function

**File**: `agent/cli/run.py` (new function)

```python
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _discover_cameras(
    imagegroups: List[dict],
    http_client: Optional[AgentApiClient] = None,
    timeout: int = 5,
) -> Dict[str, str]:
    """
    Discover and register camera IDs found during analysis.

    Extracts unique camera IDs from imagegroups, calls the server's
    discovery endpoint to register new cameras and resolve display names.

    Args:
        imagegroups: List of imagegroup dicts from build_imagegroups(),
            each containing a "camera_id" field.
        http_client: Optional AgentApiClient instance. When None (offline
            mode or unconfigured), skips the server call and returns
            identity-mapped fallback.
        timeout: HTTP request timeout in seconds.

    Returns:
        Dict mapping each discovered camera_id to its display_name.
        Example: {"AB3D": "Canon EOS R5", "XYZW": "XYZW"}

    Offline/failure behavior:
        On network error, timeout, non-200 response, or when http_client
        is None, returns a fallback dict mapping each camera_id to itself
        (identity mapping) and logs a warning. This ensures analysis
        never fails due to camera discovery issues.
    """
    # Extract and deduplicate camera IDs from imagegroups
    camera_ids: set[str] = set()
    for group in imagegroups:
        cid = group.get("camera_id")
        if cid:
            camera_ids.add(cid)

    if not camera_ids:
        return {}

    unique_ids = sorted(camera_ids)  # Sort for deterministic requests

    # Fallback: identity mapping (camera_id → camera_id)
    fallback = {cid: cid for cid in unique_ids}

    if http_client is None:
        logger.info(
            "Camera discovery skipped (no HTTP client): %d camera IDs",
            len(unique_ids),
        )
        return fallback

    try:
        # POST /api/agent/v1/cameras/discover
        # Request body: {"camera_ids": ["AB3D", "XYZW"]}
        # Response body: {"cameras": [{"camera_id": "AB3D", "display_name": "Canon EOS R5"}, ...]}
        response = http_client.discover_cameras(
            camera_ids=unique_ids,
            timeout=timeout,
        )
        # Build mapping from response
        result: Dict[str, str] = {}
        for cam in response.get("cameras", []):
            cid = cam.get("camera_id", "")
            name = cam.get("display_name") or cid  # Fallback to ID if name is null
            result[cid] = name
        # Ensure all requested IDs are present (server may omit on error)
        for cid in unique_ids:
            if cid not in result:
                result[cid] = cid
        return result

    except Exception as e:
        logger.warning(
            "Camera discovery failed (%s): %d camera IDs will use raw IDs. "
            "Error: %s",
            type(e).__name__,
            len(unique_ids),
            e,
        )
        return fallback
```

### 8. Pipeline Resolution in Agent Run Flow

```python
# In the run command, after resolving team_config:

pipeline_tool_config = None

# Determine which pipeline to use for this collection
pipeline = _resolve_collection_pipeline(collection_guid, team_config)

if pipeline:
    try:
        pipeline_tool_config = extract_tool_config(
            nodes_json=pipeline.nodes,
            edges_json=pipeline.edges,
        )
    except ValueError as e:
        click.echo(
            click.style("Warning: ", fg="yellow")
            + f"Pipeline config extraction failed: {e}. "
            "Falling back to server configuration."
        )

# Build HTTP client for online operations (camera discovery, etc.)
# http_client is None when running in --offline mode.
http_client = _build_api_client(config) if not offline else None

# Pass to tool execution
analysis_data, report_html = _execute_tool(
    tool, file_infos, location, team_config,
    pipeline_tool_config=pipeline_tool_config,
    http_client=http_client,
)
```

### 8. Data Flow Diagram

```
Collection
  │
  ├── pipeline_id (assigned) ──→ Pipeline (specific version)
  │         OR                         │
  ├── pipeline_id = NULL ──→ Team Default Pipeline
  │                                    │
  │                         ┌──────────┴──────────┐
  │                         │  extract_tool_config │
  │                         └──────────┬──────────┘
  │                                    │
  │                         PipelineToolConfig
  │                         ├── filename_regex
  │                         ├── camera_id_group
  │                         ├── photo_extensions
  │                         ├── metadata_extensions
  │                         ├── require_sidecar
  │                         └── processing_suffixes
  │                                    │
  ├─────────────────────┬──────────────┼─────────────────┐
  │                     │              │                  │
  PhotoStats      Photo_Pairing    Pipeline_Validation  (future tools)
  │                     │
  │                     ├── build_imagegroups(regex)
  │                     ├── Camera auto-discover
  │                     └── calculate_analytics(suffixes, cameras)
  │
  └── Config fallback (when no Pipeline available)
```

---

## Implementation Plan

### Phase 1: PipelineToolConfig Extraction & Camera Entity

**Tasks:**

1. Create `agent/src/analysis/pipeline_tool_config.py` with `PipelineToolConfig` dataclass and `extract_tool_config()` function
2. Implement File node extension categorization (image vs. metadata)
3. Implement Process node suffix extraction
4. Implement sidecar requirement inference from Pipeline paths
5. Create `Camera` model in `backend/src/models/camera.py`
6. Add reciprocal `cameras` relationship to the `Team` model (`backend/src/models/team.py`)
7. Create Alembic migration for `cameras` table with unique constraint on `(team_id, camera_id)`
8. Create `CameraService` in `backend/src/services/camera_service.py` with CRUD operations and `discover_cameras()` method
9. Create Camera API schemas in `backend/src/schemas/camera.py`
10. Create Camera API endpoints (`GET /api/cameras`, `GET /api/cameras/{guid}`, `PUT /api/cameras/{guid}`, `DELETE /api/cameras/{guid}`, `GET /api/cameras/stats`)
11. Create agent-facing `POST /api/agent/v1/cameras/discover` endpoint
12. Add `discover_cameras(camera_ids: List[str], timeout: int = 5) -> Dict[str, Any]` method to `AgentApiClient` (`agent/src/api_client.py`). The method issues a `POST` to `/api/agent/v1/cameras/discover` with `{"camera_ids": [...]}` and returns the JSON response body. This is the client-side counterpart of the server's `CameraService.discover_cameras()` and is called by `_discover_cameras()` (§7).
13. Unit tests for `extract_tool_config()` with various Pipeline structures
14. Unit tests for Camera service (CRUD, discover, idempotency)
15. Unit tests for `AgentApiClient.discover_cameras()` (mock HTTP, verify request shape and response parsing)

**Checkpoint**: `PipelineToolConfig` correctly extracted from Pipeline definitions. Camera entity exists with CRUD API and agent discovery endpoint.

---

### Phase 2: PhotoStats Pipeline Integration

**Tasks:**

1. Modify `_execute_tool()` in `agent/cli/run.py` to accept optional `PipelineToolConfig`
2. Add Pipeline resolution logic: Collection pipeline → team default → Config fallback
3. Wire `PipelineToolConfig` extensions into `_run_photostats()` when available
4. Verify `calculate_stats()` and `analyze_pairing()` produce identical results with Pipeline-derived extensions vs. Config-based extensions
5. Add fallback behavior when no Pipeline is available
6. Unit tests comparing Pipeline-driven vs. Config-driven PhotoStats results
7. Integration test: end-to-end PhotoStats with Pipeline

**Checkpoint**: PhotoStats uses Pipeline-derived extensions when available, falls back to Config gracefully.

---

### Phase 3: Photo_Pairing Pipeline Integration

**Tasks:**

1. Extend `build_imagegroups()` to accept optional `filename_regex` and `camera_id_group` parameters
2. Implement regex-based filename parsing alongside existing `FilenameParser` fallback
3. Wire `PipelineToolConfig` into `_run_photo_pairing()`
4. Pass `processing_suffixes` from Pipeline to `calculate_analytics()` for method name resolution
5. Integrate Camera auto-discovery into Photo_Pairing flow (call discover endpoint, map names)
6. Pass resolved camera names to `calculate_analytics()` via config dict
7. Unit tests for regex-based filename parsing with various Capture node configurations
8. Unit tests for processing suffix resolution from Pipeline Process nodes
9. Unit tests for Camera auto-discovery integration
10. Integration test: end-to-end Photo_Pairing with Pipeline and Camera discovery

**Checkpoint**: Photo_Pairing uses Pipeline regex for parsing, resolves camera and method names from Pipeline and Camera entity.

---

### Phase 4: Agent Pipeline Resolution & Cache Updates

**Tasks:**

1. Add Collection-specific pipeline resolution to agent run flow (check `Collection.pipeline_id`, then team default)
2. Update `TeamConfigCache` to optionally include Collection-assigned pipeline data
3. Add server endpoint for fetching Collection's assigned pipeline (if not already available)
4. Handle invalid Pipeline gracefully (log warning, fall back to Config)
5. Handle offline mode: Pipeline data cached alongside team config
6. Integration test: full agent run with Collection → Pipeline → tool execution flow
7. Test offline execution with cached Pipeline data

**Checkpoint**: Agent resolves correct Pipeline per Collection, extracts config, passes to tools. Offline mode works.

---

### Phase 5: Frontend — "Resources" Page & Camera Management UI

**Tasks:**

1. Create `ResourcesPage` component at `frontend/src/pages/ResourcesPage.tsx` with URL-synced tabs (`useSearchParams`), following the `DirectoryPage.tsx` pattern
2. Refactor existing `PipelinesPage` into a `PipelinesTab` component (preserve all Pipeline functionality: list, CRUD, activate, validate graph, import/export, KPI stats)
3a. Add the new `/resources` route in `App.tsx` pointing to `<ResourcesPage />` with `pageTitle: 'Resources'`, `pageIcon: Box`, and `pageHelp` text
3b. Convert the existing `/pipelines` route in `App.tsx` to a redirect to `/resources?tab=pipelines` for backward compatibility (bookmarks, shared links). Both the new route (3a) and the redirect (3b) MUST coexist in the route configuration.
4. Update `Sidebar.tsx`: replace "Pipelines" menu entry with "Resources" (`Box` icon, `/resources` href)
5. Create `CamerasTab` component with Camera list table (columns: Camera ID, Display Name, Make, Model, Status, Modified)
6. Add Camera edit dialog for confirming temporary cameras (status → confirmed, add make/model/serial/notes)
7. Add Camera status filter (All / Temporary / Confirmed)
8. Wire TopHeader KPI stats per-tab: Camera stats when Cameras tab is active, Pipeline stats when Pipelines tab is active
9. Create `useCameras` hook and Camera API service
10. Add Camera TypeScript contracts in `frontend/src/contracts/api/camera-api.ts`
11. Wire Camera names into Photo_Pairing results display (reports show resolved names)
12. Component tests for ResourcesPage, CamerasTab, PipelinesTab, and Camera edit dialog

**Checkpoint**: "Resources" menu entry replaces "Pipelines". Cameras tab shows auto-discovered cameras with edit/confirm flow. Pipelines tab preserves all existing functionality. `/pipelines` redirects to `/resources?tab=pipelines`.

---

## Alternatives Considered

### Configuration Source Strategy

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Pipeline-derived config (chosen)** | Single source of truth; consistent with Pipeline_Validation; auto-adapts when Pipeline changes | Requires fallback logic for no-Pipeline case; more complex extraction | **Selected** — aligns all tools on same data source |
| Keep Config as primary, add Pipeline override | No migration needed; simpler | Two sources of truth; Config drift from Pipeline; doesn't solve the core problem | Rejected — perpetuates duplication |
| Merge Config into Pipeline model | Cleanest data model; no duplication | Breaking change to Pipeline schema; migration complexity; Config used by non-tool features | Rejected — too disruptive for v1 |

### Camera Discovery Strategy

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Auto-create with temporary status (chosen)** | Zero friction; progressive enrichment; analysis never blocked | Potential for many temporary records; needs cleanup UX | **Selected** — best UX for discovery |
| Require pre-registration | Clean data from start | Blocks analysis on unknown cameras; high friction | Rejected — contradicts YAGNI |
| Config-only (current) | No new entity | Static; no auto-discovery; no enrichment over time | Rejected — doesn't meet requirements |

### Filename Parsing Strategy

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Use Capture node regex (chosen)** | Consistent with Pipeline_Validation; configurable per-pipeline | More complex than hardcoded pattern; regex errors possible | **Selected** — leverages existing Pipeline configuration |
| Keep FilenameParser hardcoded | Simple; no changes needed | Cannot accommodate alternative naming conventions; inconsistent with Pipeline | Rejected — fundamental limitation for this issue |
| New configurable parser class | Clean API; testable | Over-engineered; Capture node regex already exists | Rejected — unnecessary abstraction |

---

## Risks and Mitigation

### Risk 1: Pipeline Regex Errors Break Analysis

- **Impact**: High — Photo_Pairing would fail to parse any filenames, producing zero results.
- **Probability**: Low — Capture node regex is validated when the Pipeline is saved (must match `sample_filename` with exactly 2 capture groups).
- **Mitigation**: Wrap regex parsing in try/except; on failure, fall back to `FilenameParser` hardcoded pattern and log a warning. Never crash the analysis due to regex issues.

### Risk 2: Extension Categorization Ambiguity

- **Impact**: Medium — A File node extension could be miscategorized (e.g., `.mie` as image instead of metadata).
- **Probability**: Low — Currently only `.xmp` is a recognized metadata format. New formats are rare.
- **Mitigation**: FR-600.1 defines explicit categorization rules. If new metadata formats emerge, the `METADATA_EXTENSIONS` set is the single place to update. For v1 the `.xmp` convention is sufficient.

### Risk 3: Camera Auto-Discovery Creates Noise

- **Impact**: Low — Many temporary Camera records for teams with diverse collections.
- **Probability**: Medium — Collections with varied camera IDs will generate many records.
- **Mitigation**: Temporary cameras are clearly marked. The Camera list UI filters by status. A future bulk-cleanup action can remove unconfirmed cameras older than N days.

### Risk 4: Concurrent Camera Discovery Race Condition

- **Impact**: Medium — Duplicate Camera records for the same camera_id.
- **Probability**: Low — Unique constraint on `(team_id, camera_id)` prevents duplicates at the DB level.
- **Mitigation**: Use a DB-agnostic check-before-insert within the same transaction (see NFR-200.1). The unique constraint acts as a safety net: if a race condition causes a duplicate insert attempt, the `IntegrityError` is caught and the existing record is returned. The discover endpoint handles conflicts gracefully without dialect-specific SQL.

### Risk 5: No Pipeline Available (New/Unconfigured Teams)

- **Impact**: Medium — Tools would have no configuration source.
- **Probability**: Medium — New teams may not have created a Pipeline yet.
- **Mitigation**: Explicit fallback to Config-based parameters (FR-200.5, FR-300.6, FR-500.1). Tools never fail solely due to missing Pipeline. Clear warning in analysis output when using Config fallback.

### Risk 6: Sidecar Inference Produces Incorrect Requirements

- **Impact**: Medium — PhotoStats may report false orphans (images missing sidecars that aren't actually required).
- **Probability**: Low — Sidecar inference is based on explicit Pipeline structure (sibling File nodes).
- **Mitigation**: The inference algorithm is conservative: only sibling relationships trigger sidecar requirements. Pipeline authors control this by their graph structure. Config-based `require_sidecar` remains as fallback.

---

## Affected Entities Summary

| Entity | Change Type | Details |
|--------|-------------|---------|
| Camera | **New** | New model, migration, service, API endpoints, frontend tab |
| Collection | Unchanged | Existing `pipeline_id` / `pipeline_version` fields are sufficient |
| Pipeline | Unchanged | No schema changes; existing node properties are sufficient |
| PipelineConfig | Extended | `PipelineToolConfig` is a new extraction layer, not a model change |
| TeamConfigCache | Extended | May include Collection-specific pipeline data for offline use |
| PhotoStats Analyzer | Modified | Accepts Pipeline-derived extensions |
| Photo_Pairing Analyzer | Modified | Accepts Pipeline regex, suffixes, and camera names |
| FilenameParser | Unchanged | Retained as fallback utility |
| PipelinesPage | **Refactored** | Extracted into `PipelinesTab`; hosted within new `ResourcesPage` |
| ResourcesPage | **New** | New tabbed page replacing Pipelines in sidebar; hosts Cameras and Pipelines tabs |
| Sidebar | Modified | "Pipelines" entry replaced by "Resources" (`Box` icon, `/resources` href) |
| App.tsx routes | Modified | `/pipelines` route replaced by `/resources`; redirect added for backward compat |

---

## Success Metrics

- **M1**: 100% of PhotoStats and Photo_Pairing executions on Pipeline-assigned Collections use Pipeline-derived configuration.
- **M2**: Photo_Pairing reports display resolved camera names (from Camera entity) instead of raw 4-character codes.
- **M3**: Photo_Pairing reports display resolved processing method names (from Pipeline Process nodes) instead of raw codes.
- **M4**: PhotoStats sidecar detection matches Pipeline path structure (inferred `require_sidecar` consistent with Pipeline_Validation).
- **M5**: Camera auto-discovery creates records for new camera IDs within the analysis flow (zero manual pre-registration required).
- **M6**: No analysis failures when no Pipeline is available (Config fallback works for 100% of cases).

---

## Dependencies

### Internal Dependencies

- Pipeline model and service (existing — `backend/src/models/pipeline.py`, `backend/src/services/pipeline_service.py`)
- Pipeline config builder (existing — `agent/src/analysis/pipeline_config_builder.py`)
- Collection-Pipeline linkage (existing — `Collection.pipeline_id`)
- Audit mixin (existing — `backend/src/models/mixins/audit.py`)
- GUID service (existing — `backend/src/services/guid.py`)
- Agent authentication (existing — `backend/src/api/agent/`)

### External Dependencies

- None — no new Python packages required

### New GUID Prefix

| Entity | Prefix | Example |
|--------|--------|---------|
| Camera | `cam_` | `cam_01hgw2bbg0000000000000001` |

---

## Future Enhancements

### v1.1
- **Camera EXIF enrichment**: Extract camera make, model, and serial number from EXIF metadata during analysis and update Camera records automatically.
- **Camera merge UI**: Allow merging multiple Camera records that represent the same physical camera (e.g., after firmware update changes the camera ID).
- **Pipeline diff for tools**: Show what changes in analysis behavior when switching a Collection's Pipeline assignment.
- **Processing Software tab**: Add a third tab to the Resources page for tracking processing software (Lightroom, Capture One, etc.) referenced by Pipeline Process nodes.

### v2.0
- **Config table cleanup**: Once all teams have Pipelines, deprecate the tool-related fields in `configurations` table.
- **Per-collection extension override**: Allow Collections to override Pipeline-derived extensions for edge cases.
- **Camera health analysis**: Actuation tracking and maintenance predictions using the Camera entity (as described in domain model Phase 9).
- **Lenses tab**: Add a Lenses tab to the Resources page for tracking lens equipment, linked to Camera bodies.
- **Tool configuration preview**: Show what parameters each tool will use before running analysis, based on the resolved Pipeline.

---

## Revision History

- **2026-02-15 (v1.3)**: Review feedback round 2 — 3 fixes
  - **§6 `_run_photo_pairing` http_client**: Added `http_client: Optional[AgentApiClient]` parameter to `_run_photo_pairing()` and `_execute_tool()`. Updated call site to pass `http_client` through to `_discover_cameras()` so online camera lookup works instead of always falling back to identity mapping. Updated §8 pipeline resolution flow to construct `http_client` and pass it to `_execute_tool()`.
  - **Phase 1 Task 12 (new)**: Add `discover_cameras()` method to `AgentApiClient` (`agent/src/api_client.py`) — the client-side counterpart of `CameraService.discover_cameras()`. Task 15 added for corresponding unit tests.
  - **FR-100.6 / §1 filename_regex**: Removed default regex fallback (`r"([A-Z0-9]{4})([0-9]{4})"`) from `extract_tool_config()`. `filename_regex` is now required — a missing property raises `ValueError` instead of silently degrading. This aligns with `pipeline_service` validation which already enforces the property's presence. `camera_id_group` retains its default of `1`.
- **2026-02-15 (v1.2)**: Review feedback — 7 clarifications and fixes
  - **FR-700.5 (new)**: Optional metadata File nodes (`optional: true`) MUST NOT create hard `require_sidecar` relationships. Updated FR-700.1–FR-700.4 examples and §2 sidecar inference code to exclude optional metadata.
  - **§7 _discover_cameras (new)**: Added full specification with function signature `_discover_cameras(imagegroups, http_client=None, timeout=5)`, camera ID extraction/dedup, HTTP call to discover endpoint, return shape (`Dict[str, str]`), and offline/failure fallback (identity mapping + logged warning).
  - **Phase 1 Task 6 (new)**: Add reciprocal `cameras` relationship to Team model (`backend/src/models/team.py`). Updated §3 Camera model code with reciprocal relationship note.
  - **Phase 5 Task 3 split**: Split into Task 3a (add `/resources` route in `App.tsx`) and Task 3b (convert `/pipelines` to redirect to `/resources?tab=pipelines`), clarifying both must coexist.
  - **FR-400.1 mixin fix**: Changed Camera model declaration from `GuidMixin` to `ExternalIdMixin` to match codebase pattern. Added `GUID_PREFIX = "cam"`.
  - **FR-100.2 / FR-600.1–600.2 alignment**: Removed hardcoded image extension list from FR-100.2. Both sections now consistently state that any non-`METADATA_EXTENSIONS` extension is an image extension. Implementations MUST NOT rely on hardcoded image format lists.
  - **NFR-200.1 / Risk 4 / §4 DB-agnostic**: Replaced PostgreSQL-specific `INSERT ... ON CONFLICT` with DB-agnostic check-before-insert pattern using `session.query().filter_by()` + `IntegrityError` catch. Added full `discover_cameras()` service method implementation.
  - **§5 pipeline_validation clarification**: Added inline comment and design note explaining that Pipeline_Validation intentionally does NOT use `PipelineToolConfig` — it invokes `build_pipeline_config()` directly for the full graph structure. The shared `photo_extensions`/`metadata_extensions` ensure file-selection consistency.
- **2026-02-15 (v1.1)**: Added "Resources" page consolidation (FR-800)
  - New FR-800 section: Camera and Pipelines consolidated under a tabbed "Resources" page, replacing the standalone Pipelines menu entry
  - Follows the existing `DirectoryPage.tsx` tab pattern (URL-synced tabs via `useSearchParams`)
  - Sidebar: "Pipelines" entry replaced by "Resources" with `Box` icon
  - `/pipelines` redirect to `/resources?tab=pipelines` for backward compatibility
  - Rewrote Phase 5 with Resources page creation, PipelinesPage → PipelinesTab refactor, and CamerasTab
  - Updated Affected Entities with PipelinesPage refactor, ResourcesPage, Sidebar, and App.tsx route changes
  - Added Processing Software tab (v1.1) and Lenses tab (v2.0) to Future Enhancements
- **2026-02-15 (v1.0)**: Initial draft
  - Defined Pipeline-to-tool configuration extraction via `PipelineToolConfig`
  - Specified integration of Pipeline-derived extensions, regex, and suffixes into PhotoStats and Photo_Pairing
  - Designed Camera entity with auto-discovery during analysis
  - Specified sidecar requirement inference from Pipeline path analysis
  - Created 5-phase implementation plan
  - Documented fallback behavior when no Pipeline is available
  - Catalogued alternatives considered and risks
