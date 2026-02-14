# ShutterSense Security Audit Report

**Original Audit:** 2026-02-14
**Phase 2 Review:** 2026-02-14
**Scope:** Full codebase (backend, frontend, agent) + production deployment (`docs/deployment-hostinger-kvm2.md`)
**Methodology:** Manual code review against OWASP Top 10 and multi-tenant security best practices, cross-referenced with documented production infrastructure controls

---

## Executive Summary

ShutterSense implements a solid security foundation with OAuth 2.0 + PKCE, Fernet encryption for credentials, tenant isolation, and comprehensive security headers. The production deployment adds significant defense-in-depth through nginx TLS termination, multi-layer firewalls (Hostinger managed + UFW + fail2ban), systemd sandboxing, and explicit production environment configuration.

**Phase 1** addressed all 5 code-level findings requiring immediate fixes (2 critical, 2 high, 1 medium). These are now verified and documented in [Appendix A](#appendix-a--phase-1-remediation-history).

**Phase 2** (this document's focus) identifies **10 remaining items** for defense-in-depth hardening: 5 carried forward from the original audit and 5 new findings discovered during the Phase 2 review. None are currently exploitable in production, but each represents an opportunity to strengthen the security posture.

| Category | Count | Breakdown |
|----------|-------|-----------|
| Phase 2 — New Findings | 5 | 2 medium, 3 low |
| Phase 2 — Carried Forward | 5 | 1 high, 2 medium, 2 low |
| Deployment-Mitigated (no code change) | 4 | See [Appendix B](#appendix-b--deployment-mitigated-items-no-code-change-needed) |
| Phase 1 — Fixed | 5 | See [Appendix A](#appendix-a--phase-1-remediation-history) |

---

## Phase 2 — New Findings

These issues were identified during the Phase 2 audit review and were not present in the original report.

### N1. Import Session Not Scoped by Tenant

**Severity:** MEDIUM
**OWASP:** A01:2021 - Broken Access Control
**Affected Files:**
- `backend/src/services/config_service.py` (lines 572-595)
- `backend/src/api/config.py` (lines 313-424)

**Description:**
The config import session endpoints (`get_import_session`, `resolve_import`, `cancel_import`) accept a `session_id` and retrieve the session from an in-memory dictionary without verifying that the requesting user's `team_id` matches the session's `team_id`. Although import sessions are stored with `team_id` (set during `start_import`), the retrieval in `get_import_session()` only checks existence and expiration — not tenant ownership.

The API endpoints do require authentication (`ctx: TenantContext = Depends(require_auth)`), but pass only the `session_id` to the service without `ctx.team_id` verification.

**Risk Assessment:**
The session IDs use GUID format (`imp_` prefix with 26-char Crockford Base32), making brute-force guessing practically infeasible. The real risk is defense-in-depth: if a session ID is ever leaked (logs, error messages, browser history), a user from another team could interact with it.

**Recommended Fix:**
Add `team_id` parameter to `get_import_session()`, `apply_import()`, and `cancel_import()` service methods, and verify `session["team_id"] == team_id` before returning data:
```python
def get_import_session(self, session_id: str, team_id: int) -> Dict[str, Any]:
    session = self._import_sessions.get(session_id)
    if not session or session["team_id"] != team_id:
        raise NotFoundError("Import session", session_id)
    # ...
```

---

### N2. Pipeline YAML Import Missing File Size Limit

**Severity:** MEDIUM
**OWASP:** A05:2021 - Security Misconfiguration
**Affected File:** `backend/src/api/pipelines.py` (lines 693-727)

**Description:**
The pipeline YAML import endpoint (`POST /api/pipelines/import`) reads the uploaded file with `await file.read()` without any size limit. In contrast, the config YAML import at `backend/src/api/config.py` (line 273-281) correctly limits reads to 1MB.

An attacker could upload a very large file to exhaust server memory, although the global 10MB request body limit in `SecurityHeadersMiddleware` provides a partial mitigation.

**Recommended Fix:**
Apply the same size-limited read pattern used in config import:
```python
max_import_size = 1 * 1024 * 1024  # 1MB
content = await file.read(max_import_size + 1)
if len(content) > max_import_size:
    raise HTTPException(status_code=413, detail="YAML file exceeds maximum size")
```

---

### N3. Content-Disposition Header Injection in Report Download

**Severity:** LOW
**OWASP:** A03:2021 - Injection
**Affected File:** `backend/src/api/results.py` (lines 297-311)

**Description:**
The report download endpoint constructs a `Content-Disposition` header filename using `collection_name` directly from the database without sanitization:
```python
filename = f"{report_data['tool']}_report_{report_data['collection_name']}_..."
headers={"Content-Disposition": f'attachment; filename="{filename}"'}
```

A collection name containing double quotes or newlines could inject additional headers or break the `Content-Disposition` format.

**Risk Assessment:** Collection names are created by authenticated, tenant-scoped users, so exploitation requires a malicious insider. Modern browsers also handle malformed Content-Disposition gracefully.

**Recommended Fix:**
Sanitize the filename by stripping or replacing unsafe characters:
```python
import re
safe_name = re.sub(r'[^\w\s\-.]', '_', report_data['collection_name'])
```

---

### N4. Pipeline YAML Import Missing Generic Exception Handler

**Severity:** LOW
**OWASP:** A04:2021 - Insecure Design
**Affected File:** `backend/src/api/pipelines.py` (lines 714-727)

**Description:**
The pipeline import endpoint catches `ValidationError` and `ConflictError` but lacks a generic `except Exception` handler. Unexpected errors (e.g., database failures, encoding errors) will propagate to FastAPI's default handler, which may include internal details in the response depending on configuration.

This is inconsistent with the H3 fix applied to other endpoints across the API layer.

**Recommended Fix:**
Add the standard generic handler matching the pattern used elsewhere:
```python
except Exception as e:
    logger.error(f"Error importing pipeline: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="An internal error occurred")
```

---

### N5. Agent Registration Endpoint Has No Rate Limiting

**Severity:** LOW
**OWASP:** A07:2021 - Identification and Authentication Failures
**Affected File:** `backend/src/api/agent/routes.py` (lines 292-339)

**Description:**
The `POST /api/agent/v1/register` endpoint is intentionally public (agents don't have credentials yet during registration). It accepts a one-time registration token, but there is no rate limiting on failed attempts.

**Risk Assessment:**
Registration tokens are one-time-use and stored as SHA-256 hashes, making brute-force attacks computationally expensive. The production fail2ban `nginx-limit-req` jail also catches repeated 401/400 responses. However, registration failures return 400 (not 401), so coverage depends on the specific fail2ban filter configuration.

**Recommended Fix:**
Add per-IP rate limiting to the registration endpoint, similar to the SEC-13 pattern in `tenant.py`, or add a dedicated fail2ban jail for agent registration failures.

---

## Phase 2 — Carried Forward Items

These items were identified in the original audit as deployment-mitigated but recommended for code-level hardening.

### H2. No Rate Limiting on Agent Authentication

**Severity:** HIGH (reduced to MEDIUM by deployment mitigation)
**OWASP:** A07:2021 - Identification and Authentication Failures
**Status:** Open — code fix recommended for defense-in-depth
**Affected File:** `backend/src/api/agent/dependencies.py` (lines 60-157)

**Description:**
The agent authentication function (`get_agent_context`) has no application-level rate limiting for failed API key validation attempts. User API token authentication in `backend/src/middleware/tenant.py` (lines 32-95) implements per-IP failure tracking with blocking after 20 failures (SEC-13), but this pattern has not been applied to agent authentication.

**Deployment Mitigation:**
fail2ban `nginx-limit-req` jail catches HTTP 401 responses (10 retries/minute, 30-minute ban). The `recidive` jail escalates repeat offenders.

**Residual Risk:** If fail2ban is misconfigured or the deployment deviates from the documented guide, there is no application-level fallback.

**Recommended Fix:**
Apply the `_record_token_failure` / `_is_token_blocked` pattern from `tenant.py` to agent authentication in `agent/dependencies.py`.

---

### M5. Deprecated `datetime.utcnow()` Usage

**Severity:** MEDIUM
**OWASP:** N/A (Reliability/Correctness)
**Status:** Partially addressed (~11% migrated)
**Affected Files:** ~386 occurrences using `datetime.utcnow()`, ~49 using `datetime.now(timezone.utc)`

**Description:**
`datetime.utcnow()` is deprecated since Python 3.12 and returns naive (timezone-unaware) datetimes. Some agent cache modules and newer code have migrated to `datetime.now(timezone.utc)`, but the vast majority of backend models and services still use the deprecated form.

**Deployment Mitigation:**
The production server is configured with UTC timezone (`timedatectl set-timezone UTC`), eliminating the primary risk of timezone mismatch.

**Residual Risk:** The deprecation will become a removal in a future Python version, making this a growing technical debt item.

**Recommended Fix:**
Systematic replacement across the codebase. Prioritize security-sensitive code first (token expiry checks in `token_service.py`, `agent_service.py`, `agent_registration_token.py`), then migrate remaining occurrences as routine maintenance:
```python
from datetime import datetime, timezone
# Before: datetime.utcnow()
# After:  datetime.now(timezone.utc)
```

---

### L3. Secret Keys Default to Empty String Without Fail-Fast in Production

**Severity:** LOW (elevated to MEDIUM recommendation)
**OWASP:** A05:2021 - Security Misconfiguration
**Status:** Partially addressed — validators exist, fail-fast missing
**Affected Files:**
- `backend/src/config/settings.py` (line 36)
- `backend/src/config/session.py` (line 28)
- `backend/src/main.py` (lines 489-503)

**Description:**
Both `JWT_SECRET_KEY` and `SESSION_SECRET_KEY` default to empty string. Validators enforce minimum 32 characters if a non-empty value is provided, and `main.py` logs warnings for empty keys in production mode. However, the application **continues to start** with empty keys — unlike `SHUSAI_MASTER_KEY` which triggers `sys.exit(1)`.

**Recommended Fix:**
Add fail-fast behavior in the application lifespan for production mode (`SHUSAI_ENV=production`), matching the existing `validate_master_key()` pattern:
```python
if settings.env == "production":
    if not settings.session_secret_key:
        logger.critical("SESSION_SECRET_KEY is required in production")
        sys.exit(1)
    if not settings.jwt_secret_key:
        logger.critical("JWT_SECRET_KEY is required in production")
        sys.exit(1)
```

---

### L4. API Token Scopes Not Enforced

**Severity:** LOW
**OWASP:** A01:2021 - Broken Access Control
**Status:** Open — data model prepared, enforcement not implemented
**Affected File:** `backend/src/services/token_service.py` (line 169)

**Description:**
API tokens are created with `scopes=["*"]` (full access). The `ApiToken` model stores scopes as JSON, but:
- The JWT payload does not include a `scopes` claim
- `TenantContext` has no `scopes` field
- No route-level scope enforcement exists
- Super admin endpoints are already blocked for API tokens

**Recommended Fix (when implementing):**
1. Add `scopes` claim to JWT payload in `token_service.py`
2. Add `scopes` field to `TenantContext`
3. Create `require_scope(scope: str)` FastAPI dependency
4. Apply scope validation to route handlers

---

### L1. CSP Allows `unsafe-inline` for Styles

**Severity:** LOW
**Status:** Accepted risk (Tailwind CSS / Radix UI requirement)
**Affected File:** `backend/src/main.py` (line 131)

The SPA Content-Security-Policy includes `style-src 'self' 'unsafe-inline'`. This weakens CSP protection against style-based attacks but is required by Tailwind CSS and Radix UI primitives used by shadcn/ui. `script-src` is correctly limited to `'self'` only (no inline scripts).

**Recommended Improvement:**
Evaluate nonce-based CSP for styles when build tooling supports it. This would require a Vite plugin to inject nonces and changes to the `SecurityHeadersMiddleware` to generate per-request nonces.

---

## Positive Security Findings

### Application-Level Controls

1. **OAuth 2.0 with PKCE** — Properly configured with state/nonce validation
2. **Credential Encryption** — Fernet (AES-128-CBC + HMAC) with environment-based key management
3. **Tenant Isolation** — Service layer consistently filters by `team_id`; API layer IDOR issues fixed in Phase 1
4. **Security Headers** — Comprehensive CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
5. **Path Traversal Protection** — `is_path_authorized()` and `is_safe_static_file_path()` properly validate paths
6. **No SQL Injection** — Exclusive use of SQLAlchemy ORM with parameterized queries
7. **No Dangerous Functions** — No `eval()`, `exec()`, or `subprocess(shell=True)` patterns
8. **No Hardcoded Secrets** — All secrets loaded from environment variables
9. **Token Hash Storage** — API tokens and agent keys stored as SHA-256 hashes
10. **Super Admin via Hashed Emails** — No plaintext admin identifiers in configuration
11. **Frontend Security** — No `dangerouslySetInnerHTML`, proper XSS prevention, no client-side secret storage
12. **Request Size Limiting** — 10MB body limit with both Content-Length and streaming checks
13. **Audit Trail** — `AuditMixin` with `created_by_user_id` / `updated_by_user_id` on all entities
14. **GeoIP Geofencing** — Optional country-based access control with fail-closed default
15. **Per-IP Token Brute-Force Protection** (SEC-13) — In-memory tracking with auto-block after 20 failures

### Deployment-Level Controls

16. **Three-Layer Firewall** — Hostinger managed firewall (cloud) + UFW (OS) + fail2ban (application-aware)
17. **TLS Termination at Nginx** — Modern TLS 1.2/1.3, strong cipher suites, session tickets disabled
18. **HSTS** — Staged rollout via nginx (5 min -> 1 day -> 1 week -> 2 years)
19. **HTTP-to-HTTPS Redirect** — nginx `return 301` for all HTTP traffic
20. **Localhost-Only Binding** — Gunicorn on `127.0.0.1:8000`, PostgreSQL on `localhost:5432`
21. **Systemd Sandboxing** — `NoNewPrivileges=yes`, `PrivateTmp=yes`, `ProtectSystem=strict`, `ProtectHome=yes`
22. **fail2ban Jails** — SSH (3 retries/24h ban), nginx rate limiting, bot scanning, OAuth abuse, API token brute-force, recidive escalation
23. **PostgreSQL Hardening** — SCRAM-SHA-256 auth, explicit reject for non-local connections, minimal privileges
24. **SSH Key-Only Auth** — Password auth disabled, root login disabled, max 3 auth tries
25. **Automatic Security Updates** — `unattended-upgrades` enabled for OS packages
26. **Secret File Permissions** — `.env` file with `chmod 600`, owned by application user
27. **CAA DNS Record** — Restricts certificate issuance to Let's Encrypt only
28. **Production Cleanup** — Development artifacts, test suites, and source maps removed from production
29. **Log Rotation** — 14-day retention with compression

---

## Phase 2 Remediation Priority

| Priority | Finding | Severity | Effort | Recommended Action |
|----------|---------|----------|--------|--------------------|
| 1 | N1 - Import session tenant scoping | Medium | Low | Add `team_id` verification to import session service methods |
| 2 | H2 - Agent auth rate limiting | Medium | Low | Apply SEC-13 `_record_token_failure` pattern to `agent/dependencies.py` |
| 3 | N2 - Pipeline import size limit | Medium | Low | Add 1MB size-limited read matching config import pattern |
| 4 | N4 - Pipeline import error handler | Low | Low | Add `except Exception` handler consistent with H3 fix |
| 5 | L3 - Secret key fail-fast | Low | Low | Add `sys.exit(1)` for empty keys in production mode |
| 6 | N3 - Content-Disposition injection | Low | Low | Sanitize collection name in download filename |
| 7 | N5 - Agent registration rate limiting | Low | Low | Add per-IP rate limiting or dedicated fail2ban jail |
| 8 | M5 - `datetime.utcnow()` migration | Medium | High | Replace ~386 occurrences; prioritize security-sensitive code |
| 9 | L4 - API token scopes | Low | High | Implement scope-based permissions (deferred to feature work) |
| 10 | L1 - CSP `unsafe-inline` styles | Low | High | Evaluate nonce-based CSP when tooling supports it |

---

## Appendix A — Phase 1 Remediation History

All 5 findings requiring code-level fixes were remediated in Phase 1 and verified in the Phase 2 review.

### C1. Cross-Tenant IDOR via GUID Resolution Without team_id Filtering

**Severity:** CRITICAL
**OWASP:** A01:2021 - Broken Access Control
**Status:** Fixed (Phase 1) — Verified (Phase 2)
**Affected Files:**
- `backend/src/api/collections.py` — 7 GUID resolution queries
- `backend/src/api/tools.py` — 4 GUID resolution queries

**Description:**
When creating or updating collections, the API resolved related entity GUIDs (Connector, Pipeline, Agent) to internal IDs using direct database queries **without filtering by `team_id`**. This allowed an authenticated user from Team A to reference resources belonging to Team B.

**Fix Applied:**
Added `team_id == ctx.team_id` filtering to all 11 raw GUID resolution queries across both files. Phase 2 review confirmed all queries follow the pattern:
```python
connector = db.query(Connector).filter(
    Connector.uuid == connector_uuid,
    Connector.team_id == ctx.team_id  # Added team scoping
).first()
```

Additionally verified that newer API files (`connectors.py`, `pipelines.py`, `events.py`, `agent/routes.py`) consistently use team-scoped service methods or include `team_id` in direct queries.

---

### C2. Unauthenticated WebSocket Endpoints

**Severity:** CRITICAL
**OWASP:** A01:2021 - Broken Access Control
**Status:** Fixed (Phase 1) — Verified (Phase 2)
**Affected Files:**
- `backend/src/api/tools.py` — both WebSocket endpoints
- `backend/src/utils/websocket.py` — team-scoped broadcast channels
- `backend/src/api/agent/routes.py` — broadcast callers updated
- `backend/src/services/tool_service.py` — broadcast callers updated

**Description:**
Two WebSocket endpoints accepted connections without any authentication or authorization checks. `/ws/jobs/all` received updates for ALL jobs globally, and `/ws/jobs/{job_id}` allowed subscribing to any job without team verification.

**Fix Applied (3 parts):**
1. **Authentication added** to both WebSocket endpoints using `get_websocket_tenant_context_standalone()` — unauthenticated connections receive code 4001 close
2. **Team-scoped channels** added to `ConnectionManager` — jobs broadcast to `__team_jobs_{team_id}__` instead of the global channel
3. **All broadcast callers updated** to pass `team_id` for team-scoped delivery

---

### H1. Session Fixation After OAuth Login

**Severity:** HIGH
**OWASP:** A07:2021 - Identification and Authentication Failures
**Status:** Fixed (Phase 1) — Verified (Phase 2)
**Affected File:** `backend/src/services/auth_service.py`

**Description:**
After successful OAuth authentication, `create_session()` set session data without first clearing or regenerating the session, enabling session fixation.

**Fix Applied:**
Added `request.session.clear()` before populating session data:
```python
def create_session(self, request: Request, user: User) -> None:
    request.session.clear()  # Prevent session fixation
    request.session["user_guid"] = user.guid
    # ...
```

---

### H3. Internal Error Details Leaked in API Responses

**Severity:** HIGH
**OWASP:** A04:2021 - Insecure Design
**Status:** Fixed (Phase 1) — Verified (Phase 2)
**Affected Files:** 10 files in `backend/src/api/`

**Description:**
Across the API layer, generic `except Exception` handlers included `str(e)` directly in HTTP error responses, potentially leaking database errors, file paths, and internal details.

**Fix Applied:**
All `except Exception` blocks now return opaque `"An internal error occurred"` messages. Exception details are logged server-side with `exc_info=True` for debugging. Specific exception handlers (`NotFoundError`, `ValidationError`, `ConflictError`) retain their user-safe messages.

Files updated: `collections.py`, `connectors.py`, `categories.py`, `locations.py`, `organizers.py`, `performers.py`, `config.py`, `agent/routes.py`, `tokens.py`.

**Note:** The Phase 2 review found that `pipelines.py` import endpoint is missing this pattern (see finding N4).

---

### M4. Internal Numeric ID Stored in Session

**Severity:** MEDIUM
**OWASP:** A04:2021 - Insecure Design
**Status:** Fixed (Phase 1) — Verified (Phase 2)
**Affected Files:**
- `backend/src/services/auth_service.py` — session creation and lookup
- `backend/src/middleware/tenant.py` — session authentication in all 3 auth functions

**Description:**
The session stored internal auto-increment integer IDs (`user_id`, `team_id`) and authentication lookups used the numeric ID, violating the GUID-only external interface principle (Issue #42).

**Fix Applied:**
1. **Session creation** (`auth_service.py`): Session now stores only: `user_guid`, `team_guid`, `email`, `is_super_admin`, `authenticated_at`
2. **Session authentication** (`tenant.py`): All three auth functions now parse `user_guid` via `GuidService.parse_identifier()` and look up by `User.uuid`
3. **Session helpers** (`auth_service.py`): `is_authenticated()` checks `user_guid`, `get_current_user_info()` returns only GUIDs

---

## Appendix B — Deployment-Mitigated Items (No Code Change Needed)

These items are fully mitigated by the production deployment configuration documented in `docs/deployment-hostinger-kvm2.md`. No code changes are required.

### M1. Missing HSTS Header in Application Code

**Severity:** MEDIUM
**OWASP:** A05:2021 - Security Misconfiguration

The application-level `SecurityHeadersMiddleware` does not set `Strict-Transport-Security`. This is the correct architectural decision — HSTS belongs at the TLS-terminating reverse proxy (nginx), which sets `add_header Strict-Transport-Security "max-age=63072000" always;` with a staged rollout. The nginx configuration also forces HTTP-to-HTTPS redirect and uses modern TLS 1.2/1.3 only.

### M2. In-Memory Rate Limiting Bypassed with Multiple Workers

**Severity:** MEDIUM
**OWASP:** A07:2021 - Identification and Authentication Failures

Per-IP token failure tracking uses in-process dictionaries. With 4 Gunicorn workers, each maintains separate counters. fail2ban's `shuttersense-token` jail reads aggregated logs across all workers and blocks at the firewall level (UFW), providing persistent cross-process protection. The in-memory counters remain valuable as a fast first-line defense within each worker.

### M3. Session Cookie Defaults to HTTP (Not HTTPS-Only)

**Severity:** MEDIUM
**OWASP:** A02:2021 - Cryptographic Failures

The code defaults `session_https_only` to `False` for local development. Production `.env` sets `SESSION_HTTPS_ONLY=true`. Additional layers prevent HTTP session exposure: nginx HTTPS redirect, Gunicorn binding to `127.0.0.1:8000` only, and firewall rules exposing only ports 80 (redirect) and 443 (HTTPS).

### L2. Default CORS Origins Include Localhost

**Severity:** LOW
**OWASP:** A05:2021 - Security Misconfiguration

Default CORS origins include `http://localhost:3000` and `http://localhost:8000` for local development. Production `.env` explicitly sets `CORS_ORIGINS=https://app.shuttersense.ai`, which completely overrides the defaults.
