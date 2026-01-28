# Inventory Import API Documentation

This document describes the inventory import endpoints for cloud storage bucket inventory integration.

**Issue #107**: Cloud Storage Bucket Inventory Import

## Overview

The inventory import feature allows ShutterSense to discover folders from S3 Inventory or GCS Storage Insights reports instead of making expensive cloud API calls. This provides:

- **Cost savings**: No per-request charges for folder discovery
- **Performance**: Process millions of files in seconds
- **Efficiency**: Delta detection between imports

## Endpoints

All inventory endpoints are under `/api/connectors/{guid}/inventory/*`.

### Configure Inventory Source

```http
PUT /api/connectors/{guid}/inventory/config
Content-Type: application/json
Authorization: Bearer {token}

{
  "config": {
    "provider": "s3",
    "destination_bucket": "my-inventory-bucket",
    "source_bucket": "my-photo-bucket",
    "config_name": "daily-inventory",
    "format": "CSV"
  },
  "schedule": "weekly"
}
```

**Response:**
```json
{
  "guid": "con_01hgw2bbg0000000000000001",
  "name": "My S3 Bucket",
  "type": "s3",
  "inventory_config": {
    "provider": "s3",
    "destination_bucket": "my-inventory-bucket",
    "source_bucket": "my-photo-bucket",
    "config_name": "daily-inventory",
    "format": "CSV"
  },
  "inventory_schedule": "weekly"
}
```

### Validate Configuration

```http
POST /api/connectors/{guid}/inventory/validate
Authorization: Bearer {token}
```

**Response (server-side credentials):**
```json
{
  "success": true,
  "message": "Found 3 inventory manifest(s)",
  "validation_status": "validated",
  "job_guid": null
}
```

**Response (agent-side credentials):**
```json
{
  "success": true,
  "message": "Validation job created for agent",
  "validation_status": "pending",
  "job_guid": "job_01hgw2bbg0000000000000001"
}
```

### Get Inventory Status

```http
GET /api/connectors/{guid}/inventory/status
Authorization: Bearer {token}
```

**Response:**
```json
{
  "validation_status": "validated",
  "validation_error": null,
  "latest_manifest": "2026-01-26T01-00Z/manifest.json",
  "last_import_at": "2026-01-24T10:00:00Z",
  "next_scheduled_at": "2026-01-25T00:00:00Z",
  "folder_count": 42,
  "mapped_folder_count": 15,
  "mappable_folder_count": 27,
  "current_job": null
}
```

### Trigger Import

```http
POST /api/connectors/{guid}/inventory/import
Authorization: Bearer {token}
```

**Response:**
```json
{
  "job_guid": "job_01hgw2bbg0000000000000001",
  "message": "Inventory import job created"
}
```

**Error (concurrent import):**
```json
{
  "message": "An inventory import job is already running",
  "existing_job_guid": "job_01hgw2bbg0000000000000001"
}
```

### List Discovered Folders

```http
GET /api/connectors/{guid}/inventory/folders?unmapped_only=true&limit=100
Authorization: Bearer {token}
```

**Response:**
```json
{
  "folders": [
    {
      "guid": "fld_01hgw2bbg0000000000000001",
      "path": "2020/Vacation/",
      "object_count": 150,
      "total_size_bytes": 3750000000,
      "deepest_modified": "2020-08-15T14:30:00Z",
      "discovered_at": "2026-01-25T10:00:00Z",
      "collection_guid": null,
      "suggested_name": "2020 - Vacation",
      "is_mappable": true
    }
  ],
  "total_count": 42,
  "has_more": false
}
```

### Create Collections from Folders

```http
POST /api/collections/from-inventory
Content-Type: application/json
Authorization: Bearer {token}

{
  "connector_guid": "con_01hgw2bbg0000000000000001",
  "folders": [
    {
      "folder_guid": "fld_01hgw2bbg0000000000000001",
      "name": "2020 - Vacation",
      "state": "archived",
      "pipeline_guid": null
    },
    {
      "folder_guid": "fld_01hgw2bbg0000000000000002",
      "name": "2021 - Wedding",
      "state": "closed",
      "pipeline_guid": "pip_01hgw2bbg0000000000000001"
    }
  ]
}
```

**Response:**
```json
{
  "created": [
    {
      "collection_guid": "col_01hgw2bbg0000000000000001",
      "folder_guid": "fld_01hgw2bbg0000000000000001",
      "name": "2020 - Vacation"
    },
    {
      "collection_guid": "col_01hgw2bbg0000000000000002",
      "folder_guid": "fld_01hgw2bbg0000000000000002",
      "name": "2021 - Wedding"
    }
  ],
  "errors": []
}
```

## Provider Configuration

### S3 Inventory

```json
{
  "provider": "s3",
  "destination_bucket": "my-inventory-bucket",
  "destination_prefix": "Inventories/MyProject",
  "source_bucket": "my-photo-bucket",
  "config_name": "daily-inventory",
  "format": "CSV"
}
```

**Inventory path pattern:**
```text
s3://{destination_bucket}/{destination_prefix}/{source_bucket}/{config_name}/{timestamp}/manifest.json
```

### GCS Storage Insights

```json
{
  "provider": "gcs",
  "destination_bucket": "my-inventory-bucket",
  "report_config_name": "photo-inventory",
  "format": "CSV"
}
```

**Inventory path pattern:**
```text
gs://{destination_bucket}/{report_config_name}/{date}/manifest.json
```

## Import Pipeline Phases

The inventory import job executes in three phases:

### Phase A: Folder Extraction

Parses inventory files to extract unique folder paths.

**Progress events:**
```json
{
  "phase": "folder_extraction",
  "progress_percentage": 45,
  "message": "Processing data file 2/5"
}
```

### Phase B: FileInfo Population

Populates file metadata (size, modification date, ETag) for mapped collections.

**Progress events:**
```json
{
  "phase": "file_info_population",
  "progress_percentage": 75,
  "message": "Processing collection 10/15"
}
```

### Phase C: Delta Detection

Compares current inventory against stored FileInfo to detect changes.

**Progress events:**
```json
{
  "phase": "delta_detection",
  "progress_percentage": 90,
  "message": "Computing deltas for 15 collections"
}
```

## Delta Summary

After import, collections include delta information:

```json
{
  "file_info_delta": {
    "new_count": 10,
    "modified_count": 5,
    "deleted_count": 2,
    "new_size_bytes": 250000000,
    "modified_size_change_bytes": 50000000,
    "deleted_size_bytes": 10000000,
    "total_changes": 17,
    "is_first_import": false,
    "computed_at": "2026-01-25T10:30:00Z"
  }
}
```

## Scheduled Imports

Inventory imports can be scheduled:

| Schedule | Frequency |
|----------|-----------|
| `manual` | Only when triggered via API |
| `daily` | Every day at midnight UTC |
| `weekly` | Every Sunday at midnight UTC |

## Error Handling

### Common Errors

| Status | Error | Description |
|--------|-------|-------------|
| 400 | No inventory configuration | Configure inventory before importing |
| 400 | Configuration not validated | Validate configuration first |
| 404 | Connector not found | Invalid connector GUID |
| 409 | Import already running | Wait for current import to complete |

### Validation Errors

```json
{
  "success": false,
  "message": "No manifest.json found at expected location",
  "validation_status": "failed",
  "job_guid": null
}
```

## Agent API Endpoints

For agent-side credential connectors, the agent reports results via:

- `POST /api/agent/v1/jobs/{job_guid}/inventory/folders` - Phase A results
- `POST /api/agent/v1/jobs/{job_guid}/inventory/file-info` - Phase B results
- `POST /api/agent/v1/jobs/{job_guid}/inventory/delta` - Phase C results

See the OpenAPI documentation at `/docs` for full schema details.
