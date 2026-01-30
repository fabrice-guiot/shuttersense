# Data Model: ShutterSense.ai Application Rebrand

**Feature**: 020-shuttersense-rebrand
**Date**: 2026-01-17

## Overview

This rebrand feature does **not** introduce any new data entities or modify existing database schemas. The application's data model remains unchanged.

## Entities Affected

### No Database Changes

The rebrand is purely cosmetic/naming focused:
- No new tables
- No column changes
- No migrations required
- No data transformations needed

### Configuration Entities (Non-Database)

The following non-database configuration items are updated:

#### Brand Identity Configuration

| Property | Old Value | New Value |
|----------|-----------|-----------|
| Application Name | Photo Admin | ShutterSense.ai |
| Short Name | photo-admin | ShutterSense |
| Abbreviated Name | PHOTO_ADMIN | SHUSAI |
| Tagline | (none) | Capture. Process. Analyze. |
| Domain | (none) | shuttersense.ai |

#### Logo Assets (New Files)

| Asset | Path | Dimensions |
|-------|------|------------|
| Sidebar Logo (SVG) | `frontend/public/logo.svg` | Scalable |
| Sidebar Logo (PNG) | `frontend/public/logo.png` | 200x50 / 400x100 @2x |
| Login Logo (PNG) | `frontend/public/logo-login.png` | 512x512+ |
| Login Logo (WebP) | `frontend/public/logo-login.webp` | 512x512+ |
| Favicon (ICO) | `frontend/public/favicon.ico` | 16/32/48 |
| Favicon (PNG) | `frontend/public/favicon-192.png` | 192x192 |
| Apple Touch Icon | `frontend/public/apple-touch-icon.png` | 180x180 |
| Favicon (SVG) | `frontend/public/favicon.svg` | Scalable |
| Open Graph Image | `frontend/public/og-image.png` | 1200x630 |

## Environment Variables

Environment variable names are updated (not database stored):

| Old Name | New Name |
|----------|----------|
| PHOTO_ADMIN_DB_URL | SHUSAI_DB_URL |
| PHOTO_ADMIN_MASTER_KEY | SHUSAI_MASTER_KEY |
| PHOTO_ADMIN_LOG_LEVEL | SHUSAI_LOG_LEVEL |
| PHOTO_ADMIN_LOG_DIR | SHUSAI_LOG_DIR |
| PHOTO_ADMIN_ENV | SHUSAI_ENV |
| PHOTO_ADMIN_AUTHORIZED_LOCAL_ROOTS | SHUSAI_AUTHORIZED_LOCAL_ROOTS |
| PHOTO_ADMIN_SPA_DIST_PATH | SHUSAI_SPA_DIST_PATH |
| PHOTO_ADMIN_VERSION | SHUTTERSENSE_VERSION |

## Validation Rules

N/A - No data validation changes.

## State Transitions

N/A - No workflow or state changes.

## Relationships

N/A - No relationship changes.

## Notes

This data model document exists for completeness in the planning workflow. The actual data model of the application (Collections, Connectors, Pipelines, Events, Users, Teams, etc.) remains completely unchanged by the rebrand.
