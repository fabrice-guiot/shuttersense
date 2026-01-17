# Quickstart: Teams/Tenants and User Management with Authentication

**Feature**: 019-user-tenancy
**Date**: 2026-01-15

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- PostgreSQL 12+ (production) or SQLite (development/testing)
- Google Cloud Console account (for OAuth)
- Azure Portal account (for Microsoft OAuth, optional)

## Setup Steps

### 1. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

New dependencies for this feature:
```text
authlib>=1.6.0        # OAuth 2.0 + PKCE
itsdangerous>=2.2.0   # Session signing
python-jose[cryptography]>=3.3.0  # JWT handling
```

### 2. Configure OAuth Providers

#### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Navigate to **APIs & Services > Credentials**
4. Click **Create Credentials > OAuth 2.0 Client IDs**
5. Configure consent screen if prompted
6. Set **Application type** to "Web application"
7. Add authorized redirect URI: `http://localhost:8000/api/auth/callback/google`
8. Note the **Client ID** and **Client Secret**

#### Microsoft OAuth Setup (Optional)

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Azure Active Directory > App registrations**
3. Click **New registration**
4. Set redirect URI: `http://localhost:8000/api/auth/callback/microsoft`
5. Note the **Application (client) ID**
6. Create a **Client secret** under "Certificates & secrets"

### 3. Configure Environment Variables

Create/update `.env` in the backend directory:

```bash
# Existing variables...
PHOTO_ADMIN_DB_URL=postgresql://user:pass@localhost/photo_admin
PHOTO_ADMIN_MASTER_KEY=your-32-byte-key

# New OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret

# Session Configuration
SESSION_SECRET_KEY=your-random-32-byte-session-secret

# JWT Configuration (for API tokens)
JWT_SECRET_KEY=your-random-32-byte-jwt-secret
JWT_ALGORITHM=HS256
API_TOKEN_DEFAULT_EXPIRY_DAYS=90

# Optional: Super Admin Configuration
# SUPER_ADMIN_EMAIL_HASHES=hash1,hash2
```

Generate secure secrets:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Run Database Migrations

```bash
cd backend
alembic upgrade head
```

This will create:
- `teams` table
- `users` table
- `api_tokens` table
- Add `team_id` column to all existing tables

### 5. Seed First Team

Run the seeding script to create the initial team and admin user:

```bash
python -m backend.src.scripts.seed_first_team \
  --team-name "My Photography Studio" \
  --admin-email "admin@example.com"
```

Output:
```
Created team: ten_01hgw2bbg0000000000000001 (My Photography Studio)
Created user: usr_01hgw2bbg0000000000000002 (admin@example.com) - Status: pending
```

The admin user is created with `pending` status. They will become `active` after first OAuth login.

### 6. Start the Application

**Backend:**
```bash
cd backend
uvicorn backend.src.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### 7. Login Flow

1. Navigate to `http://localhost:5173` (frontend dev server)
2. You'll be redirected to `/login`
3. Click "Login with Google" or "Login with Microsoft"
4. Complete OAuth flow with your pre-provisioned email
5. On success, redirected to dashboard with profile in top header

## Development Workflow

### Running Tests

**Backend:**
```bash
cd backend
pytest tests/ -v

# Run specific test files
pytest tests/unit/test_auth_service.py -v
pytest tests/integration/test_oauth_flow.py -v
```

**Frontend:**
```bash
cd frontend
npm run test

# With coverage
npm run test:coverage
```

### Testing OAuth Locally

For local development, you can use the `/api/auth/debug` endpoint (only available in development mode):

```bash
# Create a test session without OAuth
curl -X POST http://localhost:8000/api/auth/debug/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com"}'
```

### Adding Super Admins

1. Generate email hash:
```python
import hashlib
email = "superadmin@example.com".lower().strip()
print(hashlib.sha256(email.encode()).hexdigest())
```

2. Add hash to `backend/src/config/super_admins.py`:
```python
SUPER_ADMIN_EMAIL_HASHES = {
    "generated-hash-here",
}
```

3. Restart backend

### Creating API Tokens

Via UI:
1. Login to application
2. Navigate to Settings > API Tokens
3. Click "Generate Token"
4. Copy the token immediately (shown only once)

Via API:
```bash
curl -X POST http://localhost:8000/api/tokens \
  -H "Cookie: photo_admin_session=your-session-cookie" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Token", "expires_in_days": 30}'
```

### Using API Tokens

```bash
curl http://localhost:8000/api/collections \
  -H "Authorization: Bearer your-jwt-token"
```

## Common Issues

### "User not found" on OAuth callback

- Ensure the user is pre-provisioned with matching email
- Check email case sensitivity (emails are normalized to lowercase)
- Verify team is active

### "Team inactive" error

- A super admin needs to reactivate the team
- Use seed script to create a new team

### CSRF/State validation errors

- Clear browser cookies and try again
- Check `SESSION_SECRET_KEY` hasn't changed
- Verify redirect URI matches exactly

### Session cookie not set

- Check `https_only` setting (set to `false` for localhost)
- Verify CORS configuration allows credentials

## File Structure Reference

```text
backend/
├── src/
│   ├── models/
│   │   ├── team.py           # Team entity
│   │   ├── user.py           # User entity
│   │   └── api_token.py      # ApiToken entity
│   ├── services/
│   │   ├── auth_service.py   # OAuth + session
│   │   ├── user_service.py   # User CRUD
│   │   ├── team_service.py   # Team CRUD
│   │   └── token_service.py  # API token mgmt
│   ├── api/
│   │   ├── auth.py           # /auth/* endpoints
│   │   ├── users.py          # /api/users/*
│   │   ├── tokens.py         # /api/tokens/*
│   │   └── admin/
│   │       └── teams.py      # /api/admin/teams/*
│   └── config/
│       └── super_admins.py   # Super admin hashes

frontend/
├── src/
│   ├── contexts/
│   │   └── AuthContext.tsx   # Auth state
│   ├── components/
│   │   ├── auth/
│   │   │   ├── OAuthButton.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   └── settings/
│   │       ├── TokensTab.tsx   # API Token management
│   │       └── TeamsTab.tsx    # Team management (super admin)
│   ├── pages/
│   │   ├── LoginPage.tsx
│   │   ├── ProfilePage.tsx
│   │   └── TeamPage.tsx        # User management
│   └── hooks/
│       ├── useAuth.ts
│       ├── useUsers.ts
│       ├── useTeams.ts
│       └── useTokens.ts
```

## Next Steps

After basic setup:

1. **Invite team members**: Settings > Users > Invite User
2. **Configure team settings**: Settings > Teams (super admin)
3. **Generate API tokens**: Settings > API Tokens
4. **Test tenant isolation**: Create data as different team users

For production deployment, see the main deployment documentation.
