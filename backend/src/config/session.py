"""
Session management configuration for photo-admin.

Uses Starlette's SessionMiddleware with signed cookies.
Configuration is loaded from environment variables.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class SessionSettings(BaseSettings):
    """
    Session configuration loaded from environment variables.

    Environment Variables:
        SESSION_SECRET_KEY: Secret key for signing session cookies (required)
        SESSION_MAX_AGE: Session duration in seconds (default: 24 hours)
        SESSION_COOKIE_NAME: Name of the session cookie
        SESSION_SAME_SITE: SameSite cookie attribute (lax, strict, none)
        SESSION_HTTPS_ONLY: Whether to require HTTPS for cookies
    """

    # Secret key for signing cookies (REQUIRED)
    session_secret_key: str = Field(
        default="",
        validation_alias="SESSION_SECRET_KEY",
        description="Secret key for signing session cookies. Must be at least 32 bytes."
    )

    # Session duration (24 hours default, sliding)
    session_max_age: int = Field(
        default=24 * 60 * 60,  # 24 hours in seconds
        validation_alias="SESSION_MAX_AGE",
        ge=60,  # Minimum 1 minute
        le=30 * 24 * 60 * 60,  # Maximum 30 days
    )

    # Cookie configuration
    session_cookie_name: str = Field(
        default="photo_admin_session",
        validation_alias="SESSION_COOKIE_NAME"
    )

    session_same_site: Literal["lax", "strict", "none"] = Field(
        default="lax",
        validation_alias="SESSION_SAME_SITE"
    )

    session_https_only: bool = Field(
        default=False,  # Set to True in production
        validation_alias="SESSION_HTTPS_ONLY"
    )

    session_path: str = Field(
        default="/",
        validation_alias="SESSION_PATH"
    )

    class Config:
        env_file = ".env"
        extra = "ignore"

    @field_validator("session_secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate that secret key is sufficiently long."""
        if v and len(v) < 32:
            raise ValueError("SESSION_SECRET_KEY must be at least 32 characters")
        return v

    @property
    def is_configured(self) -> bool:
        """Check if session is properly configured."""
        return bool(self.session_secret_key)


@lru_cache()
def get_session_settings() -> SessionSettings:
    """
    Get cached session settings instance.

    Returns:
        SessionSettings: Configured session settings from environment
    """
    return SessionSettings()


def generate_secret_key() -> str:
    """
    Generate a cryptographically secure secret key.

    Utility function for administrators to generate new secret keys.

    Returns:
        URL-safe base64-encoded 32-byte random key

    Example:
        >>> key = generate_secret_key()
        >>> len(key) >= 32
        True
    """
    import secrets
    return secrets.token_urlsafe(32)
