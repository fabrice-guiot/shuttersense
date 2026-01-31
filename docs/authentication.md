# Authentication Guide

ShutterSense uses OAuth 2.0 for user authentication and API tokens for agent and programmatic access.

## Authentication Methods

| Method | Use Case | Mechanism |
|--------|----------|-----------|
| OAuth 2.0 (Google) | Web UI login | Session cookies |
| OAuth 2.0 (Microsoft) | Web UI login | Session cookies |
| API Token (Bearer) | Agent registration, programmatic access | `Authorization: Bearer <token>` |

## OAuth 2.0 Setup

### Google Provider

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Navigate to **APIs & Services > Credentials**
4. Create an **OAuth 2.0 Client ID** (Web application type)
5. Configure authorized redirect URIs:
   - Development: `http://localhost:8000/api/auth/google/callback`
   - Production: `https://your-domain.com/api/auth/google/callback`
6. Set environment variables:
   ```bash
   export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
   export GOOGLE_CLIENT_SECRET="your-client-secret"
   ```

### Microsoft Provider

1. Go to [Azure Portal](https://portal.azure.com/) > **App registrations**
2. Register a new application
3. Under **Authentication**, add redirect URIs:
   - Development: `http://localhost:8000/api/auth/microsoft/callback`
   - Production: `https://your-domain.com/api/auth/microsoft/callback`
4. Under **Certificates & secrets**, create a new client secret
5. Set environment variables:
   ```bash
   export MICROSOFT_CLIENT_ID="your-application-client-id"
   export MICROSOFT_CLIENT_SECRET="your-client-secret"
   ```

## OAuth PKCE Flow

ShutterSense uses the Authorization Code flow with PKCE (Proof Key for Code Exchange) for enhanced security:

1. User clicks "Sign in with Google" (or Microsoft) on `/login`
2. Backend generates a PKCE code verifier and challenge
3. User is redirected to the OAuth provider's consent screen
4. After consent, provider redirects back with an authorization code
5. Backend exchanges the code for tokens using the PKCE verifier
6. Backend creates or updates the User record
7. A session cookie is set and the user is redirected to the SPA

## Session-Based Authentication

After OAuth login, authentication is maintained via session cookies.

### Session Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SESSION_SECRET_KEY` | Secret for signing session cookies (min 32 chars, required) | - |
| `SESSION_MAX_AGE` | Session duration in seconds | `86400` (24 hours) |
| `SESSION_COOKIE_NAME` | Cookie name | `shusai_session` |
| `SESSION_SAME_SITE` | SameSite attribute (`lax`, `strict`, `none`) | `lax` |
| `SESSION_HTTPS_ONLY` | Require HTTPS for cookies | `false` |
| `SESSION_PATH` | Cookie path | `/` |

Generate a session secret:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Production Recommendations

- Set `SESSION_HTTPS_ONLY=true` to require HTTPS
- Set `SESSION_SAME_SITE=lax` (default) for CSRF protection
- Use a strong, unique `SESSION_SECRET_KEY` (min 32 characters)

## API Token Management

API tokens provide authentication for agents and programmatic access.

### Creating Tokens

Tokens are created through the web UI:

1. Navigate to **Profile** (click your avatar)
2. Go to the **API Tokens** section
3. Click **Generate Token**
4. Copy the token immediately (it is only shown once)

### Token Properties

| Property | Description |
|----------|-------------|
| Format | JWT signed with `JWT_SECRET_KEY` |
| Expiry | Configurable (default 90 days, max 365 days) |
| Scope | Scoped to the user's team |
| Limitations | Cannot access super admin endpoints (`/api/admin/*`) |

### Using Tokens

Include the token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer tok_xxxxx..." https://your-domain.com/api/collections
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_SECRET_KEY` | Secret for signing JWT tokens (min 32 chars, required) | - |
| `JWT_TOKEN_EXPIRY_DAYS` | Token expiry in days | `90` |

## Frontend Auth Flow

### Key Components

- **AuthContext** (`src/contexts/AuthContext.tsx`) - Provides `useAuth()` hook with `user`, `isAuthenticated`, `logout()`
- **ProtectedRoute** (`src/components/auth/ProtectedRoute.tsx`) - Wraps routes that require authentication
- **AuthRedirectHandler** (`src/components/auth/AuthRedirectHandler.tsx`) - Handles OAuth callback redirects
- **LoginPage** (`src/pages/LoginPage.tsx`) - OAuth provider selection

### Usage

```typescript
import { useAuth } from '@/contexts/AuthContext'

function MyComponent() {
  const { user, isAuthenticated, logout } = useAuth()

  if (!isAuthenticated) return null

  return <div>Hello, {user.display_name}</div>
}
```

## Security Features

### Rate Limiting

- Login endpoints are rate-limited to prevent brute force attacks
- Global rate limiting via slowapi middleware
- Configurable per-endpoint limits

### CSRF Protection

- Session cookies use `SameSite=lax` by default
- State parameter validation in OAuth flow
- PKCE prevents authorization code interception

### Public Endpoints

The following endpoints do NOT require authentication:

- `GET /health` - Health check
- `GET /api/version` - Version information
- `GET /api/auth/*` - OAuth login and callback URLs
- `POST /api/agent/v1/register` - Agent registration (uses one-time tokens)

### Super Admin

Super admin access is configured via environment variable or database flag. Super admin users can access:

- `GET/POST/DELETE /api/admin/teams` - Team management
- `GET/POST/DELETE /api/admin/release-manifests` - Agent release management

## Troubleshooting

### "Session expired" errors

- Check `SESSION_MAX_AGE` value (default 24 hours)
- Verify `SESSION_SECRET_KEY` hasn't changed (changing it invalidates all sessions)

### OAuth redirect errors

- Verify redirect URIs match exactly (including trailing slashes)
- Check that the OAuth client ID and secret are correct
- Ensure the OAuth provider's consent screen is configured

### API token rejected

- Tokens expire after `JWT_TOKEN_EXPIRY_DAYS` (default 90 days)
- Verify `JWT_SECRET_KEY` hasn't changed
- Check that the token hasn't been revoked in the web UI
