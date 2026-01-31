# Security Guidelines

This document covers the security architecture, known risks, and operational guidelines for ShutterSense. It serves as both a reference for developers and a deployment checklist for operators.

## Table of Contents

- [Security Architecture Overview](#security-architecture-overview)
- [Pre-Release Security Audit Findings](#pre-release-security-audit-findings)
- [Authentication](#authentication)
- [Authorization and Tenant Isolation](#authorization-and-tenant-isolation)
- [Credential and Secret Management](#credential-and-secret-management)
- [API Security](#api-security)
- [Agent Security](#agent-security)
- [Frontend Security](#frontend-security)
- [Infrastructure Security](#infrastructure-security)
- [Production Deployment Checklist](#production-deployment-checklist)
- [Security Development Guidelines](#security-development-guidelines)
- [Incident Response](#incident-response)

---

## Security Architecture Overview

ShutterSense is a multi-component application with three main surfaces:

| Component | Role | Auth Mechanism |
|-----------|------|----------------|
| **Backend** (FastAPI) | API server, SPA host | Session cookies, JWT API tokens |
| **Frontend** (React SPA) | User interface | Session cookies (HttpOnly) |
| **Agent** (Python binary) | Distributed job executor | API key (Bearer token) |

### Trust Boundaries

```
Internet ──▶ [Reverse Proxy (TLS)] ──▶ [FastAPI Backend] ──▶ [PostgreSQL]
                                            │
                                            ├──▶ [OAuth Providers (Google/Microsoft)]
                                            │
              [Agent Binary] ◀──────────────┘
                  │
                  ▼
            [Local Filesystem / Cloud Storage]
```

### Defense in Depth

The application implements layered security:

1. **Network**: TLS termination at reverse proxy, CORS, rate limiting
2. **Transport**: Session cookies with SameSite, HTTPS-only enforcement
3. **Application**: Input validation (Pydantic), SQL injection prevention (SQLAlchemy ORM), security headers (CSP, X-Frame-Options)
4. **Data**: Fernet encryption for stored credentials, SHA-256 hashed API tokens
5. **Access Control**: Multi-tenant isolation via `team_id`, role-based super admin

---

## Pre-Release Security Audit Findings

Full audit conducted 2026-01-30 covering backend, frontend, and agent components.

### Critical Findings

#### SEC-01: Microsoft OAuth Issuer Validation Disabled

- **File**: `backend/src/auth/oauth_client.py:40-46`
- **Severity**: Critical
- **Description**: The `MicrosoftOAuth2App` class disables JWT issuer (`iss`) claim validation by setting `"essential": False`. This is a workaround for Microsoft's multi-tenant "common" endpoint returning tenant-specific issuers that don't match the discovery document's placeholder.
- **Risk**: An attacker could present a token from a different Azure AD tenant or a forged token with an arbitrary issuer, potentially bypassing identity verification.
- **Remediation**: Validate that the issuer matches the expected pattern `https://login.microsoftonline.com/{tenant_id}/v2.0` by extracting the `tid` (tenant ID) from the token and constructing the expected issuer dynamically. The `nonce` and `aud` (audience) claims are still validated, which significantly limits the attack surface, but issuer validation should not be skipped entirely.

#### SEC-02: Agent API Key Stored in Plaintext on Disk

- **File**: `agent/src/config.py:330-344`
- **Severity**: Critical
- **Description**: After registration, the agent saves its API key to `~/.config/shuttersense/agent-config.yaml` in plaintext YAML. Unlike the credential store (which uses Fernet encryption), the config file has no encryption and no explicit file permissions set.
- **Risk**: Any local user or process with read access to the config file can extract the API key and impersonate the agent.
- **Remediation**: Either encrypt the API key using the same Fernet mechanism as `credential_store.py`, or at minimum set file permissions to `0o600` after writing. The environment variable path (`SHUSAI_API_KEY`) should be recommended as the primary mechanism for production deployments.

### High Findings

#### SEC-03: Session Cookie Defaults Insecure for Production

- **File**: `backend/src/config/session.py:53-56`
- **Severity**: High
- **Description**: `SESSION_HTTPS_ONLY` defaults to `False` and `SESSION_SAME_SITE` defaults to `"lax"`. The 24-hour `SESSION_MAX_AGE` is generous. No startup warning is emitted when running with insecure defaults in production.
- **Risk**: Session cookies transmitted over HTTP can be intercepted. Long session durations increase the window for session hijacking.
- **Remediation**: Add a startup check that logs a warning when `SHUSAI_ENV=production` and `SESSION_HTTPS_ONLY=false`. Consider defaulting `SESSION_MAX_AGE` to 8 hours. Document production-required values prominently.

#### SEC-04: CORS Allows All Methods and Headers

- **File**: `backend/src/main.py:643-650`
- **Severity**: High
- **Description**: `allow_methods=["*"]` and `allow_headers=["*"]` in the CORS middleware accept any HTTP method and header.
- **Risk**: Increases attack surface by allowing unnecessary methods (TRACE, CONNECT) and arbitrary custom headers in cross-origin requests.
- **Remediation**: Restrict to `allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]` and `allow_headers=["Content-Type", "Authorization", "X-Requested-With"]`.

#### SEC-05: Debug Profile Endpoint Exposed

- **File**: `backend/src/api/auth.py:339-378`
- **Severity**: High
- **Description**: The `GET /api/auth/profile/debug` endpoint exposes OAuth provider names, subject identifiers, and login timestamps.
- **Risk**: Information useful for targeted account takeover or social engineering.
- **Remediation**: Remove the endpoint or restrict it to super admin only. If kept for support purposes, add audit logging.

#### SEC-06: Request Size Limit Bypass via Missing Content-Length

- **File**: `backend/src/main.py:149-179`
- **Severity**: High
- **Description**: The `RequestSizeLimitMiddleware` checks the `Content-Length` header, which is optional. Chunked transfer encoding requests without `Content-Length` bypass this check entirely.
- **Risk**: Memory exhaustion via large request bodies without a Content-Length header.
- **Remediation**: Add streaming body size tracking in addition to header checks, or configure the ASGI server (uvicorn/gunicorn) with a `--limit-request-body` flag.

#### SEC-07: Agent Development Mode Bypasses Attestation

- **File**: `agent/src/attestation.py:179-194`
- **Severity**: High
- **Description**: Setting `SHUSAI_AGENT_DEV_MODE=true` disables binary attestation checks completely.
- **Risk**: If an attacker can control environment variables on an agent host, they can disable the attestation system and run tampered binaries.
- **Remediation**: Remove this bypass for production builds. If needed for development, gate it behind a compile-time flag rather than a runtime environment variable.

#### SEC-08: Agent Allows HTTP Server URLs

- **File**: `agent/src/config.py:41-49`
- **Severity**: High
- **Description**: The URL validation regex accepts both `http://` and `https://` server URLs. No warning is emitted when connecting over unencrypted HTTP.
- **Risk**: API key and all data transmitted in plaintext over the network.
- **Remediation**: Emit a prominent warning when HTTP is used. For production, enforce HTTPS by default with an explicit `--allow-insecure` flag for development.

### Medium Findings

#### SEC-09: Sensitive Data in Debug Logs

- **File**: `backend/src/services/auth_service.py:373`
- **Severity**: Medium
- **Description**: `logger.debug(f"No 'picture' field in user_info. Available: {user_info}")` logs the entire OAuth user info object, potentially including email, name, and provider-specific PII.
- **Risk**: Debug logs collected in production could expose user information.
- **Remediation**: Log only field names, never values: `logger.debug(f"user_info keys: {list(user_info.keys())}")`.

#### SEC-10: Offline Results Stored Unencrypted

- **File**: `agent/src/cache/result_store.py:49, 75`
- **Severity**: Medium
- **Description**: Analysis results cached locally for offline sync are stored as plaintext JSON. These files contain file paths, metadata, and analysis data.
- **Risk**: Sensitive filesystem information exposed if agent host is compromised.
- **Remediation**: Apply the same Fernet encryption used by `credential_store.py` to cached results.

#### SEC-11: CSP Allows unsafe-inline for Styles

- **File**: `backend/src/main.py:122`
- **Severity**: Medium
- **Description**: The Content Security Policy includes `style-src 'self' 'unsafe-inline'`, allowing inline style injection.
- **Risk**: Inline styles can be used for CSS-based information exfiltration attacks, though the practical impact is low.
- **Remediation**: If Tailwind CSS requires inline styles at build time, consider using a nonce-based CSP instead. Otherwise, remove `'unsafe-inline'`.

#### SEC-12: Super Admin Hashes in Source Code

- **File**: `backend/src/config/super_admins.py:33`
- **Severity**: Medium
- **Description**: Super admin email SHA-256 hashes are hardcoded in source code. While hashes don't directly reveal emails, common admin email patterns could be brute-forced.
- **Risk**: Admin account enumeration via rainbow table attacks on common email addresses.
- **Remediation**: Move super admin configuration to an environment variable (`SHUSAI_SUPER_ADMIN_HASHES`) or database configuration. Never store in version-controlled source.

#### SEC-13: No Rate Limiting on Token Validation

- **File**: `backend/src/services/token_service.py:184-258`
- **Severity**: Medium
- **Description**: The `validate_token()` method has no rate limiting. Failed token validation attempts are not tracked or throttled.
- **Risk**: Brute force attacks on API tokens.
- **Remediation**: Track failed validation attempts per IP. Implement exponential backoff after repeated failures. Log suspicious validation patterns.

#### SEC-14: File Upload Size Not Validated Before Read

- **File**: `backend/src/api/config.py:250-294`
- **Severity**: Medium
- **Description**: The YAML import endpoint reads the entire uploaded file into memory before any size validation.
- **Risk**: Memory exhaustion via large file uploads on this specific endpoint, despite the global 10MB middleware.
- **Remediation**: Check `file.size` or read with a size limit before processing.

#### SEC-15: Agent Error Messages Leak System Details

- **File**: `agent/cli/run.py:161`, `agent/cli/sync_results.py:116-133`
- **Severity**: Medium
- **Description**: Exception messages are printed directly to the user (`click.echo(f"failed: {e}")`), potentially leaking filesystem paths, server details, or configuration information.
- **Remediation**: Wrap exceptions and display generic user-facing messages. Log full details to a local log file.

### Low Findings

#### SEC-16: PyInstaller Version Not Pinned in Build Scripts

- **File**: `agent/packaging/build_macos.sh:17`
- **Severity**: Low
- **Description**: `pip install -q pyinstaller` installs the latest version without pinning.
- **Risk**: Supply chain attack via compromised PyInstaller release.
- **Remediation**: Pin to a specific version: `pip install pyinstaller==6.x.y`.

#### SEC-17: TypeScript Strict Mode Disabled

- **File**: `frontend/tsconfig.json:18`
- **Severity**: Low
- **Description**: `"strict": false` reduces type safety guarantees.
- **Risk**: Type-related runtime errors that could manifest as security bugs.
- **Remediation**: Enable strict mode and address type errors incrementally.

#### SEC-18: JWT Expiration Relies on Library Default

- **File**: `backend/src/services/token_service.py:196-200`
- **Severity**: Low (PyJWT verifies `exp` by default)
- **Description**: `jwt.decode()` does not explicitly pass `options={"verify_exp": True}`. PyJWT defaults to verifying expiration, but the explicit intent is not documented.
- **Risk**: If PyJWT behavior changes or a different library is used, tokens might not expire.
- **Remediation**: Add explicit `options={"verify_exp": True}` for defense in depth, and add a code comment noting the intent.

---

## Authentication

### OAuth 2.0 (User Login)

- **Providers**: Google, Microsoft (via Authlib)
- **Flow**: Authorization Code with PKCE (S256)
- **Session**: Signed cookies via Starlette SessionMiddleware
- **Anti-forgery**: State parameter + nonce for replay prevention

**Security requirements for OAuth configuration:**

1. Always use HTTPS redirect URIs in production
2. Rotate client secrets periodically (annually at minimum)
3. Use separate OAuth applications for development and production
4. Restrict the OAuth application to the minimum required scopes (`openid email profile`)

### API Tokens (Programmatic Access)

- **Format**: JWT signed with HS256 using `JWT_SECRET_KEY`
- **Storage**: Token hash (SHA-256) stored in database; raw token never persisted
- **Scope**: Scoped to user's team; cannot access super admin endpoints
- **Lifecycle**: Configurable expiry (default 90 days, max 365 days); revocable through UI
- **Display**: Shown once at creation, then only the prefix is visible

### Agent Authentication

- **Registration**: One-time registration token (`art_` prefix)
- **Runtime**: API key in `Authorization: Bearer` header
- **Attestation**: Binary checksum verified against release manifests (when `REQUIRE_AGENT_ATTESTATION=true`)

---

## Authorization and Tenant Isolation

### Multi-Tenant Data Model

All user data is scoped to a `team_id`. Every service method that queries data accepts a `TenantContext` and filters by `team_id`.

**Rules:**

- Cross-team access returns `404 Not Found` (not `403 Forbidden`) to prevent resource existence leakage
- API tokens inherit the team of the user who created them
- Super admin status is determined by email hash comparison, not database role
- API tokens can never grant super admin access

### Public Endpoints (No Auth Required)

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Health check |
| `GET /api/version` | Version information |
| `GET /api/auth/*` | OAuth login and callback |
| `POST /api/agent/v1/register` | Agent registration (requires one-time token) |

All other endpoints require authentication.

---

## Credential and Secret Management

### Required Secrets

| Secret | Purpose | Generation |
|--------|---------|------------|
| `SHUSAI_MASTER_KEY` | Encrypts stored connector credentials (Fernet) | `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `SESSION_SECRET_KEY` | Signs session cookies | `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `JWT_SECRET_KEY` | Signs API tokens (must differ from SESSION_SECRET_KEY) | `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `SHUSAI_DB_URL` | Database connection with credentials | Manual configuration |

### Secret Rotation Impact

| Secret | Rotation Effect |
|--------|----------------|
| `SHUSAI_MASTER_KEY` | **Destructive**: All encrypted connector credentials become unreadable |
| `SESSION_SECRET_KEY` | All active user sessions are invalidated |
| `JWT_SECRET_KEY` | All API tokens are invalidated |
| `VAPID_PRIVATE_KEY` | All push notification subscriptions become invalid |

### Storage Security

- **Connector credentials** (S3 keys, GCS service accounts, SMB passwords): Encrypted with Fernet before database storage, decrypted on access with audit logging
- **Agent API keys**: Stored as SHA-256 hashes in the database; the raw key is returned once at registration
- **API tokens**: Stored as SHA-256 hashes; the raw JWT is returned once at creation
- **OAuth client secrets**: Environment variables only; never stored in database

### Operational Rules

1. Never commit `.env` files to version control (verified: `.gitignore` properly excludes them)
2. Never log secret values; log only identifiers or hashes
3. Use separate secrets for each environment (development, staging, production)
4. Store production secrets in a secrets manager (AWS Secrets Manager, HashiCorp Vault, or equivalent)
5. Rotate OAuth client secrets annually

---

## API Security

### Input Validation

- All request bodies validated via Pydantic v2 schemas
- Path parameters use GUID format validation (`{prefix}_{26-char}`)
- Query parameters validated with type coercion and bounds checking
- No raw SQL queries; all database access through SQLAlchemy ORM

### Rate Limiting

- Authentication endpoints: 10 requests/minute per IP
- YAML import: 5 requests/minute per IP
- Tool execution: 10 requests/minute per IP
- Global default via slowapi middleware

### Security Headers

Applied to all responses via `SecurityHeadersMiddleware`:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-XSS-Protection` | `1; mode=block` | Legacy XSS filter |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control referrer leakage |
| `Content-Security-Policy` | Varies by route | Restrict resource loading |
| `Permissions-Policy` | Restrictive | Disable unused browser APIs |

### CORS

- Origins configured via `CORS_ORIGINS` environment variable
- Credentials allowed (cookies)
- Production: restrict to exact production domain only

### Request Size

- Global limit: 10MB via `RequestSizeLimitMiddleware`
- Applied via `Content-Length` header check

---

## Agent Security

### Binary Attestation

When `REQUIRE_AGENT_ATTESTATION=true`, agents must present a valid binary checksum that matches a release manifest registered by a super admin. This prevents tampered agent binaries from connecting to the server.

### Local Credential Storage

Agent stores cloud connector credentials using Fernet encryption:

- **Location**: `~/.shuttersense-agent/credentials/` (platform-specific)
- **Permissions**: Directory `0o700`, files `0o600`
- **Master key**: Auto-generated, stored at `~/.shuttersense-agent/master.key` with `0o600`

### Authorized Paths

The `SHUSAI_AUTHORIZED_LOCAL_ROOTS` setting restricts which filesystem paths agents can access for local collections. If not set, local collections are disabled.

### Network Security

- Agent communicates with server via HTTPS (recommended) or HTTP (development only)
- API key sent in `Authorization: Bearer` header on every request
- WebSocket connections for real-time progress use `wss://` when HTTPS is configured

---

## Frontend Security

### XSS Prevention

- React's default JSX escaping handles all user-rendered content
- No use of `dangerouslySetInnerHTML` in production code
- Content Security Policy restricts script sources to `'self'`

### Session Management

- Authentication via HttpOnly session cookies (set by backend)
- No tokens or credentials stored in `localStorage` or `sessionStorage`
- Temporary redirect URL in `sessionStorage` is the only session-scoped storage, cleared after use
- Automatic redirect to login on 401 response

### Sensitive Data Display

- API tokens shown once at creation, then only the prefix
- Agent registration tokens shown once with copy-to-clipboard
- Connector credential forms send data directly to backend; never stored client-side

### Build Security

- Source maps disabled in production builds
- Console logging removed via Terser in production builds
- No secrets in `VITE_*` environment variables
- Zero npm audit vulnerabilities (as of 2026-01-30)

---

## Infrastructure Security

### TLS/HTTPS

Required for production. Enables:

- Secure session cookies (`SESSION_HTTPS_ONLY=true`)
- OAuth redirect URIs (providers require HTTPS)
- Web Push notifications (VAPID requires secure context)
- Agent API key protection in transit

### Reverse Proxy

Place nginx (or equivalent) in front of the application:

- Terminate TLS at the proxy
- Forward `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto` headers
- Configure WebSocket proxying for `/api/tools/ws/` paths
- Set `client_max_body_size` to match the application's 10MB limit

### Database

- Use a dedicated database user with minimal required privileges
- Enable SSL for database connections in production
- Regular automated backups (pg_dump)
- Store connection credentials in a secrets manager, not in `.env` files on disk

### Logging

- Production log level: `WARNING` (set via `SHUSAI_LOG_LEVEL`)
- Never log request/response bodies containing credentials
- Never log OAuth user info objects (log field names only)
- Retain logs for incident investigation (minimum 90 days)

---

## Production Deployment Checklist

### Secrets Configuration

- [ ] `SHUSAI_MASTER_KEY` set to a unique Fernet key (not the development key)
- [ ] `SESSION_SECRET_KEY` set to a unique value (min 32 characters)
- [ ] `JWT_SECRET_KEY` set to a unique value (different from SESSION_SECRET_KEY)
- [ ] `SHUSAI_DB_URL` uses a strong, unique database password
- [ ] OAuth client secrets are production-specific (not development credentials)
- [ ] VAPID keys generated for this deployment
- [ ] All secrets stored in a secrets manager (not in `.env` files on the host)

### Transport Security

- [ ] TLS certificate configured on the reverse proxy
- [ ] `SESSION_HTTPS_ONLY=true`
- [ ] OAuth redirect URIs use `https://`
- [ ] `CORS_ORIGINS` restricted to the production domain only
- [ ] HTTP to HTTPS redirect configured at the reverse proxy

### Application Hardening

- [ ] `SHUSAI_ENV=production`
- [ ] `SHUSAI_LOG_LEVEL=WARNING`
- [ ] Debug endpoints removed or restricted (`/api/auth/profile/debug`)
- [ ] `REQUIRE_AGENT_ATTESTATION=true` (if using distributed agents)
- [ ] `SHUSAI_AUTHORIZED_LOCAL_ROOTS` set to specific paths (or unset to disable local collections)
- [ ] `INMEMORY_JOB_TYPES` left empty (all jobs processed by agents)

### Database Security

- [ ] Dedicated database user with minimal privileges
- [ ] Database connections use SSL
- [ ] Database password is unique and strong
- [ ] Alembic migrations run successfully (`alembic upgrade head`)
- [ ] Database backups configured and tested

### Monitoring

- [ ] Health check endpoint monitored (`GET /health`)
- [ ] Agent heartbeat monitoring configured
- [ ] Failed authentication attempts logged and alerted
- [ ] Rate limit hits logged
- [ ] Error rates tracked

---

## Security Development Guidelines

### Adding New API Endpoints

1. **Authentication**: All endpoints require auth unless explicitly public. Use `Depends(get_tenant_context)` for tenant-scoped endpoints.
2. **Input validation**: Use Pydantic schemas for all request bodies. Validate GUIDs with prefix checks.
3. **Tenant isolation**: Always filter queries by `team_id`. Never expose internal numeric IDs.
4. **Error responses**: Return generic messages. Never expose stack traces, SQL queries, or internal paths.
5. **Rate limiting**: Apply `@limiter.limit()` to state-changing endpoints.

### Adding New Entities

1. Implement `ExternalIdMixin` for GUID generation
2. Register a GUID prefix in `docs/domain-model.md`
3. Ensure all service methods accept and filter by `team_id`
4. Use `404` (not `403`) for cross-tenant access attempts

### Handling Credentials

1. Never log credential values; use identifiers or masked representations
2. Encrypt at rest using `backend/src/utils/crypto.py`
3. Decrypt only when needed; never cache decrypted credentials
4. Log all credential access events for audit

### Writing Tests

1. Include negative security tests (unauthorized access, cross-tenant access, invalid input)
2. Test that internal IDs are not exposed in API responses
3. Test rate limiting behavior
4. Use generated test credentials (never real ones)

---

## Incident Response

### If a Secret is Compromised

| Secret | Action |
|--------|--------|
| `SHUSAI_MASTER_KEY` | Re-encrypt all connector credentials with a new key. Requires database migration script. |
| `SESSION_SECRET_KEY` | Rotate key; all users must re-login |
| `JWT_SECRET_KEY` | Rotate key; all API tokens become invalid; users must regenerate |
| OAuth client secret | Rotate in the OAuth provider console and update environment variable |
| Agent API key | Revoke the agent in the web UI; re-register the agent |
| Database password | Change in PostgreSQL; update `SHUSAI_DB_URL`; restart application |

### If the `.env` File is Exposed

1. Immediately rotate ALL secrets listed in the file
2. Revoke and regenerate OAuth client secrets in provider consoles
3. Change the database password
4. Review audit logs for unauthorized access
5. Check if the exposure was via version control (search git history)

### If an Agent is Compromised

1. Revoke the agent's registration in the web UI
2. Review job history for unauthorized executions
3. Rotate any connector credentials the agent had access to
4. Re-register a new agent on a clean host
