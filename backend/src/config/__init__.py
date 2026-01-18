"""
Configuration module for ShutterSense backend.

Provides centralized configuration for:
- OAuth providers (Google, Microsoft)
- Session management
- Super admin authorization
"""

from backend.src.config.oauth import OAuthSettings, get_oauth_settings
from backend.src.config.session import SessionSettings, get_session_settings
from backend.src.config.super_admins import is_super_admin, SUPER_ADMIN_EMAIL_HASHES

__all__ = [
    "OAuthSettings",
    "get_oauth_settings",
    "SessionSettings",
    "get_session_settings",
    "is_super_admin",
    "SUPER_ADMIN_EMAIL_HASHES",
]
