# PRD: Adobe Lightroom Cloud Connector

**Issue**: #TBD
**Status**: Draft
**Created**: 2026-01-13
**Last Updated**: 2026-01-13
**Related Features**:
- 004-remote-photos-persistence (Connector architecture)
- 013-cloud-drive-connectors (OAuth patterns)

---

## Executive Summary

This PRD defines requirements for integrating Adobe Lightroom Cloud as a storage connector in photo-admin. Unlike file-based storage systems (S3, OneDrive, Google Drive), Lightroom is a **photo processing platform** with its own data model of catalogs, albums, and assets. This integration enables photographers to analyze their professionally-managed Lightroom libraries directly, without export.

### Strategic Significance

Adobe Lightroom is the industry-standard photo management platform for professional and serious amateur photographers. Integration provides:

1. **Professional Workflow Integration**: Photographers already organizing in Lightroom can analyze without disrupting workflow
2. **Metadata Richness**: Access to develop settings, ratings, keywords, and organizational structure
3. **Market Differentiation**: Few tools offer direct Lightroom cloud analysis
4. **Complete Photo Ecosystem**: Combined with OneDrive/Google Drive, covers all major photo storage

### Complexity Assessment

This connector is significantly more complex than file-based storage:

| Aspect | File Storage (S3/GCS/Drive) | Adobe Lightroom |
|--------|----------------------------|-----------------|
| **Data Model** | Flat file hierarchy | Catalog → Albums → Assets with metadata |
| **File Access** | Direct URLs | Renditions via API (no direct file URL) |
| **Authentication** | Standard OAuth2 | Adobe IMS OAuth2 with partner registration |
| **Partner Status** | Public APIs | Requires Adobe partner approval |
| **Rate Limits** | Generally high | Strict per-application quotas |
| **File Identification** | Path/filename | UUID + import_source metadata |
| **Filename Access** | Native paths | Original filename in import_source.fileName |

### What This PRD Delivers

- **Lightroom Connector**: Access Adobe Lightroom Cloud catalogs via Partner API
- **Catalog/Album Navigation**: Browse and select albums for analysis
- **Asset Enumeration**: List photos with original filenames from import metadata
- **Rendition Access**: Download renditions for analysis (when needed)
- **OAuth2 Integration**: Adobe IMS authentication with token management

---

## Background

### Adobe Lightroom Architecture

Adobe Lightroom Cloud organizes user content in a hierarchical structure:

```
User Account
└── Catalog (one per user)
    ├── Albums (collections/projects)
    │   └── Assets (photos/videos)
    └── Assets (all photos, including unorganized)
```

**Key Concepts:**

| Concept | Description |
|---------|-------------|
| **Catalog** | Root container for all user content (one per account) |
| **Album** | Organizational container (subtype: `project` or `project_set`) |
| **Asset** | Individual photo or video with metadata |
| **Rendition** | Generated image at specific size (thumbnail, 640, 1280, 2048, fullsize) |
| **Import Source** | Original file metadata including filename and capture device |

### Lightroom Partner API

The Lightroom API is a **partner-only API** requiring:

1. **Partner Application Registration**: Through Adobe Developer Console
2. **API Key**: Unique client identifier (`X-API-Key` header)
3. **OAuth2 Access Token**: User authorization via Adobe IMS
4. **Partner Scopes**: `lr_partner_apis`, `lr_partner_rendition_apis`

**Base URL**: `https://lr.adobe.io`

**API Version**: v2 (current)

### Problem Statement

Professional photographers face challenges analyzing Lightroom libraries:

1. **Export Required**: Current analysis requires exporting photos from Lightroom
2. **Metadata Loss**: Export loses Lightroom-specific metadata (develop settings, collections)
3. **Storage Duplication**: Must maintain local copies alongside cloud originals
4. **Workflow Disruption**: Export/re-import cycle interrupts professional workflow
5. **Album Structure**: Cannot analyze photos within album organization context

### User Pain Points

- "I have 50,000 photos in Lightroom but can't analyze my naming conventions without exporting"
- "My PhotoStats analysis doesn't reflect my album organization"
- "I want to validate my processing pipeline against Lightroom albums, not exports"

---

## Goals

### Primary Goals

1. **Lightroom Integration**: Connect to Adobe Lightroom Cloud via Partner API
2. **Catalog Access**: Enumerate all assets in user's Lightroom catalog
3. **Album Navigation**: Browse and select specific albums for analysis
4. **Filename Extraction**: Access original filenames from import_source metadata
5. **OAuth2 Authentication**: Implement Adobe IMS authorization flow

### Secondary Goals

1. **Metadata Access**: Extract ratings, keywords, capture dates from assets
2. **Album Hierarchy**: Support album sets (nested album structure)
3. **Rendition Download**: Download specific renditions when file analysis required

### Non-Goals (v1)

1. **Write Operations**: No upload, edit, or delete capabilities
2. **Develop Settings**: No access to RAW processing parameters
3. **Smart Collections**: No support for Lightroom's dynamic collections
4. **Lightroom Classic**: Desktop-only Lightroom Classic catalogs not supported
5. **Real-Time Sync**: No continuous monitoring for changes

---

## User Personas

### Primary: Professional Photographer (Morgan)
- **Tools**: Adobe Lightroom Classic + Cloud sync, photo-admin for validation
- **Collection**: 200,000+ images across 500 albums in Lightroom
- **Current Pain**: Must export albums to analyze naming conventions
- **Desired Outcome**: Run PhotoStats directly on Lightroom albums
- **This PRD Delivers**: Lightroom connector with album selection

### Secondary: Event Photographer (Casey)
- **Tools**: Lightroom CC (cloud-native), needs batch analysis
- **Collection**: 50,000 images, organized by event albums
- **Current Pain**: Cannot analyze camera usage patterns across events
- **Desired Outcome**: Photo Pairing analysis on Lightroom event albums
- **This PRD Delivers**: Camera ID and filename analysis from Lightroom metadata

### Tertiary: Photo Studio Manager (Alex)
- **Tools**: Lightroom for multiple photographers, QA analysis
- **Collection**: Team library with strict naming conventions
- **Current Pain**: No way to validate naming standards across team uploads
- **Desired Outcome**: Pipeline validation on Lightroom ingest albums
- **This PRD Delivers**: Filename validation using import_source.fileName

---

## User Stories

### User Story 1: Connect Adobe Lightroom Account (Priority: P1) 🎯 MVP

**As** a photographer with photos in Adobe Lightroom Cloud
**I want to** connect my Lightroom account to photo-admin
**So that** I can analyze my cloud photo library without exporting

**Acceptance Criteria:**
- Click "Add Connector" and select "Adobe Lightroom"
- Browser opens Adobe sign-in page
- After authorization, connector appears in connector list
- Connector shows Adobe ID email and storage quota
- Connection test succeeds and shows catalog information

**Independent Test:** Connect Lightroom, verify catalog ID and asset count displayed

---

### User Story 2: Browse and Select Lightroom Albums (Priority: P1) 🎯 MVP

**As** a photographer with organized Lightroom albums
**I want to** create a collection from a specific Lightroom album
**So that** I can analyze a subset of my library (not all 200,000 photos)

**Acceptance Criteria:**
- When creating collection from Lightroom connector, show album picker
- Album picker displays hierarchical album structure (album sets)
- Show asset count per album
- Selected album stored with collection configuration
- Tool execution scopes to selected album assets only

**Independent Test:** Create collection from album with 500 photos, verify PhotoStats analyzes exactly 500 files

---

### User Story 3: Analyze Original Filenames (Priority: P1) 🎯 MVP

**As** a photographer with naming conventions
**I want to** analyze original filenames from Lightroom imports
**So that** I can validate my file naming standards

**Acceptance Criteria:**
- PhotoStats/Photo Pairing access original filename via `import_source.fileName`
- Filenames displayed match original camera/export names
- Analysis treats Lightroom as filename source (not asset UUIDs)
- Support both image and video assets

**Independent Test:** Import "AB3D0001.dng" to Lightroom, analyze via photo-admin, verify "AB3D0001.dng" appears in results

---

### User Story 4: Handle Token Expiration (Priority: P1)

**As** a user with a connected Lightroom account
**I want to** be notified when my authorization expires
**So that** I can re-authorize without losing my connector settings

**Acceptance Criteria:**
- When access token expires and refresh fails, connector shows "Re-authorization required"
- User can click "Re-authorize" to repeat Adobe sign-in
- Existing connector settings preserved after re-auth
- Collections using connector remain intact (paused state)

**Independent Test:** Revoke Adobe authorization, attempt tool execution, verify re-auth flow

---

### User Story 5: View Album Metadata in Analysis (Priority: P2)

**As** a photographer analyzing my library
**I want to** see Lightroom album context in analysis results
**So that** I can understand organization alongside file analysis

**Acceptance Criteria:**
- Analysis results include album name when collection is album-scoped
- Optional: Include ratings, keywords in enhanced analysis mode
- Optional: Group results by album when analyzing multiple albums

**Independent Test:** Analyze album "Wedding 2025", verify album name appears in report header

---

## Requirements

### Functional Requirements

#### Core Connector Support

- **FR-001**: Add `LIGHTROOM` value to `ConnectorType` enum
- **FR-002**: Implement `LightroomAdapter` extending `StorageAdapter` base class
- **FR-003**: `LightroomAdapter.list_files(location)` MUST return list of original filenames
- **FR-004**: `LightroomAdapter.test_connection()` MUST verify catalog access and return account info
- **FR-005**: Location parameter format: `catalog:{catalog_id}` or `album:{album_id}`
- **FR-006**: Adapter MUST follow existing retry pattern (3 attempts with exponential backoff)

#### Adobe IMS OAuth2 Authentication

- **FR-010**: Implement OAuth2 authorization code flow with Adobe IMS
- **FR-011**: Request scopes: `openid`, `AdobeID`, `lr_partner_apis`, `lr_partner_rendition_apis`
- **FR-012**: Store encrypted OAuth tokens (access_token, refresh_token, expiry) in connector credentials
- **FR-013**: Implement automatic token refresh using refresh_token before expiration
- **FR-014**: Handle token revocation with clear user feedback
- **FR-015**: Provide `/api/connectors/oauth/lightroom/authorize` endpoint
- **FR-016**: Provide `/api/connectors/oauth/lightroom/callback` endpoint

#### Lightroom API Integration

- **FR-020**: Use base URL `https://lr.adobe.io` for all API calls
- **FR-021**: Include `X-API-Key` header with registered API key in all requests
- **FR-022**: Include `Authorization: Bearer {token}` header in all authenticated requests
- **FR-023**: Implement `GET /v2/catalog` to retrieve user catalog ID
- **FR-024**: Implement `GET /v2/catalogs/{catalog_id}/assets` for full catalog listing
- **FR-025**: Implement `GET /v2/catalogs/{catalog_id}/albums` for album enumeration
- **FR-026**: Implement `GET /v2/catalogs/{catalog_id}/albums/{album_id}/assets` for album asset listing
- **FR-027**: Handle API pagination using `links.next` cursor
- **FR-028**: Extract original filename from `payload.importSource.fileName` field

#### Credential Schema

- **FR-030**: Create `LightroomCredentials` Pydantic schema for OAuth token storage
- **FR-031**: Schema MUST include: access_token, refresh_token, expires_at, catalog_id, account_email
- **FR-032**: Token refresh MUST update stored credentials atomically

#### Album Browser

- **FR-040**: Implement `/api/lightroom/{connector_guid}/albums` endpoint listing all albums
- **FR-041**: Album list MUST include: album_id, name, asset_count, parent_album_id
- **FR-042**: Support album hierarchy display (album sets containing albums)
- **FR-043**: Frontend album picker MUST display hierarchical structure

#### Collection Integration

- **FR-050**: Add `LIGHTROOM` to `CollectionType` enum
- **FR-051**: Collection `path` field stores album ID for album-scoped collections
- **FR-052**: Collection without album ID analyzes entire catalog
- **FR-053**: Collection detail view shows album name and asset count

### Non-Functional Requirements

#### Security

- **NFR-001**: Adobe API key MUST be stored in environment variable `LIGHTROOM_API_KEY`
- **NFR-002**: Adobe client secret MUST be stored in environment variable `LIGHTROOM_CLIENT_SECRET`
- **NFR-003**: All tokens MUST be encrypted at rest using Fernet encryption
- **NFR-004**: OAuth state parameter MUST be validated to prevent CSRF attacks
- **NFR-005**: Audit logging for all Lightroom API operations

#### Performance

- **NFR-010**: Catalog listing MUST support pagination (handle 100,000+ assets)
- **NFR-011**: Initial album enumeration MUST complete within 30 seconds
- **NFR-012**: Asset listing MUST process at minimum 1,000 assets per second
- **NFR-013**: Token refresh MUST complete within 5 seconds

#### Reliability

- **NFR-020**: API calls MUST retry on 429 (rate limit) and 5xx errors
- **NFR-021**: Token refresh MUST retry 3 times before failing
- **NFR-022**: Failed token refresh MUST NOT delete connector (mark as needs re-auth)
- **NFR-023**: Connector status MUST reflect actual authorization state

#### Adobe Partner Compliance

- **NFR-030**: Application MUST comply with Adobe Partner API terms of service
- **NFR-031**: User consent screen MUST clearly describe data access
- **NFR-032**: Application MUST handle API deprecation notices gracefully

#### Testing

- **NFR-040**: Backend test coverage MUST exceed 80% for adapter code
- **NFR-041**: OAuth flow MUST have integration tests with mocked Adobe responses
- **NFR-042**: Pagination handling MUST have dedicated unit tests
- **NFR-043**: Rate limit handling MUST have dedicated unit tests

---

## Technical Approach

### Architecture Extension

```
┌────────────────────────────────────────────────────────────────────┐
│                    StorageAdapter (Abstract Base)                   │
│  - list_files(location) → List[str]                                │
│  - test_connection() → Tuple[bool, str]                            │
└─────────────────────────────────────┬──────────────────────────────┘
                                      │
        ┌───────────────┬─────────────┼─────────────┬───────────────┐
        │               │             │             │               │
        ▼               ▼             ▼             ▼               ▼
┌───────────┐   ┌───────────┐  ┌───────────┐  ┌────────────┐  ┌────────────┐
│ S3Adapter │   │GCSAdapter │  │SMBAdapter │  │GoogleDrive │  │OneDrive    │
│           │   │           │  │           │  │Adapter     │  │Adapter     │
└───────────┘   └───────────┘  └───────────┘  └────────────┘  └────────────┘
                                      │
                                      ▼
                            ┌─────────────────────┐
                            │  LightroomAdapter   │
                            │  (NEW - Complex)    │
                            │                     │
                            │  Features:          │
                            │  - Catalog access   │
                            │  - Album browsing   │
                            │  - Asset metadata   │
                            │  - Filename extract │
                            └─────────────────────┘
```

### Lightroom Data Flow

```
┌──────────────────┐     ┌─────────────────┐     ┌────────────────────┐
│  photo-admin     │     │  Adobe IMS      │     │  Lightroom API     │
│  (Connector)     │     │  (Auth Server)  │     │  (lr.adobe.io)     │
└────────┬─────────┘     └────────┬────────┘     └──────────┬─────────┘
         │                        │                         │
         │  1. OAuth Authorize    │                         │
         │───────────────────────►│                         │
         │                        │                         │
         │  2. User signs in      │                         │
         │◄───────────────────────│                         │
         │                        │                         │
         │  3. Exchange code      │                         │
         │───────────────────────►│                         │
         │                        │                         │
         │  4. Access + Refresh   │                         │
         │◄───────────────────────│                         │
         │                        │                         │
         │  5. GET /v2/catalog                              │
         │─────────────────────────────────────────────────►│
         │                                                  │
         │  6. Catalog metadata                             │
         │◄─────────────────────────────────────────────────│
         │                                                  │
         │  7. GET /v2/catalogs/{id}/albums                 │
         │─────────────────────────────────────────────────►│
         │                                                  │
         │  8. Album list (paginated)                       │
         │◄─────────────────────────────────────────────────│
         │                                                  │
         │  9. GET /v2/catalogs/{id}/albums/{id}/assets     │
         │─────────────────────────────────────────────────►│
         │                                                  │
         │  10. Asset list with import_source               │
         │◄─────────────────────────────────────────────────│
         │                                                  │
         │  11. Extract payload.importSource.fileName       │
         │  12. Return as file list to photo-admin tools    │
```

### Recommended Python Libraries

Since there is no official Adobe Python SDK for Lightroom, implementation options:

| Option | Library | Justification |
|--------|---------|---------------|
| **Recommended** | `httpx` (async) or `requests` | Direct REST API calls with full control |
| **OAuth Helper** | `authlib` | Robust OAuth2 client implementation |
| **Alternative** | `lightroom-cc-api` | Community library (limited maintenance, v0.0.2) |

**Recommendation:** Implement custom adapter using `httpx` + `authlib` for:
- Full control over API interaction
- Better error handling and retry logic
- Consistency with photo-admin patterns
- No dependency on minimally-maintained community library

**Installation:**
```bash
pip install httpx authlib
```

### API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /v2/health` | API health check |
| `GET /v2/account` | User account info (email, storage) |
| `GET /v2/catalog` | Catalog metadata (catalog_id) |
| `GET /v2/catalogs/{catalog_id}/albums` | List all albums |
| `GET /v2/catalogs/{catalog_id}/albums/{album_id}` | Single album details |
| `GET /v2/catalogs/{catalog_id}/albums/{album_id}/assets` | Album assets |
| `GET /v2/catalogs/{catalog_id}/assets` | All catalog assets |
| `GET /v2/catalogs/{catalog_id}/assets/{asset_id}` | Single asset details |

### Credential Schema

```python
class LightroomCredentials(BaseModel):
    """Adobe Lightroom OAuth2 credentials."""

    # OAuth tokens
    access_token: str = Field(..., min_length=20)
    refresh_token: str = Field(..., min_length=20)
    expires_at: int = Field(...)  # Unix timestamp
    token_type: str = Field(default="Bearer")

    # Lightroom-specific
    catalog_id: str = Field(..., description="User's Lightroom catalog UUID")

    # Account info (for display)
    account_email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    account_name: Optional[str] = Field(default=None)

    # Entitlement info
    storage_used: Optional[int] = Field(default=None)  # bytes
    storage_limit: Optional[int] = Field(default=None)  # bytes

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1Q...",
                "refresh_token": "eyJ0eXAiOiJKV1Q...",
                "expires_at": 1705159800,
                "catalog_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "account_email": "photographer@adobe.com",
                "storage_used": 107374182400,
                "storage_limit": 1099511627776
            }
        }
    }
```

### Asset Filename Extraction

Original filenames are stored in the asset's `payload.importSource` object:

```json
{
  "id": "asset-uuid-here",
  "type": "asset",
  "subtype": "image",
  "payload": {
    "captureDate": "2025-12-15T14:30:00Z",
    "importSource": {
      "fileName": "AB3D0001-HDR.dng",
      "importedOnDevice": "Canon EOS R5",
      "importTimestamp": "2025-12-15T18:45:00Z"
    }
  }
}
```

The adapter extracts `payload.importSource.fileName` to provide familiar filenames to photo-admin analysis tools.

### Environment Variables

```bash
# Adobe Developer Console credentials
LIGHTROOM_API_KEY=your-api-key-from-console
LIGHTROOM_CLIENT_SECRET=your-client-secret

# OAuth configuration
LIGHTROOM_REDIRECT_URI=http://localhost:8000/api/connectors/oauth/lightroom/callback

# Optional: Custom IMS endpoint (for testing)
ADOBE_IMS_ENDPOINT=https://ims-na1.adobelogin.com
```

### New Files

```
backend/src/
├── services/
│   ├── oauth/
│   │   └── adobe_oauth.py       # Adobe IMS OAuth2 flow handler
│   ├── remote/
│   │   └── lightroom_adapter.py # LightroomAdapter implementation
│   └── lightroom_service.py     # Lightroom-specific business logic
├── api/
│   └── lightroom.py             # Lightroom-specific endpoints (albums, etc.)
└── schemas/
    └── lightroom.py             # Lightroom-specific Pydantic schemas
```

### New API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/connectors/oauth/lightroom/authorize` | GET | Generate Adobe OAuth authorization URL |
| `/api/connectors/oauth/lightroom/callback` | GET | Handle Adobe OAuth callback |
| `/api/lightroom/{connector_guid}/catalog` | GET | Get catalog info for connector |
| `/api/lightroom/{connector_guid}/albums` | GET | List albums with hierarchy |
| `/api/lightroom/{connector_guid}/albums/{album_id}` | GET | Get album details with asset count |

---

## Implementation Plan

### Phase 1: Adobe OAuth & Basic Connectivity (Priority: P1) 🎯 MVP

**Estimated Tasks: ~35**

**Backend (20 tasks):**
1. Add `LIGHTROOM` to `ConnectorType` and `CollectionType` enums
2. Create `LightroomCredentials` Pydantic schema
3. Implement `AdobeOAuthService` with IMS integration
4. Implement OAuth authorization URL generation with partner scopes
5. Implement OAuth callback handling with token exchange
6. Implement token refresh using refresh_token
7. Create `LightroomAdapter` extending `StorageAdapter`
8. Implement `test_connection()` using `/v2/health` and `/v2/account`
9. Store catalog_id during OAuth callback (from `/v2/catalog`)
10. Add retry logic matching existing adapter patterns
11. Integrate with `ConnectorService` for adapter selection
12. Add OAuth endpoints to API router
13. Comprehensive unit tests

**Frontend (10 tasks):**
1. Add "Adobe Lightroom" to connector type selector
2. Implement OAuth redirect flow to Adobe sign-in
3. Handle OAuth callback success/failure
4. Display connected Adobe account info and storage quota
5. Add "Re-authorize" button for expired tokens
6. Component tests

**Testing (5 tasks):**
1. Mock Adobe IMS token exchange
2. Mock Lightroom API health/account responses
3. Test token refresh scenarios
4. Integration test: OAuth → Connector created

**Checkpoint:** Users can connect Adobe Lightroom and see account info. Basic connection verification works.

---

### Phase 2: Album Browsing & Asset Listing (Priority: P1) 🎯 MVP

**Estimated Tasks: ~40**

**Backend (25 tasks):**
1. Implement `GET /v2/catalogs/{catalog_id}/albums` with pagination
2. Implement album hierarchy parsing (album_sets contain albums)
3. Implement `GET /v2/catalogs/{catalog_id}/albums/{album_id}/assets` with pagination
4. Extract original filenames from `payload.importSource.fileName`
5. Implement `LightroomAdapter.list_files(location)` method
6. Support location formats: `catalog:{id}` and `album:{id}`
7. Handle missing `importSource` gracefully (use asset ID as fallback)
8. Implement `/api/lightroom/{guid}/albums` endpoint
9. Implement `/api/lightroom/{guid}/albums/{album_id}` endpoint
10. Add caching for album structure (5-minute TTL)
11. Handle Lightroom API rate limiting (429 responses)
12. Comprehensive unit tests
13. Integration tests with mocked Lightroom API

**Frontend (12 tasks):**
1. Create album picker component with tree structure
2. Show asset count per album
3. Support album set expansion (nested albums)
4. Integrate album picker with collection creation form
5. Display selected album path in collection details
6. Component tests

**Testing (3 tasks):**
1. Test pagination handling for large catalogs
2. Test album hierarchy parsing
3. E2E test: Connect → Select Album → Create Collection

**Checkpoint:** Users can browse Lightroom albums and create collections scoped to specific albums.

---

### Phase 3: Tool Execution Integration (Priority: P1)

**Estimated Tasks: ~30**

**Backend (18 tasks):**
1. Ensure `LightroomAdapter.list_files()` returns proper filename list
2. Handle video assets (use video filename from importSource)
3. Handle assets without importSource (cloud-native edits)
4. Implement batch asset fetching for performance (100 assets per request)
5. Add progress reporting hooks for long listings
6. Integrate with PhotoStats tool execution
7. Integrate with Photo Pairing tool execution
8. Integrate with Pipeline Validation tool execution
9. Unit tests for tool integration

**Frontend (8 tasks):**
1. Show "Lightroom Album" indicator in collection list
2. Display album name in collection details
3. Show Lightroom-specific collection stats
4. Progress indicator during large album listing

**Testing (4 tasks):**
1. E2E test: PhotoStats on Lightroom album
2. E2E test: Photo Pairing on Lightroom album
3. Test with large album (10,000+ assets)
4. Test with empty album

**Checkpoint:** All three analysis tools work with Lightroom collections.

---

### Phase 4: Enhanced Metadata Access (Priority: P2)

**Estimated Tasks: ~25**

**Backend (15 tasks):**
1. Extract asset ratings from metadata
2. Extract keywords from asset metadata
3. Extract capture date for temporal analysis
4. Optional: Include camera/device info from importSource.importedOnDevice
5. Create enhanced metadata schema for Lightroom assets
6. Add metadata export capability to analysis results
7. Unit tests

**Frontend (7 tasks):**
1. Optional metadata display in collection details
2. Filter assets by rating (if exposed)
3. Show capture date range for collections

**Testing (3 tasks):**
1. Test metadata extraction accuracy
2. Test with assets lacking metadata
3. Performance test with full metadata extraction

**Checkpoint:** Enhanced analysis with Lightroom metadata available.

---

### Phase 5: Rendition Access (Priority: P3)

**Estimated Tasks: ~20**

**Backend (12 tasks):**
1. Implement rendition URL generation
2. Support rendition types: thumbnail2x, 640, 1280, 2048, fullsize
3. Cache rendition URLs (short TTL due to signed URLs)
4. Implement rendition download for file-based analysis (if needed)
5. Handle rendition generation async (for on-demand renditions)

**Frontend (5 tasks):**
1. Thumbnail display in asset browser (if implemented)
2. Rendition size selector

**Testing (3 tasks):**
1. Test rendition URL generation
2. Test async rendition handling

**Checkpoint:** Full rendition access for advanced use cases.

---

## Risks and Mitigation

### Risk 1: Adobe Partner Approval Required (HIGH)
- **Impact**: Critical - Cannot proceed without partner status
- **Probability**: Medium (requires business relationship)
- **Mitigation**:
  - Apply for partner status early in planning phase
  - Prepare demo application for Adobe review
  - Have fallback plan (document as "coming soon" feature)
  - Explore Adobe Firefly Services as alternative entry point

### Risk 2: Rate Limiting on Large Catalogs
- **Impact**: High - Users with 100,000+ photos may experience slow listing
- **Probability**: High (professional photographers have large libraries)
- **Mitigation**:
  - Implement aggressive caching (album structure, asset counts)
  - Paginate all requests with reasonable page sizes
  - Show progress indicators during long operations
  - Offer album-scoped analysis to reduce data volume

### Risk 3: API Changes Without Notice
- **Impact**: Medium - Adapter breakage
- **Probability**: Medium (API is partner-facing, not public)
- **Mitigation**:
  - Monitor Adobe developer blog and changelog
  - Version-pin expectations in tests
  - Implement graceful degradation for missing fields

### Risk 4: Token Expiration During Long Operations
- **Impact**: Medium - Analysis fails mid-execution
- **Probability**: Medium (tokens expire in ~1 hour)
- **Mitigation**:
  - Proactive token refresh before expiration (5-minute buffer)
  - Refresh token during long-running operations
  - Clear error messages if refresh fails

### Risk 5: Missing Import Source Data
- **Impact**: Low - Some assets lack original filename
- **Probability**: Medium (cloud-native edits, old imports)
- **Mitigation**:
  - Graceful fallback to asset ID when fileName missing
  - Document limitation for users
  - Log warnings for analysis reports

---

## Security Considerations

### Adobe Partner API Compliance

1. **API Key Protection**: Store in environment variable, never in code
2. **User Consent**: Clear description of data access in OAuth consent
3. **Minimal Scopes**: Only request `lr_partner_apis` and `lr_partner_rendition_apis`
4. **Token Storage**: All tokens encrypted with Fernet before database storage
5. **No Write Operations**: Read-only access reduces risk surface

### OAuth Security

1. **State Parameter**: Cryptographically random state token, validated on callback
2. **PKCE**: Use PKCE (Proof Key for Code Exchange) if supported by Adobe IMS
3. **Secure Redirect**: Validate redirect URI against whitelist
4. **Token Refresh**: Proactive refresh before expiry
5. **Audit Logging**: Log all OAuth operations with timestamps

### Adobe Developer Console Setup

1. Create project in Adobe Developer Console
2. Add Lightroom Services API
3. Configure OAuth Web credentials
4. Set redirect URI to callback endpoint
5. Note: Requires approved partner account with `lr_partner_apis` scope

---

## Open Questions

1. **Partner Approval Timeline**: How long does Adobe partner approval take?
2. **Rate Limit Specifics**: What are exact rate limits for partner applications?
3. **Shared Catalogs**: Can we access shared/team catalogs (Adobe Creative Cloud for Teams)?
4. **Lightroom Classic**: Any path to support desktop-only Lightroom Classic catalogs?
5. **Album Type Filtering**: Should we filter to show only user-created albums (not system albums)?
6. **Asset Type Filtering**: Should we allow filtering to images-only, excluding videos?
7. **Develop Settings**: Is there demand for accessing RAW develop parameters?

---

## Success Metrics

### Adoption Metrics
- **M1**: 30% of professional users connect Lightroom within 3 months
- **M2**: 80% of Lightroom OAuth flows complete successfully
- **M3**: Average album selection takes <30 seconds

### Performance Metrics
- **M4**: OAuth flow completes within 30 seconds
- **M5**: Album enumeration completes within 30 seconds
- **M6**: 10,000 asset listing completes within 60 seconds
- **M7**: Token refresh completes within 5 seconds

### Reliability Metrics
- **M8**: 99% of token refreshes succeed without user intervention
- **M9**: Zero OAuth token leaks in logs
- **M10**: <2% of tool executions fail due to Lightroom API issues

---

## Dependencies

### External Dependencies

- **Adobe Partner Account**: Required for `lr_partner_apis` scope
- **Adobe Developer Console**: For API key and OAuth configuration
- **Adobe IMS**: Identity management for OAuth2 flow
- **Lightroom Partner API**: `https://lr.adobe.io` availability

### Internal Dependencies

- ✅ Connector architecture (StorageAdapter, ConnectorType, encrypted credentials)
- ✅ Fernet encryption infrastructure
- ✅ GUID-based external identification
- ✅ Frontend connector management UI
- ✅ OAuth patterns (from 013-cloud-drive-connectors if implemented first)

### New Dependencies (requirements.txt)

```
# HTTP client with async support
httpx>=0.25.0

# OAuth2 client library
authlib>=1.2.0
```

---

## Appendix

### A. Adobe Lightroom API Reference

**Base URL:** `https://lr.adobe.io`

**Required Headers:**
```
X-API-Key: {api_key}
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Key Endpoints:**

| Endpoint | Description |
|----------|-------------|
| `GET /v2/health` | API health check |
| `GET /v2/account` | User account and entitlement |
| `GET /v2/catalog` | User catalog metadata |
| `GET /v2/catalogs/{id}/albums` | List albums |
| `GET /v2/catalogs/{id}/albums/{id}/assets` | Album assets |
| `GET /v2/catalogs/{id}/assets` | All catalog assets |

### B. Sample Asset Response

```json
{
  "base": "https://lr.adobe.io/",
  "resources": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "type": "asset",
      "subtype": "image",
      "created": "2025-12-15T18:45:00Z",
      "updated": "2025-12-16T10:30:00Z",
      "payload": {
        "captureDate": "2025-12-15T14:30:00Z",
        "importSource": {
          "fileName": "AB3D0001-HDR.dng",
          "importedOnDevice": "Canon EOS R5",
          "importTimestamp": "2025-12-15T18:45:00Z",
          "originalWidth": 8192,
          "originalHeight": 5464
        },
        "develop": {
          "userUpdated": "2025-12-16T10:30:00Z"
        }
      },
      "links": {
        "self": {"href": "catalogs/{catalog_id}/assets/{asset_id}"},
        "/rels/rendition_type/thumbnail2x": {"href": "..."},
        "/rels/rendition_type/2048": {"href": "..."}
      }
    }
  ],
  "links": {
    "next": {"href": "catalogs/{catalog_id}/assets?cursor=..."}
  }
}
```

### C. Sample Album Response

```json
{
  "base": "https://lr.adobe.io/",
  "resources": [
    {
      "id": "album-uuid-here",
      "type": "album",
      "subtype": "project",
      "created": "2025-12-01T10:00:00Z",
      "updated": "2025-12-15T18:45:00Z",
      "payload": {
        "name": "Wedding 2025",
        "cover": {
          "id": "asset-uuid-for-cover"
        },
        "parent": {
          "id": "parent-album-set-uuid"
        }
      },
      "links": {
        "self": {"href": "catalogs/{catalog_id}/albums/{album_id}"},
        "/rels/assets": {"href": "catalogs/{catalog_id}/albums/{album_id}/assets"}
      }
    }
  ]
}
```

### D. OAuth2 Scopes Reference

| Scope | Purpose |
|-------|---------|
| `openid` | OpenID Connect standard scope |
| `AdobeID` | Adobe identity verification |
| `lr_partner_apis` | Lightroom Partner API access |
| `lr_partner_rendition_apis` | Rendition download access |

### E. Error Response Format

```json
{
  "code": "error_code_here",
  "description": "Human-readable error message",
  "errors": {
    "field_name": ["Validation error details"]
  }
}
```

### F. Comparison: Lightroom vs File Storage Adapters

| Capability | S3/GCS/OneDrive | Lightroom |
|------------|-----------------|-----------|
| List files by path | ✅ Native | ⚠️ Via album ID |
| Direct file URL | ✅ Native | ❌ Rendition API |
| Original filename | ✅ Path-based | ✅ importSource.fileName |
| Folder hierarchy | ✅ Native | ✅ Album hierarchy |
| File streaming | ✅ Native | ❌ Rendition download |
| Metadata access | ❌ Limited | ✅ Rich (ratings, keywords) |
| Authentication | OAuth2/Keys | OAuth2 (partner) |

---

## Revision History

- **2026-01-13 (v1.0)**: Initial draft
  - Defined Adobe Lightroom connector requirements
  - Analyzed Lightroom Partner API capabilities
  - Designed adapter for catalog/album/asset access
  - Recommended httpx + authlib for implementation
  - Created 5-phase implementation plan (~150 tasks)
  - Documented Adobe partner approval as prerequisite
  - Noted complexity differences from file-based storage

---

## References

- [Adobe Lightroom API Documentation](https://developer.adobe.com/lightroom/lightroom-api-docs/)
- [Lightroom API Reference](https://developer.adobe.com/lightroom/lightroom-api-docs/api/)
- [Adobe Firefly Services - Lightroom](https://developer.adobe.com/firefly-services/docs/lightroom/)
- [Authenticating Customers](https://developer.adobe.com/lightroom/lightroom-api-docs/getting-started/authenticate_customers/)
- [GitHub - AdobeDocs/lightroom-public-apis](https://github.com/AdobeDocs/lightroom-public-apis)
- [Community Python Library (lightroom-cc-api)](https://github.com/lou-k/lightroom-cc-api)
