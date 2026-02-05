"""
Client IP extraction utility.

Provides a centralized function for extracting the real client IP address
from incoming requests, accounting for reverse proxies (e.g., nginx).

Note: When Uvicorn is configured with --proxy-headers and
--forwarded-allow-ips, request.client.host already reflects the
X-Forwarded-For value. This utility provides an explicit fallback
for environments where proxy headers are not pre-processed.
"""

from fastapi import Request


def get_client_ip(request: Request) -> str:
    """
    Extract the real client IP address from a request.

    Checks X-Forwarded-For header first (for requests behind a reverse
    proxy like nginx), then falls back to the direct connection IP.

    Args:
        request: FastAPI/Starlette Request object

    Returns:
        Client IP address string, or "unknown" if unavailable
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take first IP (the original client), ignore proxy chain
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
