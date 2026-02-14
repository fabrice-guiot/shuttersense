# ShutterSense Security Audit Report

**Date:** 2026-02-14
**Scope:** Full codebase (backend, frontend, agent) + production deployment (`docs/deployment-hostinger-kvm2.md`)
**Methodology:** Manual code review against OWASP Top 10 and multi-tenant security best practices, cross-referenced with documented production infrastructure controls

---

## Executive Summary

ShutterSense implements a solid security foundation with OAuth 2.0 + PKCE, Fernet encryption for credentials, tenant isolation, and comprehensive security headers. The production deployment adds significant defense-in-depth through nginx TLS termination, multi-layer firewalls (Hostinger managed + UFW + fail2ban), systemd sandboxing, and explicit production environment configuration.

The audit identified **14 security findings**. Of these, **5 require code-level fixes** (two critical, two high, one medium), while **5 are fully mitigated by the documented deployment configuration** and **4 are partially mitigated** with code improvements still recommended for defense-in-depth.

| Severity | Count | Requires Code Fix | Mitigated by Deployment |
|----------|-------|-------------------|------------------------|
| Critical | 2 | 2 | 0 |
| High | 3 | 2 | 0 (1 partially mitigated) |
| Medium | 5 | 1 | 3 fully + 1 partially |
| Low | 4 | 1 | 2 fully + 1 partially |

---

## Critical Findings

### C1. Cross-Tenant IDOR via GUID Resolution Without team_id Filtering

**Severity:** CRITICAL
**OWASP:** A01:2021 - Broken Access Control
**Status:** Requires code fix
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

**Deployment Note:** This is a pure application-layer authorization bug. No infrastructure control can mitigate cross-tenant IDOR; the fix must be in the code.

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
**Status:** Requires code fix
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

**Deployment Note:** Nginx proxies WebSocket connections through with `proxy_set_header Upgrade $http_upgrade` (deployment guide section 9.2). No infrastructure-level authentication is applied to WebSocket upgrades.

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
**Status:** Requires code fix
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

**Deployment Note:** The production session configuration (`SESSION_SAME_SITE=lax`, `SESSION_HTTPS_ONLY=true`) reduces the attack surface by preventing cross-site cookie injection, but does not fully prevent session fixation from same-site origins. The fix must be in code.

**Remediation:**
Clear the session before populating it with authenticated user data:
```python
def create_session(self, request: Request, user: User) -> None:
    request.session.clear()  # Regenerate session
    request.session["user_guid"] = user.guid  # Use GUID only (see M4)
```

---

### H2. No Rate Limiting on Agent Authentication

**Severity:** HIGH (reduced to MEDIUM by deployment mitigation)
**OWASP:** A07:2021 - Identification and Authentication Failures
**Status:** Partially mitigated by deployment; code fix recommended for defense-in-depth
**Affected File:** `backend/src/api/agent/dependencies.py` (lines 60-157)

**Description:**
The agent authentication endpoint (`get_agent_context`) has no application-level rate limiting for failed API key validation attempts. In contrast, user API token authentication in `backend/src/middleware/tenant.py` (lines 32-95) implements per-IP failure tracking with blocking after 20 failures.

**Deployment Mitigation:**
The production deployment provides infrastructure-level brute-force protection via fail2ban:
- **`nginx-limit-req` jail** (section 5.4): Catches HTTP 401 responses in the nginx access log — agent auth failures returning 401 trigger this jail (10 retries in 1 minute, 30-minute ban)
- **`recidive` jail**: Escalates repeat offenders to 1-week bans after 3 bans in a day

This means agent auth brute-force attempts ARE caught and blocked at the infrastructure layer, though with different thresholds than the in-app SEC-13 mechanism.

**Residual Risk:** If fail2ban is misconfigured or the deployment deviates from the documented guide, there is no application-level fallback.

**Recommended Improvement:**
Apply the same `_record_token_failure` / `_is_token_blocked` pattern from `tenant.py` to agent authentication for consistent defense-in-depth.

---

### H3. Internal Error Details Leaked in API Responses

**Severity:** HIGH
**OWASP:** A04:2021 - Insecure Design
**Status:** Requires code fix
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

**Deployment Note:** Nginx passes through application JSON response bodies without filtering. No infrastructure control can mask application-layer error details. The fix must be in code.

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

### M1. Missing HSTS (Strict-Transport-Security) Header in Application Code

**Severity:** MEDIUM
**OWASP:** A05:2021 - Security Misconfiguration
**Status:** Mitigated by deployment (nginx)
**Affected File:** `backend/src/main.py` (SecurityHeadersMiddleware, lines 76-148)

**Description:**
The application-level `SecurityHeadersMiddleware` does not set `Strict-Transport-Security`. In isolation, this would allow protocol downgrade attacks.

**Deployment Mitigation:**
The nginx reverse proxy configuration (deployment guide section 9.2, 9.6) handles HSTS at the infrastructure layer:

1. **HTTP-to-HTTPS redirect:** `return 301 https://$host$request_uri;` ensures all HTTP traffic is redirected
2. **HSTS header:** `add_header Strict-Transport-Security "max-age=63072000" always;` is configured in nginx with a documented staged rollout (5 min -> 1 day -> 1 week -> 2 years)
3. **TLS configuration:** Modern TLS 1.2/1.3 only, with strong cipher suite and session ticket disabled

This is the correct architectural placement for HSTS — the TLS-terminating reverse proxy (nginx) is the authoritative layer for transport security headers, not the application behind it.

**No code change needed.** The application correctly delegates transport security to the reverse proxy.

---

### M2. In-Memory Rate Limiting Bypassed with Multiple Workers

**Severity:** MEDIUM
**OWASP:** A07:2021 - Identification and Authentication Failures
**Status:** Mitigated by deployment (fail2ban)
**Affected File:** `backend/src/middleware/tenant.py` (lines 43-44)

**Description:**
The per-IP token failure tracking uses in-process dictionaries (`_token_failures`, `_token_blocked`). With 4 Gunicorn workers in production, each worker maintains separate counters.

**Deployment Mitigation:**
fail2ban provides persistent, cross-process brute-force protection that supersedes the in-memory counters:

| Jail | Monitors | Threshold | Ban Duration |
|------|----------|-----------|-------------|
| `shuttersense-token` | Application SEC-13 log messages | 10 in 5m | 2 hours |
| `nginx-limit-req` | Nginx 429/401 responses | 10 in 1m | 30 minutes |
| `recidive` | Repeat bans across all jails | 3 bans/day | 1 week |

The `shuttersense-token` jail reads from `/var/log/shuttersense/api.log`, which aggregates logs from all workers. This means that even though individual workers have separate in-memory counters, the fail2ban jail sees the total failure count across all workers and blocks the IP at the firewall level (UFW).

The in-memory counters still provide value as a fast first-line defense within each worker process.

**No code change needed.** The multi-layer approach (per-worker in-memory + cross-worker fail2ban) provides effective protection.

---

### M3. Session Cookie Defaults to HTTP (Not HTTPS-Only)

**Severity:** MEDIUM
**OWASP:** A02:2021 - Cryptographic Failures
**Status:** Mitigated by deployment (environment config + nginx)
**Affected File:** `backend/src/config/session.py` (line 53-55)

**Description:**
The code defaults `session_https_only` to `False`, which in isolation would send session cookies over HTTP.

**Deployment Mitigation:**
The production `.env` template (deployment guide section 7.7) explicitly sets:
```bash
SESSION_HTTPS_ONLY=true
SESSION_SAME_SITE=lax
```

Additionally, multiple infrastructure layers prevent HTTP session exposure:
1. **Nginx redirects** all HTTP to HTTPS (`return 301 https://...`)
2. **Gunicorn binds to `127.0.0.1:8000`** only — the application never receives external HTTP requests directly
3. **Hostinger/UFW firewalls** only expose ports 80 (redirect) and 443 (HTTPS)
4. **Startup warning** in `main.py` alerts operators if `SESSION_HTTPS_ONLY=false` in production mode

The `False` default is intentional for local development where HTTPS is not available.

**No code change needed.** The deployment configuration and architecture prevent this from being exploitable.

---

### M4. Internal Numeric ID Stored in Session

**Severity:** MEDIUM
**OWASP:** A04:2021 - Insecure Design
**Status:** Requires code fix (defense-in-depth)
**Affected File:** `backend/src/services/auth_service.py` (line 430)

**Description:**
The session stores both the internal auto-increment integer and the GUID, but authentication lookups use the numeric ID:
```python
request.session["user_id"] = user.id       # Internal numeric ID — unnecessary
request.session["user_guid"] = user.guid    # GUID already stored but unused for auth
```

The session authentication in `tenant.py:324` queries using the numeric ID:
```python
user = db.query(User).filter(User.id == user_id).first()
```

While the session cookie is signed (preventing tampering), storing sequential integer IDs makes ID prediction trivial if the signing key is compromised. The application's own architecture principle (Issue #42) states that external-facing identifiers should use GUIDs. The GUID is already present in the session — it just needs to be used.

**Deployment Note:** The signed session cookie (`SESSION_SECRET_KEY` with 32+ char requirement) makes direct tampering infeasible without key compromise. This finding is about consistency with the GUID architecture principle and defense-in-depth, not an immediately exploitable vulnerability.

**Remediation:**
Stop storing the numeric `user_id` in the session and use the existing `user_guid` for lookups:
```python
# In auth_service.py — remove user_id, keep user_guid:
request.session["user_guid"] = user.guid
# Do NOT store: request.session["user_id"] = user.id

# In tenant.py — look up by GUID instead of numeric ID:
user = db.query(User).filter(User.guid == user_guid).first()
```

---

### M5. Deprecated `datetime.utcnow()` Usage

**Severity:** MEDIUM (reduced to LOW by deployment)
**OWASP:** N/A (Reliability/Correctness)
**Status:** Partially mitigated by deployment; code fix recommended
**Affected Files:** ~90 occurrences across models and services

**Description:**
`datetime.utcnow()` is deprecated since Python 3.12 and returns naive (timezone-unaware) datetimes. This affects token expiry checks (e.g., `api_token.py` line 206, `agent_registration_token.py` lines 160, 184) and all model timestamps.

**Deployment Mitigation:**
The production server is configured with UTC timezone (deployment guide section 4.5: `timedatectl set-timezone UTC`), which eliminates the primary risk of timezone mismatch between `utcnow()` and the system clock. PostgreSQL also stores timestamps without timezone ambiguity when the server runs in UTC.

**Residual Risk:** The deprecation warning will become a removal in a future Python version. This is a technical debt item that should be addressed during a future Python version upgrade.

**Recommended Improvement:**
Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)` as part of routine maintenance:
```python
from datetime import datetime, timezone
# Before: datetime.utcnow()
# After:  datetime.now(timezone.utc)
```

---

## Low Findings

### L1. CSP Allows `unsafe-inline` for Styles

**Severity:** LOW
**Status:** Accepted risk (Tailwind CSS requirement)
**Affected File:** `backend/src/main.py` (line 130)

The SPA Content-Security-Policy includes `style-src 'self' 'unsafe-inline'`. This weakens CSP protection against style-based attacks. This is a known trade-off required by Tailwind CSS and many component libraries (including Radix UI primitives used by shadcn/ui). Consider using nonces or hashes in the future.

### L2. Default CORS Origins Include Localhost

**Severity:** LOW
**Status:** Mitigated by deployment (environment config)
**Affected File:** `backend/src/main.py` (lines 741-746)

When `CORS_ORIGINS` is not set, the default includes `http://localhost:3000` and `http://localhost:8000`.

**Deployment Mitigation:** The production `.env` (section 7.7) explicitly sets `CORS_ORIGINS=https://app.shuttersense.ai`, which completely overrides the defaults. The localhost origins only apply during local development where they are needed.

**No code change needed.**

### L3. Secret Keys Default to Empty String

**Severity:** LOW
**Status:** Partially mitigated by deployment
**Affected Files:** `backend/src/config/settings.py` (line 36), `backend/src/config/session.py` (line 28)

Both `JWT_SECRET_KEY` and `SESSION_SECRET_KEY` default to empty string.

**Deployment Mitigation:**
- `SHUSAI_MASTER_KEY`: The application calls `validate_master_key()` on startup and **exits immediately** if it is missing or invalid (section 7.7-7.8). This is a hard fail.
- `SESSION_SECRET_KEY`: If empty, `is_configured` returns `False` and session middleware is not installed, with a `UserWarning`. Sessions simply don't work.
- `JWT_SECRET_KEY`: If empty, `jwt_configured` returns `False`. Token generation would fail at usage time.
- The deployment guide (section 7.8) requires generating all three keys before the application will function.

**Recommended Improvement:** Add fail-fast behavior in production mode (`SHUSAI_ENV=production`) for `SESSION_SECRET_KEY` and `JWT_SECRET_KEY`, matching the existing behavior for `SHUSAI_MASTER_KEY`.

### L4. API Token Scopes Not Enforced

**Severity:** LOW
**Status:** Accepted risk (future enhancement)
**Affected File:** `backend/src/services/token_service.py` (line 169)

API tokens are created with `scopes=["*"]` (full access) and no mechanism exists to restrict token permissions to specific operations. This violates the principle of least privilege. Note that API tokens already cannot access super admin endpoints (enforced in `require_super_admin`).

---

## Positive Security Findings

### Application-Level Controls

1. **OAuth 2.0 with PKCE** - Properly configured with state/nonce validation
2. **Credential Encryption** - Fernet (AES-128-CBC + HMAC) with environment-based key management
3. **Tenant Isolation** - Service layer consistently filters by `team_id` (the IDOR issues are at the API layer)
4. **Security Headers** - Comprehensive CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
5. **Path Traversal Protection** - `is_path_authorized()` and `is_safe_static_file_path()` properly validate paths
6. **No SQL Injection** - Exclusive use of SQLAlchemy ORM with parameterized queries
7. **No Dangerous Functions** - No `eval()`, `exec()`, or `subprocess(shell=True)` patterns
8. **No Hardcoded Secrets** - All secrets loaded from environment variables
9. **Token Hash Storage** - API tokens and agent keys stored as SHA-256 hashes
10. **Super Admin via Hashed Emails** - No plaintext admin identifiers in configuration
11. **Frontend Security** - No `dangerouslySetInnerHTML`, proper XSS prevention, no client-side secret storage
12. **Request Size Limiting** - 10MB body limit with both Content-Length and streaming checks
13. **Audit Trail** - `AuditMixin` with `created_by_user_id` / `updated_by_user_id` on all entities
14. **GeoIP Geofencing** - Optional country-based access control with fail-closed default
15. **Per-IP Token Brute-Force Protection** (SEC-13) - In-memory tracking with auto-block after 20 failures

### Deployment-Level Controls (from `docs/deployment-hostinger-kvm2.md`)

16. **Three-Layer Firewall** - Hostinger managed firewall (cloud) + UFW (OS) + fail2ban (application-aware)
17. **TLS Termination at Nginx** - Modern TLS 1.2/1.3, strong cipher suites, session tickets disabled
18. **HSTS** - Staged rollout via nginx (5 min -> 1 day -> 1 week -> 2 years)
19. **HTTP-to-HTTPS Redirect** - nginx `return 301` for all HTTP traffic
20. **Localhost-Only Binding** - Gunicorn on `127.0.0.1:8000`, PostgreSQL on `localhost:5432`
21. **Systemd Sandboxing** - `NoNewPrivileges=yes`, `PrivateTmp=yes`, `ProtectSystem=strict`, `ProtectHome=yes`
22. **fail2ban Jails** - SSH (3 retries/24h ban), nginx rate limiting, bot scanning, OAuth abuse, API token brute-force, recidive escalation
23. **PostgreSQL Hardening** - SCRAM-SHA-256 auth, explicit reject for non-local connections, minimal privileges
24. **SSH Key-Only Auth** - Password auth disabled, root login disabled, max 3 auth tries
25. **Automatic Security Updates** - `unattended-upgrades` enabled for OS packages
26. **Secret File Permissions** - `.env` file with `chmod 600`, owned by application user
27. **CAA DNS Record** - Restricts certificate issuance to Let's Encrypt only
28. **Production Cleanup** - Development artifacts, test suites, and source maps removed from production
29. **Log Rotation** - 14-day retention with compression

---

## Remediation Priority

Findings requiring code changes, ordered by severity and effort:

| Priority | Finding | Severity | Status | Effort |
|----------|---------|----------|--------|--------|
| 1 | C1 - Cross-tenant IDOR | Critical | Requires code fix | Add `team_id` filters to ~10 queries |
| 2 | C2 - Unauthenticated WebSockets | Critical | Requires code fix | Add auth checks to 2 endpoints |
| 3 | H1 - Session fixation | High | Requires code fix | Add `session.clear()` before login |
| 4 | H3 - Error detail leakage | High | Requires code fix | Replace `str(e)` in ~200 error responses |
| 5 | M4 - Internal ID in session | Medium | Requires code fix | Remove numeric ID; use existing GUID for lookups |

Findings mitigated by deployment (no code change needed, or defense-in-depth only):

| Finding | Severity | Deployment Control | Action |
|---------|----------|-------------------|--------|
| M1 - HSTS | Medium | nginx `Strict-Transport-Security` header | No code change needed |
| M2 - In-memory rate limiting | Medium | fail2ban `shuttersense-token` + `nginx-limit-req` jails | No code change needed |
| M3 - Session HTTPS default | Medium | `.env` `SESSION_HTTPS_ONLY=true` + nginx HTTPS redirect | No code change needed |
| H2 - Agent auth rate limiting | High->Medium | fail2ban `nginx-limit-req` catches 401s | Code fix recommended (defense-in-depth) |
| M5 - Deprecated utcnow() | Medium->Low | Server timezone UTC | Code fix recommended (future-proofing) |
| L2 - Default CORS localhost | Low | `.env` `CORS_ORIGINS=https://app.shuttersense.ai` | No code change needed |
| L3 - Secret key defaults | Low | Mandatory key generation in deployment guide | Code fix recommended (fail-fast in prod) |
| L1 - CSP unsafe-inline | Low | N/A (Tailwind CSS requirement) | Accepted risk |
| L4 - API token scopes | Low | N/A (future enhancement) | Accepted risk |
