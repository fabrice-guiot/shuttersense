"""
Shared team config resolution for CLI commands.

Resolves team configuration using the following priority chain:
1. Fetch from server (if agent is registered and server is reachable)
2. Use valid (non-expired) cached config
3. Use expired cached config (with warning)
4. Return None (no config available)

Used by both ``test`` and ``run`` CLI commands.

Issue #108 - Remove CLI Direct Usage (Config Caching)
"""

import logging
from dataclasses import dataclass
from typing import Optional

from src.cache import TeamConfigCache
from src.cache import team_config_cache
from src.config import AgentConfig

logger = logging.getLogger(__name__)


@dataclass
class ConfigResult:
    """Result of team config resolution."""

    config: Optional[TeamConfigCache]
    source: str  # "server", "cache", "expired_cache", "unavailable"
    message: str  # Human-readable status for CLI output


def resolve_team_config() -> ConfigResult:
    """
    Resolve team configuration: server fetch > fresh cache > expired cache > None.

    Returns:
        ConfigResult with the resolved config (or None) and metadata
        about where it came from, for the caller to format output.
    """
    # Try to fetch from server if agent is registered
    server_error = None
    try:
        agent_config = AgentConfig()
        if agent_config.is_registered and agent_config.server_url:
            try:
                from src.api_client import AgentApiClient

                client = AgentApiClient(
                    server_url=agent_config.server_url,
                    api_key=agent_config.api_key,
                )
                response = client.get_team_config()

                # Cache the response
                cached = team_config_cache.make_cache(agent_config.agent_guid, response)
                team_config_cache.save(cached)

                logger.debug("Fetched and cached team config from server")
                return ConfigResult(
                    config=cached,
                    source="server",
                    message="from server",
                )

            except Exception as e:
                server_error = str(e)
                logger.debug("Server config fetch failed: %s", e)
    except Exception:
        # AgentConfig not available (not registered)
        logger.debug("Agent config not available, skipping server fetch")

    # Fall back to valid (non-expired) cached config
    cached = team_config_cache.load_valid()
    if cached is not None:
        fetched_str = cached.fetched_at.strftime("%Y-%m-%d %H:%M UTC")
        logger.debug("Using valid cached team config (fetched at %s)", cached.fetched_at)
        msg = f"from cache ({fetched_str})"
        if server_error:
            msg = f"server unavailable, using cached config ({fetched_str})"
        return ConfigResult(config=cached, source="cache", message=msg)

    # Fall back to expired cached config with warning
    cached = team_config_cache.load()
    if cached is not None:
        fetched_str = cached.fetched_at.strftime("%Y-%m-%d %H:%M UTC")
        logger.debug("Using expired cached team config (fetched at %s)", cached.fetched_at)
        return ConfigResult(
            config=cached,
            source="expired_cache",
            message=f"server unavailable, using cached config from {fetched_str} (may be outdated)",
        )

    # No config available
    logger.debug("No team config available (no server, no cache)")
    msg = "no config available"
    if server_error:
        msg = f"server unavailable ({server_error}), no cached config"
    return ConfigResult(config=None, source="unavailable", message=msg)
