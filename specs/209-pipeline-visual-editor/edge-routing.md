# Constrained Orthogonal Edge Routing

**Branch**: `209-pipeline-visual-editor` | **Date**: 2026-02-16

## Overview

Pipeline edges use a constrained orthogonal routing system that enforces exactly **1, 3, or 5 segments** with deterministic behavior. All edges are strictly horizontal/vertical (no diagonals). Users can adjust edge routing by dragging handles on non-pinned segments.

## Edge Configurations

Every edge falls into exactly one of three configurations based on endpoint positions and stored waypoints:

| Config | Segments | Shape | Condition | Handles |
|--------|----------|-------|-----------|---------|
| 1-seg | 1 | V | Co-aligned, non-loopback, no stored offsets | 1 (`ew-resize`) |
| 3-seg | 3 | V-H-V | Non-aligned, non-loopback | 1 (`ns-resize`) |
| 5-seg | 5 | V-H-V-H-V | Loopback OR user detour from 1-seg | 3 (`ns`, `ew`, `ns`) |

### Co-alignment

Endpoints are considered co-aligned when `|sourceX - targetX| < 5px` (the snap threshold).

### Loopback

An edge is a loopback when `sourceY >= targetY` (the source handle is at or below the target handle). Loopback edges always render as 5-seg with clockwise routing (source down, right, up, left, down to target).

## Rules

### Rule 1: No diagonals

All segments are strictly horizontal or vertical. Corners use quadratic bezier curves (`Q`) for visual smoothness (border radius = 5px).

### Rule 2: 1-seg drag creates 5-seg

When a co-aligned, non-loopback edge has its single handle dragged horizontally:
- 4 waypoints materialize, creating a V-H-V-H-V shape
- The H segments split at 33% and 67% of the vertical span
- 3 handles appear on the middle segments
- If the middle V is dragged back to align with source X, the edge snaps back to 1-seg

### Rule 3: 3-seg handle moves vertically only

For non-aligned, non-loopback edges:
- The single handle on the H segment drags vertically (`ns-resize`)
- V segments stay pinned to source/target X; H segment resizes horizontally
- If nodes move so endpoints become co-aligned, the edge auto-collapses to 1-seg

### Rule 4: Co-aligned to 3-seg on node move

Starting from a 1-seg edge, if a node moves so endpoints are no longer co-aligned, the edge automatically renders as 3-seg with the H segment at the vertical midpoint.

### Rule 5: Loopback always 5-seg

Loopback edges always render as 5-seg. Default geometry:
- `h1Y = sourceY + 30` (below source)
- `h2Y = targetY - 30` (above target)
- `vX = max(sourceX, targetX) + 80` (to the right)

The 3 handles on the middle segments allow full adjustment of the loop shape.

## Data Model

Edge routing data is stored as `waypoints?: Array<{x, y}>` in the API. The waypoint count determines the config:

| Waypoints | Config | Meaning |
|-----------|--------|---------|
| 0 (absent) | auto | Determined by endpoint positions |
| 2 | 3-seg | User-adjusted H segment Y position |
| 4 | 5-seg | User-created detour or adjusted loopback |

Waypoint X values for the first and last waypoint are always pinned to sourceX/targetX at render time (stale values from node moves are harmless).

## State Transitions

```
1-seg ──drag handle──→ 5-seg
1-seg ──move node (misalign)──→ 3-seg (auto, no stored wp)
3-seg ──drag H handle──→ 3-seg (store 2 wp)
3-seg ──move node (co-align)──→ 1-seg (auto, clear wp)
5-seg ──drag to co-align + not loopback──→ 1-seg (clear wp)
5-seg (loopback) ──any drag──→ 5-seg (never simplifies)
```

## Key Files

| File | Role |
|------|------|
| `frontend/src/components/pipelines/graph/edges/PipelineEdge.tsx` | Edge rendering, `computeEdgeConfig()`, `getHandles()`, drag logic |
| `frontend/src/components/pipelines/graph/utils/graph-transforms.ts` | `toApiEdges()` normalizes waypoints at save time using node positions |
| `frontend/src/hooks/usePipelineGraph.ts` | Passes nodes to `toApiEdges()` in `toApiFormat()` |

## API Exports

`PipelineEdge.tsx` exports three items for use by other modules and tests:

- **`computeEdgeConfig(sx, sy, tx, ty, storedWaypoints?)`** — Pure function returning `{ config, points, effectiveWaypoints }`
- **`getHandles(config, points)`** — Pure function returning handle descriptors with position and cursor
- **`EdgeConfig`** / **`EdgeConfigResult`** — TypeScript types

## Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `SNAP_THRESHOLD` | 5 | Pixels for co-alignment detection |
| `LOOPBACK_PAD` | 30 | Vertical padding for loopback H segments |
| `LOOPBACK_X_OFFSET` | 80 | Horizontal offset for loopback V segment |
| `BORDER_RADIUS` | 5 | Corner rounding radius |
| `HANDLE_RADIUS` | 7 | Drag handle circle radius |
