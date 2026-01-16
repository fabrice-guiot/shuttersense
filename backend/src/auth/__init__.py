"""
Authentication module for photo-admin backend.

This module provides OAuth 2.0 authentication with PKCE support
for Google and Microsoft providers using Authlib.

Components:
- oauth_client: OAuth provider configuration and client setup
- AuthService: Business logic for authentication flows
"""

from backend.src.auth.oauth_client import (
    get_oauth_client,
    get_google_client,
    get_microsoft_client,
)

__all__ = [
    "get_oauth_client",
    "get_google_client",
    "get_microsoft_client",
]
