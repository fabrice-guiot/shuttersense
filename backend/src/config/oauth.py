"""
OAuth 2.0 configuration for Google and Microsoft providers.

Uses Authlib for OAuth 2.0 + PKCE authentication flow.
Configuration is loaded from environment variables.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class OAuthSettings(BaseSettings):
    """
    OAuth provider configuration loaded from environment variables.

    Environment Variables:
        GOOGLE_CLIENT_ID: Google OAuth client ID
        GOOGLE_CLIENT_SECRET: Google OAuth client secret
        MICROSOFT_CLIENT_ID: Microsoft/Azure AD client ID
        MICROSOFT_CLIENT_SECRET: Microsoft/Azure AD client secret
        OAUTH_REDIRECT_BASE_URL: Base URL for OAuth callbacks (e.g., http://localhost:8000)
    """

    # Google OAuth
    google_client_id: Optional[str] = Field(default=None, validation_alias="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(default=None, validation_alias="GOOGLE_CLIENT_SECRET")

    # Microsoft OAuth
    microsoft_client_id: Optional[str] = Field(default=None, validation_alias="MICROSOFT_CLIENT_ID")
    microsoft_client_secret: Optional[str] = Field(default=None, validation_alias="MICROSOFT_CLIENT_SECRET")

    # Redirect configuration
    oauth_redirect_base_url: str = Field(
        default="http://localhost:8000",
        validation_alias="OAUTH_REDIRECT_BASE_URL"
    )

    # OpenID Connect discovery URLs
    google_discovery_url: str = "https://accounts.google.com/.well-known/openid-configuration"
    microsoft_discovery_url: str = "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration"

    # OAuth scopes (User.Read needed for Microsoft Graph API photo access)
    oauth_scopes: list[str] = ["openid", "email", "profile", "User.Read"]

    # PKCE configuration
    code_challenge_method: str = "S256"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def google_enabled(self) -> bool:
        """Check if Google OAuth is configured."""
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def microsoft_enabled(self) -> bool:
        """Check if Microsoft OAuth is configured."""
        return bool(self.microsoft_client_id and self.microsoft_client_secret)

    @property
    def google_redirect_uri(self) -> str:
        """Get Google OAuth callback URL."""
        return f"{self.oauth_redirect_base_url}/api/auth/callback/google"

    @property
    def microsoft_redirect_uri(self) -> str:
        """Get Microsoft OAuth callback URL."""
        return f"{self.oauth_redirect_base_url}/api/auth/callback/microsoft"


@lru_cache()
def get_oauth_settings() -> OAuthSettings:
    """
    Get cached OAuth settings instance.

    Returns:
        OAuthSettings: Configured OAuth settings from environment
    """
    return OAuthSettings()
