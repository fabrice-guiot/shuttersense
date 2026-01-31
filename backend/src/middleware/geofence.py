"""
GeoIP-based geofencing middleware for ShutterSense.

Restricts API access to requests originating from configured allowed countries
using MaxMind GeoLite2-Country database lookups.

When enabled:
- Requests from allowed countries proceed normally
- Requests from disallowed countries receive 403 Forbidden
- Private/loopback IPs always pass (development, internal services)
- /health endpoint is always exempt (health probes)
- Unknown IPs are blocked by default (configurable via SHUSAI_GEOIP_FAIL_OPEN)

When disabled (no SHUSAI_GEOIP_DB_PATH configured):
- Middleware is not registered; zero runtime impact
"""

import ipaddress
from typing import Set

import geoip2.database
import geoip2.errors
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.src.utils.logging_config import get_logger

logger = get_logger("api")

# Paths exempt from geofencing (health probes must always work)
EXEMPT_PATHS: Set[str] = {"/health"}


class GeoFenceMiddleware(BaseHTTPMiddleware):
    """
    Middleware that blocks requests from countries not in the allowlist.

    Uses MaxMind GeoLite2-Country database for IP-to-country resolution.
    Private/loopback IPs are always allowed through.

    Args:
        app: ASGI application
        reader: Opened geoip2.database.Reader instance
        allowed_countries: Set of uppercase ISO 3166-1 alpha-2 country codes
        fail_open: If True, allow requests when GeoIP lookup returns no country
    """

    def __init__(
        self,
        app,
        reader: geoip2.database.Reader,
        allowed_countries: Set[str],
        fail_open: bool = False,
    ):
        super().__init__(app)
        self.reader = reader
        self.allowed_countries = allowed_countries
        self.fail_open = fail_open

    async def dispatch(self, request: Request, call_next):
        # Skip WebSocket connections
        if request.scope.get("type") == "websocket":
            return await call_next(request)

        # Exempt paths (health probes)
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        # Extract client IP
        client_ip = self._get_client_ip(request)

        # Allow private/loopback IPs (development, internal services)
        if self._is_private_ip(client_ip):
            return await call_next(request)

        # GeoIP lookup
        country_code = self._lookup_country(client_ip)

        if country_code is None:
            if self.fail_open:
                return await call_next(request)
            logger.warning(
                "GeoFence: Blocked request from unknown country (IP: %s, path: %s)",
                client_ip,
                request.url.path,
            )
            return self._forbidden_response()

        # Check against allowlist
        if country_code in self.allowed_countries:
            return await call_next(request)

        logger.warning(
            "GeoFence: Blocked request from %s (IP: %s, path: %s)",
            country_code,
            client_ip,
            request.url.path,
        )
        return self._forbidden_response()

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """
        Extract client IP from the request.

        Uses request.client.host which is resolved by Uvicorn's
        ProxyHeadersMiddleware when --proxy-headers and
        --forwarded-allow-ips are configured.

        Args:
            request: Starlette Request object

        Returns:
            Client IP address string
        """
        if request.client:
            return request.client.host
        return "0.0.0.0"

    @staticmethod
    def _is_private_ip(ip_str: str) -> bool:
        """
        Check if an IP address is private, loopback, or link-local.

        Handles both IPv4 and IPv6 addresses.

        Args:
            ip_str: IP address string

        Returns:
            True if the IP is non-routable
        """
        try:
            addr = ipaddress.ip_address(ip_str)
            return addr.is_private or addr.is_loopback or addr.is_link_local
        except ValueError:
            return False

    def _lookup_country(self, ip_str: str) -> str | None:
        """
        Look up the country code for an IP address using the GeoIP database.

        Args:
            ip_str: IP address string

        Returns:
            ISO 3166-1 alpha-2 country code (uppercase), or None if unknown
        """
        try:
            response = self.reader.country(ip_str)
            country = response.country.iso_code
            return country.upper() if country else None
        except geoip2.errors.AddressNotFoundError:
            return None
        except Exception as e:
            logger.error("GeoFence: GeoIP lookup error for %s: %s", ip_str, e)
            return None

    @staticmethod
    def _forbidden_response() -> JSONResponse:
        """Return a 403 response for blocked requests."""
        return JSONResponse(
            status_code=403,
            content={"detail": "Access denied based on geographic restrictions"},
        )
