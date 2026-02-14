# ShutterSense Security Audit Report

**Date:** 2026-02-14
**Scope:** Full codebase (backend, frontend, agent)
**Methodology:** Manual code review against OWASP Top 10 and multi-tenant security best practices

---

## Executive Summary

ShutterSense implements a solid security foundation with OAuth 2.0 + PKCE, Fernet encryption for credentials, tenant isolation, and comprehensive security headers. However, the audit identified **14 security issues** ranging from critical cross-tenant access control bypasses to medium-severity configuration gaps.

| Severity | Count | Summary |
|----------|-------|---------|
| Critical | 2 | Cross-tenant IDOR, unauthenticated WebSockets |
| High | 3 | Session fixation, missing agent auth rate limiting, error detail leakage |
| Medium | 5 | Missing HSTS, in-memory rate limiting bypass, insecure session defaults, deprecated datetime API, internal ID in session |
| Low | 4 | CSP unsafe-inline, default CORS localhost, empty secret key defaults, API token scope granularity |

---

## Critical Findings

### C1. Cross-Tenant IDOR via GUID Resolution Without team_id Filtering

**Severity:** CRITICAL
**OWASP:** A01:2021 - Broken Access Control
**Affected Files:**
- `backend/src/api/collections.py` (lines 270-277, 285-292, 296-308, 494-505, 510-522, 1090-1094, 1322-1334)
- `backend/src/api/tools.py` (lines 165, 175-192)

**Description:**
When creating or updating collections, the API resolves related entity GUIDs (Connector, Pipeline, Agent) to internal IDs using direct database queries **without filtering by `team_id`**. This allows an authenticated user from Team A to reference resources belonging to Team B.

**Vulnerable Pattern (collections.py:270-277):**
```python
connector = db.query(Connector).filter(
    Connector.uuid == connector_uuid
).first()  # No team_id filter!
connector_id = connector.id
```

**Impact:**
- A user can create a collection bound to another team's connector, potentially accessing their cloud storage credentials
- A user can bind their collection to another team's agent, executing jobs on their infrastructure
- A user can assign another team's pipeline to their collections

**Specific Vulnerable Endpoints:**
1. `POST /api/collections` - Connector, Pipeline, and Agent GUIDs resolved without team_id
2. `PUT /api/collections/{guid}` - Pipeline and Agent GUIDs resolved without team_id
3. `POST /api/collections/{guid}/assign-pipeline` - Pipeline GUID resolved without team_id
4. `POST /api/collections/from-inventory` - Pipeline GUID resolved without team_id
5. `POST /api/tools/run` - Collection GUID resolved without team_id (line 165: `collection_service.get_by_guid(tool_request.collection_guid)` -- missing `team_id=ctx.team_id`)
6. `POST /api/tools/run` - Pipeline GUID resolved without team_id (line 186)

**Remediation:**
Add `team_id` filtering to all GUID resolution queries:
```python
connector = db.query(Connector).filter(
    Connector.uuid == connector_uuid,
    Connector.team_id == ctx.team_id
).first()
```

---

### C2. Unauthenticated WebSocket Endpoints

**Severity:** CRITICAL
**OWASP:** A01:2021 - Broken Access Control
**Affected File:** `backend/src/api/tools.py` (lines 600-730)

**Description:**
Two WebSocket endpoints accept connections without any authentication or authorization checks:

1. **`/ws/jobs/all`** (line 600) - Receives real-time updates for ALL jobs globally, regardless of team. No authentication check performed before `manager.connect()`.

2. **`/ws/jobs/{job_id}`** (line 661) - Receives real-time progress for any job by ID. No verification that the connecting user belongs to the job's team.

**Contrast:** The agent pool status WebSocket (`/ws/pool-status` in `agent/routes.py:1987`) correctly implements authentication using `get_websocket_tenant_context_standalone()`.

**Impact:**
- Any unauthenticated client can connect and receive job progress data for all teams
- Job data may contain collection names, tool types, file paths, and analysis results
- Information leakage across tenant boundaries

**Remediation:**
Add authentication to both WebSocket handlers following the pattern from `agent/routes.py`:
```python
ctx = await get_websocket_tenant_context_standalone(websocket)
if not ctx:
    await websocket.close(code=4001, reason="Authentication required")
    return
# Use ctx.team_id to scope job subscriptions
```

---

## High Findings

### H1. Session Fixation After OAuth Login

**Severity:** HIGH
**OWASP:** A07:2021 - Identification and Authentication Failures
**Affected File:** `backend/src/services/auth_service.py` (line 430)

**Description:**
After successful OAuth authentication, `create_session()` sets `request.session["user_id"]` without first clearing or regenerating the session. Starlette's `SessionMiddleware` does not automatically regenerate session IDs on privilege escalation.

```python
def create_session(self, request: Request, user: User) -> None:
    request.session["user_id"] = user.id       # Sets on existing session
    request.session["user_guid"] = user.guid    # No session regeneration
```

**Impact:**
If an attacker can set a session cookie before the victim logs in (e.g., via a subdomain or XSS on a related domain), the attacker's session ID persists post-login and gains the victim's authenticated session.

**Remediation:**
Clear the session before populating it with authenticated user data:
```python
def create_session(self, request: Request, user: User) -> None:
    request.session.clear()  # Regenerate session
    request.session["user_id"] = user.id
    request.session["user_guid"] = user.guid
```

---

### H2. No Rate Limiting on Agent Authentication

**Severity:** HIGH
**OWASP:** A07:2021 - Identification and Authentication Failures
**Affected File:** `backend/src/api/agent/dependencies.py` (lines 60-157)

**Description:**
The agent authentication endpoint (`get_agent_context`) has no rate limiting for failed API key validation attempts. In contrast, user API token authentication in `backend/src/middleware/tenant.py` (lines 32-95) implements per-IP failure tracking with blocking after 20 failures.

Agent API keys use the format `agt_key_xxxxx` with SHA-256 hash comparison. Without rate limiting, the endpoint is vulnerable to brute-force attacks against agent API keys.

**Impact:**
An attacker can make unlimited authentication attempts against the agent API without being blocked.

**Remediation:**
Apply the same `_record_token_failure` / `_is_token_blocked` pattern from `tenant.py` to agent authentication.

---

### H3. Internal Error Details Leaked in API Responses

**Severity:** HIGH
**OWASP:** A04:2021 - Insecure Design
**Affected Files:** All 18 files in `backend/src/api/`

**Description:**
Across the API layer, **~200 instances** of exception details are included directly in HTTP error responses:

```python
except Exception as e:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to create connector: {str(e)}"  # Leaks internal details
    )
```

While `main.py`'s global exception handlers correctly return generic messages, these route-level handlers execute first and expose internal details.

**Examples of potential information leakage:**
- Database connection strings, table/column names, SQL errors
- File system paths and permission errors
- Cloud provider SDK errors (potentially revealing configuration)
- Pydantic validation internals

**Impact:**
Attackers can use error messages to map internal architecture, discover database schema, and identify technology stack details useful for further attacks.

**Remediation:**
Replace all `str(e)` in HTTP responses with generic messages. Log the details server-side only:
```python
except Exception as e:
    logger.error(f"Error creating connector: {str(e)}", exc_info=True)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An internal error occurred. Please try again later."
    )
```

---

## Medium Findings

### M1. Missing HSTS (Strict-Transport-Security) Header

**Severity:** MEDIUM
**OWASP:** A05:2021 - Security Misconfiguration
**Affected File:** `backend/src/main.py` (SecurityHeadersMiddleware, lines 76-148)

**Description:**
The `SecurityHeadersMiddleware` adds X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, CSP, and Permissions-Policy headers but does **not** set `Strict-Transport-Security`. Without HSTS, browsers may accept HTTP connections, enabling protocol downgrade and MITM attacks.

**Remediation:**
Add HSTS header to `SecurityHeadersMiddleware` (only when running behind HTTPS):
```python
if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
```

---

### M2. In-Memory Rate Limiting Bypassed with Multiple Workers

**Severity:** MEDIUM
**OWASP:** A07:2021 - Identification and Authentication Failures
**Affected File:** `backend/src/middleware/tenant.py` (lines 43-44)

**Description:**
The per-IP token failure tracking uses in-process dictionaries (`_token_failures`, `_token_blocked`). In production with multiple uvicorn workers, each worker maintains separate counters. An attacker distributing requests across workers can bypass the 20-failure threshold.

**Current:**
```python
_token_failures: dict[str, list[float]] = defaultdict(list)  # Per-process
_token_blocked: dict[str, float] = {}                        # Per-process
```

**Additionally:** The `slowapi` rate limiter defaults to `memory://` storage, which has the same multi-worker bypass issue.

**Remediation:**
- Set `RATE_LIMIT_STORAGE_URI=redis://...` in production
- Document that multi-worker deployments require Redis for rate limiting to be effective

---

### M3. Session Cookie Defaults to HTTP (Not HTTPS-Only)

**Severity:** MEDIUM
**OWASP:** A02:2021 - Cryptographic Failures
**Affected File:** `backend/src/config/session.py` (line 53-55)

**Description:**
```python
session_https_only: bool = Field(
    default=False,  # Set to True in production
)
```

The session cookie defaults to being sent over both HTTP and HTTPS. While there is a startup warning in `main.py` when running in production mode with `SESSION_HTTPS_ONLY=false`, the default-insecure configuration could lead to session hijacking if operators miss the warning.

**Remediation:**
Consider defaulting to `True` and requiring explicit opt-out for development:
```python
session_https_only: bool = Field(default=True)
```

---

### M4. Internal Numeric ID Stored in Session

**Severity:** MEDIUM
**OWASP:** A04:2021 - Insecure Design
**Affected File:** `backend/src/services/auth_service.py` (line 430)

**Description:**
The session stores `user.id` (internal auto-increment integer) rather than the GUID:
```python
request.session["user_id"] = user.id  # Internal numeric ID
```

The session authentication in `tenant.py:324` then queries using this numeric ID:
```python
user = db.query(User).filter(User.id == user_id).first()
```

While the session cookie is signed (preventing tampering), storing sequential integer IDs makes ID prediction trivial if the signing key is compromised. The application's own architecture principle (Issue #42) states that external-facing identifiers should use GUIDs.

**Remediation:**
Store the GUID in the session and look up by GUID:
```python
request.session["user_guid"] = user.guid
# Then in tenant.py:
user = db.query(User).filter(User.guid == user_guid).first()
```

---

### M5. Deprecated `datetime.utcnow()` Usage

**Severity:** MEDIUM
**OWASP:** N/A (Reliability/Correctness)
**Affected Files:** ~90 occurrences across models and services

**Description:**
`datetime.utcnow()` is deprecated since Python 3.12 and returns naive (timezone-unaware) datetimes. This affects token expiry checks (e.g., `api_token.py` line 206, `agent_registration_token.py` lines 160, 184) and all model timestamps.

While the application targets Python 3.11+, mixing naive and timezone-aware datetimes can lead to token expiry being calculated incorrectly, especially when running across timezones or with timezone-aware database columns.

**Remediation:**
Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)`:
```python
from datetime import datetime, timezone
# Before: datetime.utcnow()
# After:  datetime.now(timezone.utc)
```

---

## Low Findings

### L1. CSP Allows `unsafe-inline` for Styles

**Severity:** LOW
**Affected File:** `backend/src/main.py` (line 130)

The SPA Content-Security-Policy includes `style-src 'self' 'unsafe-inline'`. This weakens CSP protection against style-based attacks. This is a known trade-off required by Tailwind CSS and many component libraries. Consider using nonces or hashes in the future.

### L2. Default CORS Origins Include Localhost

**Severity:** LOW
**Affected File:** `backend/src/main.py` (lines 741-746)

When `CORS_ORIGINS` is not set, the default includes `http://localhost:3000` and `http://localhost:8000`. These should be removed in production. The application relies on operators setting `CORS_ORIGINS` correctly.

### L3. Secret Keys Default to Empty String

**Severity:** LOW
**Affected Files:** `backend/src/config/settings.py` (line 36), `backend/src/config/session.py` (line 28)

Both `JWT_SECRET_KEY` and `SESSION_SECRET_KEY` default to empty string. While the application checks `is_configured` and logs warnings, it can still start without functional authentication. Consider failing fast on startup in production mode.

### L4. API Token Scopes Not Enforced

**Severity:** LOW
**Affected File:** `backend/src/services/token_service.py` (line 169)

API tokens are created with `scopes=["*"]` (full access) and no mechanism exists to restrict token permissions to specific operations. This violates the principle of least privilege.

---

## Positive Security Findings

The following areas are well-implemented:

1. **OAuth 2.0 with PKCE** - Properly configured with state/nonce validation
2. **Credential Encryption** - Fernet (AES-128-CBC + HMAC) with environment-based key management
3. **Tenant Isolation** - Service layer consistently filters by `team_id` (the IDOR issues are at the API layer)
4. **Security Headers** - Comprehensive CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
5. **Path Traversal Protection** - `is_path_authorized()` and `is_safe_static_file_path()` properly validate paths
6. **No SQL Injection** - Exclusive use of SQLAlchemy ORM with parameterized queries
7. **No Dangerous Functions** - No `eval()`, `exec()`, or `subprocess(shell=True)` patterns
8. **No Hardcoded Secrets** - All secrets loaded from environment variables
9. **Token Hash Storage** - API tokens and agent keys stored as SHA-256 hashes
10. **Super Admin via Hashed Emails** - No plaintext admin identifiers
11. **Frontend Security** - No `dangerouslySetInnerHTML`, proper XSS prevention, no client-side secret storage
12. **Request Size Limiting** - 10MB body limit with both Content-Length and streaming checks
13. **Audit Trail** - `AuditMixin` with `created_by_user_id` / `updated_by_user_id` on all entities
14. **GeoIP Geofencing** - Optional country-based access control

---

## Remediation Priority

| Priority | Finding | Effort |
|----------|---------|--------|
| 1 | C1 - Cross-tenant IDOR | Add `team_id` filters to ~10 queries |
| 2 | C2 - Unauthenticated WebSockets | Add auth checks to 2 endpoints |
| 3 | H1 - Session fixation | Add `session.clear()` before login |
| 4 | H3 - Error detail leakage | Replace `str(e)` in ~200 error responses |
| 5 | H2 - Agent auth rate limiting | Copy pattern from tenant.py |
| 6 | M1 - Missing HSTS | Add header to SecurityHeadersMiddleware |
| 7 | M2 - In-memory rate limiting | Document Redis requirement |
| 8 | M3 - Session HTTPS default | Change default or fail in production |
| 9 | M4 - Internal ID in session | Switch to GUID-based session |
| 10 | M5 - Deprecated utcnow() | Replace across codebase |
