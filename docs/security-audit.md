# ShutterSense Security Audit Report

**Date:** 2026-02-14
**Scope:** Full codebase (backend, frontend, agent) + production deployment (`docs/deployment-hostinger-kvm2.md`)
**Methodology:** Manual code review against OWASP Top 10 and multi-tenant security best practices, cross-referenced with documented production infrastructure controls

---

## Executive Summary

ShutterSense implements a solid security foundation with OAuth 2.0 + PKCE, Fernet encryption for credentials, tenant isolation, and comprehensive security headers. The production deployment adds significant defense-in-depth through nginx TLS termination, multi-layer firewalls (Hostinger managed + UFW + fail2ban), systemd sandboxing, and explicit production environment configuration.

The audit identified **14 security findings**. Of these, **5 required code-level fixes** (two critical, two high, one medium), while **5 are fully mitigated by the documented deployment configuration** and **4 are partially mitigated** with code improvements still recommended for defense-in-depth.

**Phase 1 (completed):** All 5 code-level fixes have been implemented — C1, C2, H1, H3, and M4.

| Severity | Count | Fixed (Phase 1) | Mitigated by Deployment |
|----------|-------|-----------------|------------------------|
| Critical | 2 | 2 | 0 |
| High | 3 | 2 | 0 (1 partially mitigated) |
| Medium | 5 | 1 | 3 fully + 1 partially |
| Low | 4 | 0 | 2 fully + 1 partially + 1 accepted |

---

## Critical Findings

### C1. Cross-Tenant IDOR via GUID Resolution Without team_id Filtering

**Severity:** CRITICAL
**OWASP:** A01:2021 - Broken Access Control
**Status:** Fixed (Phase 1)
**Affected Files:**
- `backend/src/api/collections.py` — 7 GUID resolution queries
- `backend/src/api/tools.py` — 4 GUID resolution queries

**Description:**
When creating or updating collections, the API resolved related entity GUIDs (Connector, Pipeline, Agent) to internal IDs using direct database queries **without filtering by `team_id`**. This allowed an authenticated user from Team A to reference resources belonging to Team B.

**Fix Applied:**
Added `team_id == ctx.team_id` filtering to all 11 raw GUID resolution queries across both files:
```python
connector = db.query(Connector).filter(
    Connector.uuid == connector_uuid,
    Connector.team_id == ctx.team_id  # Added team scoping
).first()
```

---

### C2. Unauthenticated WebSocket Endpoints

**Severity:** CRITICAL
**OWASP:** A01:2021 - Broken Access Control
**Status:** Fixed (Phase 1)
**Affected Files:**
- `backend/src/api/tools.py` — both WebSocket endpoints
- `backend/src/utils/websocket.py` — team-scoped broadcast channels
- `backend/src/api/agent/routes.py` — broadcast callers updated
- `backend/src/services/tool_service.py` — broadcast callers updated

**Description:**
Two WebSocket endpoints accepted connections without any authentication or authorization checks. `/ws/jobs/all` received updates for ALL jobs globally, and `/ws/jobs/{job_id}` allowed subscribing to any job without team verification.

**Fix Applied (3 parts):**
1. **Authentication added** to both WebSocket endpoints using `get_websocket_tenant_context_standalone()` — unauthenticated connections receive code 4001 close
2. **Team-scoped channels** added to `ConnectionManager` — jobs broadcast to `__team_jobs_{team_id}` instead of the global channel
3. **All broadcast callers updated** to pass `team_id` for team-scoped delivery
```python
ctx = await get_websocket_tenant_context_standalone(websocket)
if not ctx:
    await websocket.close(code=4001, reason="Authentication required")
    return
channel_id = manager.get_team_jobs_channel(ctx.team_id)
await manager.register_accepted(channel_id, websocket)
```

---

## High Findings

### H1. Session Fixation After OAuth Login

**Severity:** HIGH
**OWASP:** A07:2021 - Identification and Authentication Failures
**Status:** Fixed (Phase 1)
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
**Status:** Fixed (Phase 1)
**Affected Files:** 10 files in `backend/src/api/`

**Description:**
Across the API layer, generic `except Exception` handlers included `str(e)` directly in HTTP error responses, potentially leaking database errors, file paths, and internal details.

**Fix Applied:**
All `except Exception` blocks now return opaque `"An internal error occurred"` messages. Exception details are logged server-side with `exc_info=True` for debugging. Specific exception handlers (`NotFoundError`, `ValidationError`, `ConflictError`) retain their user-safe messages.

```python
except Exception as e:
    logger.error(f"Error creating connector: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="An internal error occurred")
```

Files updated: `collections.py`, `connectors.py`, `categories.py`, `locations.py`, `organizers.py`, `performers.py`, `config.py`, `agent/routes.py`, `tokens.py` (logger added).

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
**Status:** Fixed (Phase 1)
**Affected Files:**
- `backend/src/services/auth_service.py` — session creation and lookup
- `backend/src/middleware/tenant.py` — session authentication in all 3 auth functions

**Description:**
The session stored internal auto-increment integer IDs (`user_id`, `team_id`) and authentication lookups used the numeric ID, violating the GUID-only external interface principle (Issue #42).

**Fix Applied:**
1. **Session creation** (`auth_service.py`): Removed `user_id` and `team_id` from session data. Session now stores only: `user_guid`, `team_guid`, `email`, `is_super_admin`, `authenticated_at`
2. **Session authentication** (`tenant.py`): All three auth functions (`_authenticate_session`, `get_websocket_tenant_context`, `get_websocket_tenant_context_standalone`) now parse `user_guid` via `GuidService.parse_identifier()` and look up by `User.uuid`
3. **Session helpers** (`auth_service.py`): `is_authenticated()` checks `user_guid`, `get_current_user_info()` returns only GUIDs

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

## Remediation Status

### Phase 1 — Completed

All 5 findings requiring code-level fixes have been remediated:

| Priority | Finding | Severity | Status | Summary |
|----------|---------|----------|--------|---------|
| 1 | C1 - Cross-tenant IDOR | Critical | **Fixed** | Added `team_id` filters to 11 GUID resolution queries |
| 2 | C2 - Unauthenticated WebSockets | Critical | **Fixed** | Added auth + team-scoped channels to both WS endpoints |
| 3 | H1 - Session fixation | High | **Fixed** | Added `session.clear()` before populating auth data |
| 4 | H3 - Error detail leakage | High | **Fixed** | Replaced `str(e)` with generic messages in ~63 handlers |
| 5 | M4 - Internal ID in session | Medium | **Fixed** | Removed numeric IDs; all lookups use GUIDs |

### Phase 2 — Defense-in-Depth Improvements (Planned)

Items that are deployment-mitigated but recommended for code-level hardening:

| Priority | Finding | Current Mitigation | Recommended Action |
|----------|---------|-------------------|-------------------|
| 1 | H2 - Agent auth rate limiting | fail2ban catches 401s | Apply SEC-13 `_record_token_failure` pattern to agent auth in `agent/dependencies.py` |
| 2 | M5 - Deprecated `datetime.utcnow()` | Server timezone UTC | Replace ~90 occurrences with `datetime.now(timezone.utc)` |
| 3 | L3 - Secret key defaults | Mandatory key generation in deploy guide | Add fail-fast in production mode for `SESSION_SECRET_KEY` and `JWT_SECRET_KEY` |
| 4 | L4 - API token scopes | Super admin endpoints already blocked | Implement scope-based permissions for API tokens |
| 5 | L1 - CSP `unsafe-inline` | N/A (Tailwind CSS requirement) | Evaluate nonce-based CSP for styles |

### Deployment-Mitigated (No Code Change Needed)

| Finding | Severity | Deployment Control |
|---------|----------|--------------------|
| M1 - HSTS | Medium | nginx `Strict-Transport-Security` header |
| M2 - In-memory rate limiting | Medium | fail2ban `shuttersense-token` + `nginx-limit-req` jails |
| M3 - Session HTTPS default | Medium | `.env` `SESSION_HTTPS_ONLY=true` + nginx HTTPS redirect |
| L2 - Default CORS localhost | Low | `.env` `CORS_ORIGINS=https://app.shuttersense.ai` |
