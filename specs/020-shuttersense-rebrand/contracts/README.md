# API Contracts: ShutterSense.ai Application Rebrand

**Feature**: 020-shuttersense-rebrand
**Date**: 2026-01-17

## Overview

This rebrand feature does **not** introduce any new API endpoints or modify existing API contracts.

## Changes

### No API Contract Changes

The rebrand is purely cosmetic/naming focused:
- No new endpoints
- No request/response schema changes
- No authentication changes
- No authorization changes

### Metadata Updates Only

The following API metadata will be updated (not contract changes):

| Property | Old Value | New Value |
|----------|-----------|-----------|
| FastAPI App Title | "Photo Admin API" | "ShutterSense.ai API" |
| FastAPI App Description | (current) | Updated with ShutterSense.ai branding |
| OpenAPI docs title | "Photo Admin API" | "ShutterSense.ai API" |

These changes affect the `/docs` (Swagger UI) and `/redoc` pages only. They do not affect API functionality or contracts.

## Existing Contracts

All existing API contracts remain unchanged:
- `/api/auth/*` - Authentication endpoints
- `/api/collections/*` - Collection management
- `/api/connectors/*` - Storage connector management
- `/api/pipelines/*` - Pipeline configuration
- `/api/events/*` - Event management
- `/api/admin/*` - Admin endpoints
- `/health` - Health check
- `/api/version` - Version information (returns ShutterSense.ai branding)

## Notes

This contracts directory exists for completeness in the planning workflow. No OpenAPI schema files are generated as there are no API changes.
