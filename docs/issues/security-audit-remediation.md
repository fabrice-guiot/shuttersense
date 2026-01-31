# Security Audit Remediation Plan

**Audit Date**: 2026-01-30
**Reference**: [docs/security.md](../security.md)
**Target**: v1.0 release

---

## Phase 1 — Before v1.0 Tag

Critical and high-severity items that block the release.

### SEC-01: Fix Microsoft OAuth Issuer Validation

- **Severity**: Critical
- **File**: `backend/src/auth/oauth_client.py:40-46`
- **Problem**: `MicrosoftOAuth2App.parse_id_token()` disables issuer validation entirely (`"essential": False, "value": None`). This is a workaround for Microsoft's multi-tenant "common" endpoint returning tenant-specific issuers.
- **Fix**: Extract the `tid` (tenant ID) claim from the token and validate the issuer against the expected pattern `https://login.microsoftonline.com/{tid}/v2.0`. Fall back to rejecting the token if `tid` is missing.
- **Status**: [x] Done — `_extract_tid()` method added; issuer validated against tenant-specific pattern

### SEC-02: Protect Agent API Key on Disk

- **Severity**: Critical
- **File**: `agent/src/config.py:330-344`
- **Problem**: API key written to `~/.config/shuttersense/agent-config.yaml` in plaintext with no file permission restrictions.
- **Fix**: Set `os.chmod(self._config_path, 0o600)` after writing. Also set parent directory to `0o700`. Add a comment recommending `SHUSAI_API_KEY` env var for production.
- **Status**: [x] Done — `save()` sets dir `0o700` and file `0o600`; docstring recommends env var

### SEC-04: Restrict CORS Methods and Headers

- **Severity**: High
- **File**: `backend/src/main.py:643-650`
- **Problem**: `allow_methods=["*"]` and `allow_headers=["*"]` are overly permissive.
- **Fix**: Replace with explicit lists: `allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]` and `allow_headers=["Content-Type", "Authorization", "X-Requested-With"]`.
- **Status**: [x] Done

### SEC-05: Remove or Restrict Debug Profile Endpoint

- **Severity**: High
- **File**: `backend/src/api/auth.py:339-378`
- **Problem**: `GET /api/auth/profile/debug` exposes OAuth provider names, subject identifiers, and login timestamps to any authenticated user.
- **Fix**: Restrict the endpoint to super admin only, or remove it entirely.
- **Status**: [x] Done — restricted to super admin via `require_super_admin` dependency

### SEC-03: Add Production Session Configuration Warning

- **Severity**: High
- **File**: `backend/src/config/session.py:53-56`, `backend/src/main.py` (startup)
- **Problem**: `SESSION_HTTPS_ONLY` defaults to `False` with no warning when running in production mode.
- **Fix**: During application startup, when `SHUSAI_ENV=production`, log a `WARNING` if `SESSION_HTTPS_ONLY` is `False`. Add similar check for empty `SESSION_SECRET_KEY`.
- **Status**: [x] Done — warnings added in `lifespan()` startup when `SHUSAI_ENV=production`

---

## Phase 2 — Before Production Deployment

Remaining high and medium items to address before the application is publicly accessible.

### SEC-06: Fix Request Size Limit for Chunked Requests

- **Severity**: High
- **File**: `backend/src/main.py:149-179`
- **Problem**: `RequestSizeLimitMiddleware` only checks `Content-Length` header, which is optional. Chunked transfers bypass the limit.
- **Fix**: Configure uvicorn/gunicorn `--limit-request-body` as a server-level backstop. Optionally add streaming body size tracking in middleware.
- **Status**: [x] Done — added streaming body size tracking via wrapped `_receive` for requests without Content-Length

### SEC-07: Remove Runtime Dev Mode Attestation Bypass

- **Severity**: High
- **File**: `agent/src/attestation.py:179-194`
- **Problem**: `SHUSAI_AGENT_DEV_MODE=true` env var disables binary attestation checks at runtime.
- **Fix**: Remove the env var bypass. Use a compile-time flag or a separate dev build configuration instead.
- **Status**: [x] Done — dev mode now determined by `sys.frozen` (script vs frozen binary); env var removed

### SEC-08: Warn on HTTP Agent Server URLs

- **Severity**: High
- **File**: `agent/src/config.py:41-49`
- **Problem**: Agent URL validation accepts `http://` without any warning. API key is sent in plaintext.
- **Fix**: Emit a prominent CLI warning when the server URL uses HTTP. In production, require HTTPS or an explicit `--allow-insecure` flag.
- **Status**: [x] Done — `validate()` logs warning when server URL starts with `http://`

### SEC-09: Sanitize Debug Logs

- **Severity**: Medium
- **File**: `backend/src/services/auth_service.py:373`
- **Problem**: `logger.debug()` logs the full `user_info` dict, which contains PII (email, name, profile URL).
- **Fix**: Replace `{user_info}` with `{list(user_info.keys())}` in all debug log statements.
- **Status**: [x] Done — replaced `{user_info}` with `{list(user_info.keys())}`

### SEC-10: Encrypt Offline Results Cache

- **Severity**: Medium
- **File**: `agent/src/cache/result_store.py:49, 75`
- **Problem**: Analysis results stored as plaintext JSON containing file paths and metadata.
- **Fix**: Apply Fernet encryption (same pattern as `credential_store.py`) when writing results. Decrypt on read/sync.
- **Status**: [x] Done — Fernet encryption added; reuses credential store master key; backwards-compatible read for pre-existing plaintext files

### SEC-12: Move Super Admin Config to Environment Variable

- **Severity**: Medium
- **File**: `backend/src/config/super_admins.py:33`
- **Problem**: SHA-256 email hashes hardcoded in source code. Requires code deployment to change admin list.
- **Fix**: Load hashes from `SHUSAI_SUPER_ADMIN_HASHES` env var (comma-separated). Keep the hardcoded set as a fallback or remove it.
- **Status**: [x] Done — loads from `SHUSAI_SUPER_ADMIN_HASHES` env var; hardcoded hash removed; `.env.example` updated

### SEC-14: Validate File Upload Size Before Reading

- **Severity**: Medium
- **File**: `backend/src/api/config.py:250-294`
- **Problem**: YAML import endpoint reads the full file into memory before any application-level size check.
- **Fix**: Check `file.size` or use a bounded read (`file.read(MAX_SIZE + 1)`) and reject if exceeded.
- **Status**: [x] Done — bounded read with 1MB limit; returns 413 if exceeded

---

## Phase 3 — Post-Deployment Hardening

Lower severity items and operational improvements.

### SEC-13: Rate Limit Token Validation

- **Severity**: Medium
- **File**: `backend/src/middleware/tenant.py`
- **Problem**: No throttling on failed token validation attempts.
- **Fix**: Track failed attempts per IP. Log suspicious patterns. Consider exponential backoff.
- **Status**: [x] Done — in-memory per-IP failure tracker with warning at 5 failures, block at 20 failures for 5 minutes; counters reset on successful validation

### SEC-11: Remove CSP unsafe-inline for Styles

- **Severity**: Medium
- **File**: `backend/src/main.py:122`
- **Problem**: `style-src 'self' 'unsafe-inline'` allows CSS injection.
- **Fix**: Investigate if Tailwind's build output requires inline styles. If not, remove `'unsafe-inline'`. If yes, consider nonce-based CSP.
- **Status**: [~] Deferred — investigation found 25+ components using inline styles (Recharts, dynamic colors, progress bars). PRD created at `docs/prd/sec-11-csp-nonce-based-styles.md` for future nonce-based CSP implementation.

### SEC-16: Pin PyInstaller Version in Build Scripts

- **Severity**: Low
- **File**: `agent/packaging/build_macos.sh:17`
- **Problem**: `pip install -q pyinstaller` without version pinning.
- **Fix**: Pin to a specific version (e.g., `pip install pyinstaller==6.x.y`).
- **Status**: [x] Done — pinned to `pyinstaller==6.18.0` in all three build scripts (macOS, Linux, Windows)

### SEC-18: Make JWT Expiration Verification Explicit

- **Severity**: Low
- **File**: `backend/src/services/token_service.py:196-200`
- **Problem**: `jwt.decode()` does not explicitly pass `options={"verify_exp": True}`. Relies on PyJWT default.
- **Fix**: Add explicit option and a code comment documenting the intent.
- **Status**: [x] Done — added `options={"verify_exp": True}` to `jwt.decode()` call

### SEC-15: Sanitize Agent CLI Error Messages

- **Severity**: Medium
- **File**: `agent/cli/run.py:161`, `agent/cli/sync_results.py:116-133`
- **Problem**: Raw exception messages printed to users, potentially leaking paths and server details.
- **Fix**: Display generic messages; log details to a local file.
- **Status**: [x] Done — replaced raw exception output with generic messages; details logged via `logger.debug()`

### SEC-17: Enable TypeScript Strict Mode

- **Severity**: Low
- **File**: `frontend/tsconfig.json:18`
- **Problem**: `"strict": false` reduces type safety.
- **Fix**: Enable incrementally. Low priority — no direct security vulnerability.
- **Status**: [x] Done — enabled 5 zero-impact strict flags (`alwaysStrict`, `noImplicitThis`, `strictFunctionTypes`, `strictBindCallApply`, `useUnknownInCatchVariables`); remaining flags (`noImplicitAny`, `strictNullChecks`, `strictPropertyInitialization`) deferred due to 180+ errors
