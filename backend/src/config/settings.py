"""
Application settings configuration for photo-admin.

Centralized settings loaded from environment variables.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Environment Variables:
        JWT_SECRET_KEY: Secret key for signing JWT API tokens (required for API tokens)
        JWT_TOKEN_EXPIRY_DAYS: Default token expiry in days (default: 90)
    """

    # JWT settings for API tokens
    jwt_secret_key: str = Field(
        default="",
        validation_alias="JWT_SECRET_KEY",
        description="Secret key for signing JWT API tokens. Must be at least 32 bytes."
    )

    jwt_token_expiry_days: int = Field(
        default=90,
        validation_alias="JWT_TOKEN_EXPIRY_DAYS",
        ge=1,
        le=365,
    )

    class Config:
        env_file = ".env"
        extra = "ignore"

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        """Validate that JWT secret key is sufficiently long."""
        if v and len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return v

    @property
    def jwt_configured(self) -> bool:
        """Check if JWT is properly configured."""
        return bool(self.jwt_secret_key)


@lru_cache()
def get_settings() -> AppSettings:
    """
    Get cached application settings instance.

    Returns:
        AppSettings: Configured application settings from environment
    """
    return AppSettings()
