# Research: Teams/Tenants and User Management with Authentication

**Feature**: 019-user-tenancy
**Date**: 2026-01-15
**Status**: Complete

## Overview

This document captures research decisions for implementing OAuth 2.0 authentication, multi-tenancy, and user management in photo-admin.

---

## Decision 1: OAuth Library Selection

### Decision: Authlib

**Rationale**:
- RFC-compliant OAuth 1.0, OAuth 2.0, and OpenID Connect implementation
- Native PKCE support with S256 code challenge method
- Works seamlessly with FastAPI/Starlette through `authlib.integrations.starlette_client`
- Supports both Google and Microsoft OAuth providers out of the box
- Active maintenance (v1.6.x current)
- Comprehensive JWT/JWK/JWS support for API token generation
- Used by 26%+ of REST API projects on GitHub (2024 data)

**Alternatives Considered**:

| Library | Why Rejected |
|---------|--------------|
| `httpx-oauth` | Less comprehensive than Authlib, fewer provider integrations |
| `fastapi-users` | Too opinionated, includes full user management we don't need (we have pre-provisioning model) |
| `python-social-auth` | Django-focused, not ideal for FastAPI |
| `fastapi-azure-auth` | Microsoft-only, doesn't support Google |

**Dependencies to Add**:
```text
authlib>=1.6.0
itsdangerous>=2.2.0  # Session signing (Authlib dependency)
python-jose[cryptography]>=3.3.0  # JWT handling
```

---

## Decision 2: Session Management Strategy

### Decision: HTTP-only Signed Cookies with Starlette SessionMiddleware

**Rationale**:
- Industry standard approach for web applications
- Simpler than server-side session stores (no Redis required initially)
- Authlib's Starlette integration requires session middleware for OAuth state management
- Signed cookies prevent tampering (using `itsdangerous`)
- HTTP-only prevents XSS token theft

**Cookie Configuration**:
```python
SessionMiddleware(
    secret_key=settings.SESSION_SECRET_KEY,
    session_cookie="photo_admin_session",
    max_age=24 * 60 * 60,  # 24 hours
    same_site="lax",       # CSRF protection
    https_only=True,       # Production: always True
    path="/",
)
```

**Session Data Structure**:
```python
{
    "user_id": int,           # Internal DB ID
    "user_guid": str,         # usr_... GUID for API responses
    "team_id": int,           # Internal DB ID
    "team_guid": str,         # ten_... GUID
    "email": str,
    "display_name": str,
    "picture_url": str | None,
    "is_super_admin": bool,
    "session_created_at": datetime,
    "last_activity_at": datetime,  # For sliding expiration
}
```

**Alternatives Considered**:

| Approach | Why Rejected |
|----------|--------------|
| Redis session store | Adds infrastructure complexity; can be added later for horizontal scaling |
| JWT-only (stateless) | Cannot revoke sessions immediately; harder to implement sliding expiration |
| Database session store | Adds database load; overkill for initial deployment |

---

## Decision 3: PKCE Implementation

### Decision: S256 Code Challenge Method (Mandatory)

**Rationale**:
- Plain method is deprecated and insecure
- S256 provides cryptographic protection of authorization code
- Required by OAuth 2.1 specification
- Authlib handles PKCE automatically when configured

**Flow**:
1. Client initiates auth: Generate code_verifier (43-128 chars), compute SHA256 → code_challenge
2. Server stores code_verifier in session (10-minute TTL)
3. User redirected to OAuth provider with code_challenge
4. Provider returns authorization code
5. Server exchanges code + code_verifier for tokens
6. Provider validates SHA256(code_verifier) == code_challenge

**Configuration**:
```python
oauth.register(
    name='google',
    client_kwargs={
        'scope': 'openid email profile',
        'code_challenge_method': 'S256',
    }
)
```

---

## Decision 4: Google OAuth Configuration

### Decision: OpenID Connect with Discovery

**Rationale**:
- Google's OpenID Connect provides standardized user info
- Discovery endpoint auto-configures all OAuth URLs
- Includes email verification status
- Profile picture URL included in ID token

**Configuration**:
```python
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    client_kwargs={
        'scope': 'openid email profile',
        'code_challenge_method': 'S256',
    }
)
```

**Required Scopes**:
- `openid` - Required for OpenID Connect
- `email` - User's email address
- `profile` - Name and profile picture

**Google Cloud Console Setup**:
1. Create OAuth 2.0 credentials at console.cloud.google.com
2. Set authorized redirect URI: `{BASE_URL}/auth/google/callback`
3. Note: No domain verification needed for development

---

## Decision 5: Microsoft OAuth Configuration

### Decision: Multi-tenant Azure AD with OpenID Connect

**Rationale**:
- Supports both personal Microsoft accounts and work/school accounts
- Multi-tenant (`common` endpoint) allows any Microsoft user
- Can be restricted to specific tenant later if needed

**Configuration**:
```python
oauth.register(
    name='microsoft',
    server_metadata_url='https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration',
    client_id=settings.MICROSOFT_CLIENT_ID,
    client_secret=settings.MICROSOFT_CLIENT_SECRET,
    client_kwargs={
        'scope': 'openid email profile',
        'code_challenge_method': 'S256',
    }
)
```

**Tenant Options**:
- `common` - Any Microsoft account (personal + work/school)
- `organizations` - Work/school accounts only
- `{tenant-id}` - Single organization only

**Azure Portal Setup**:
1. Register app at portal.azure.com > App registrations
2. Set redirect URI: `{BASE_URL}/auth/microsoft/callback`
3. Add API permissions: `User.Read` (delegated)
4. Note: Client secret required for confidential clients

---

## Decision 6: Tenant Isolation Strategy

### Decision: Service Layer Filtering (Not Database RLS)

**Rationale**:
- Simpler to implement and debug
- Explicit filtering in Python code is auditable
- Works with SQLite for tests (RLS is PostgreSQL-only)
- Can add RLS as defense-in-depth later
- Consistent with existing service patterns in photo-admin

**Implementation Pattern**:
```python
class TenantContext:
    team_id: int
    user_id: int
    is_super_admin: bool

def get_tenant_context(request: Request) -> TenantContext:
    """FastAPI dependency that extracts tenant from session."""
    session = request.session
    return TenantContext(
        team_id=session['team_id'],
        user_id=session['user_id'],
        is_super_admin=session.get('is_super_admin', False),
    )

class CollectionService:
    def list(self, ctx: TenantContext) -> list[Collection]:
        return self.db.query(Collection).filter(
            Collection.team_id == ctx.team_id
        ).all()

    def get_by_guid(self, ctx: TenantContext, guid: str) -> Collection | None:
        collection = self.db.query(Collection).filter(
            Collection.uuid == parse_guid(guid)
        ).first()
        # Return None (404) if wrong team - prevents enumeration
        if collection and collection.team_id != ctx.team_id:
            return None
        return collection
```

**Cross-Team Access**:
- Always return 404 (not 403) to prevent GUID enumeration
- Super admin endpoints use separate routes under `/api/admin/`

**Alternatives Considered**:

| Approach | Why Rejected |
|----------|--------------|
| PostgreSQL RLS | SQLite incompatible (breaks tests); can be added as defense-in-depth later |
| Global query filter | Implicit; harder to audit and debug |
| Separate databases | Overkill for initial deployment |

---

## Decision 7: API Token Format

### Decision: JWT with HS256 Signing

**Rationale**:
- Stateless validation (no database lookup required for validation)
- Standard format understood by all clients
- Can include team_id claim for tenant isolation
- HS256 is simpler than RS256 and sufficient for same-origin tokens

**Token Structure**:
```json
{
  "sub": "usr_01hgw2bbg...",      // User GUID
  "team_id": "ten_01hgw2bbg...",  // Team GUID
  "jti": "tok_01hgw2bbg...",      // Token GUID (for revocation)
  "iat": 1705312345,              // Issued at
  "exp": 1713088345,              // Expiration (90 days default)
  "scopes": ["*"]                 // Future: granular permissions
}
```

**Storage**:
- Token shown to user once at creation (copy-to-clipboard UI)
- SHA-256 hash stored in database (for revocation lookup)
- First 8 characters stored as prefix (for identification in UI)

**Validation Flow**:
1. Extract token from `Authorization: Bearer {token}` header
2. Validate JWT signature and expiration
3. Check `jti` hash against database (not revoked, active)
4. Inject TenantContext with team_id from token

---

## Decision 8: Super Admin Authorization

### Decision: Hashed Email List in Code

**Rationale**:
- No additional database tables needed
- Changes require deployment (acceptable security measure)
- SHA-256 hashing prevents email disclosure if code is leaked
- Simple to implement and audit

**Implementation**:
```python
# backend/src/config/super_admins.py
import hashlib

SUPER_ADMIN_EMAIL_HASHES = {
    # SHA-256 hash of lowercase email
    # hashlib.sha256("admin@example.com".encode()).hexdigest()
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}

def is_super_admin(email: str) -> bool:
    """Check if email belongs to a super admin."""
    normalized = email.lower().strip()
    email_hash = hashlib.sha256(normalized.encode()).hexdigest()
    return email_hash in SUPER_ADMIN_EMAIL_HASHES
```

**Alternatives Considered**:

| Approach | Why Rejected |
|----------|--------------|
| Database admin flag | Requires migration and management UI |
| Environment variable | Harder to manage multiple admins |
| Separate admin service | Overkill for initial deployment |

---

## Decision 9: CSRF Protection

### Decision: State Parameter + SameSite Cookies

**Rationale**:
- Authlib handles OAuth state parameter automatically
- `SameSite=Lax` cookies provide CSRF protection for most cases
- No additional CSRF token middleware needed for OAuth flow
- State-changing API endpoints will use session cookie validation

**Flow**:
1. Authlib generates cryptographic state parameter before OAuth redirect
2. State stored in session (signed cookie)
3. On callback, state validated against session
4. If mismatch, auth fails with 400 Bad Request

**Additional Protection**:
- All state-changing endpoints require valid session cookie
- Session cookie has `SameSite=Lax` (prevents cross-origin POSTs)
- Rate limiting on login endpoints (10 failed attempts/IP/hour)

---

## Decision 10: Frontend Authentication State

### Decision: React Context with Session Refresh

**Rationale**:
- Centralized auth state management
- Works with existing React patterns in photo-admin
- Session refresh on app mount ensures fresh state
- Protected routes can check context synchronously

**Implementation**:
```typescript
interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isSuperAdmin: boolean;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // Fetch /auth/me on mount to get current session
  // Redirect to /login if no session
}
```

**Session Refresh**:
- `GET /auth/me` returns current user info or 401
- Called on app mount and after navigation
- 401 response triggers redirect to login page

---

## Security Checklist

Based on research, the implementation must include:

- [x] S256 PKCE for all OAuth flows
- [x] HTTP-only, Secure, SameSite=Lax session cookies
- [x] OAuth state parameter validation (Authlib automatic)
- [x] Rate limiting on failed login attempts
- [x] 404 (not 403) for cross-team resource access
- [x] SHA-256 hashing for stored API tokens
- [x] Super admin actions logged for audit
- [x] Session invalidation on user/team deactivation

---

## Environment Variables Required

```bash
# OAuth Providers
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=

# Session
SESSION_SECRET_KEY=  # 32+ bytes, cryptographically random

# JWT (API Tokens)
JWT_SECRET_KEY=      # 32+ bytes, different from session secret
JWT_ALGORITHM=HS256
API_TOKEN_DEFAULT_EXPIRY_DAYS=90

# Security
FAILED_LOGIN_RATE_LIMIT=10  # Per IP per hour
```

---

## References

- [Authlib Documentation](https://docs.authlib.org/en/latest/client/fastapi.html)
- [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect)
- [Microsoft Identity Platform](https://learn.microsoft.com/en-us/entra/identity-platform/)
- [OAuth 2.1 Specification](https://oauth.net/2.1/)
- [PKCE RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)
