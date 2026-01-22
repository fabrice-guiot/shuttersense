"""
Application settings configuration for ShutterSense.

Centralized settings loaded from environment variables.
"""

from functools import lru_cache
from typing import List, Optional, Set

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Environment Variables:
        JWT_SECRET_KEY: Secret key for signing JWT API tokens (required for API tokens)
        JWT_TOKEN_EXPIRY_DAYS: Default token expiry in days (default: 90)
        INMEMORY_JOB_TYPES: Comma-separated list of tool types to run in-memory (default: empty)
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

    # Job execution settings
    # By default, all jobs are persisted to DB for agent execution.
    # Only tool types listed here will use in-memory queue for server-side execution.
    # Example: "photostats,photo_pairing" to run these tools in-memory on server
    inmemory_job_types: str = Field(
        default="",
        validation_alias="INMEMORY_JOB_TYPES",
        description="Comma-separated list of tool types to run in-memory on server (default: empty = all jobs go to agents)"
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

    @property
    def inmemory_job_types_set(self) -> Set[str]:
        """
        Get the set of tool types allowed to run in-memory.

        Returns:
            Set of tool type strings (e.g., {"photostats", "photo_pairing"})
        """
        if not self.inmemory_job_types:
            return set()
        return {t.strip().lower() for t in self.inmemory_job_types.split(",") if t.strip()}

    def is_inmemory_job_type(self, tool_type: str) -> bool:
        """
        Check if a tool type should run in-memory on the server.

        Args:
            tool_type: Tool type string (e.g., "photostats")

        Returns:
            True if this tool type is configured to run in-memory
        """
        return tool_type.lower() in self.inmemory_job_types_set


@lru_cache()
def get_settings() -> AppSettings:
    """
    Get cached application settings instance.

    Returns:
        AppSettings: Configured application settings from environment
    """
    return AppSettings()
