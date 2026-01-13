# API Contracts: Page Layout Cleanup

**Feature Branch**: `015-page-layout-cleanup`

## No API Changes

This feature is a **frontend-only UI cleanup**. There are no:
- New API endpoints
- Modified API responses
- Backend schema changes
- Database migrations

## Rationale

The feature scope is limited to:
1. Removing duplicate page titles from the UI
2. Adding a help tooltip mechanism (static content)
3. Repositioning action buttons within pages

All changes are contained within React components and do not require backend coordination.

## Existing APIs Used

The feature continues to use existing APIs without modification:
- Collection stats: `GET /api/collections/stats`
- Connector stats: `GET /api/connectors/stats`
- Event stats: `GET /api/events/stats`
- Pipeline stats: `GET /api/pipelines/stats`
- Result stats: `GET /api/results/stats`

These power the TopHeader KPI display, which remains unchanged.
