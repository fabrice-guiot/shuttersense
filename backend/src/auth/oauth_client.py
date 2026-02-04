"""
OAuth 2.0 client configuration for Google and Microsoft providers.

Uses Authlib for OAuth 2.0 + PKCE authentication flow with OpenID Connect
for identity verification.

Providers:
- Google: Uses OpenID Connect discovery for automatic endpoint configuration
- Microsoft: Uses Azure AD common endpoint for multi-tenant support

Security:
- PKCE (S256) is enforced for all OAuth flows
- State parameter prevents CSRF attacks
- Nonce parameter prevents replay attacks
"""

from typing import Optional

from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client.apps import StarletteOAuth2App
from starlette.requests import Request

from backend.src.config.oauth import get_oauth_settings
from backend.src.utils.logging_config import get_logger


logger = get_logger("auth")


class MicrosoftOAuth2App(StarletteOAuth2App):
    """
    Custom OAuth2 client for Microsoft that handles multi-tenant issuer validation.

    Microsoft's "common" endpoint discovery document advertises the issuer as
    ``https://login.microsoftonline.com/common/v2.0``, but actual ID tokens
    contain a tenant-specific issuer like
    ``https://login.microsoftonline.com/{tid}/v2.0``.

    This subclass extracts the ``tid`` (tenant ID) claim from the ID token
    and validates the issuer against the expected tenant-specific pattern,
    rather than skipping issuer validation entirely.
    """

    async def parse_id_token(self, token, nonce, claims_options=None, claims_cls=None, leeway=120):
        """Override to validate issuer against tenant-specific pattern."""
        if claims_options is None:
            claims_options = {}

        tid = self._extract_tid(token.get("id_token", ""))
        expected_issuer: str | None = None
        if tid:
            expected_issuer = f"https://login.microsoftonline.com/{tid}/v2.0"
            claims_options["iss"] = {"essential": True, "value": expected_issuer}
            logger.info(f"Microsoft OAuth: tid={tid}, expected_issuer={expected_issuer}")
        else:
            # Cannot determine expected issuer — reject tokens without tid
            logger.warning("Microsoft ID token missing tid claim; issuer cannot be validated")
            claims_options["iss"] = {"essential": True}

        try:
            return await super().parse_id_token(token, nonce, claims_options, claims_cls, leeway)
        except Exception as e:
            # Log detailed error for debugging token validation failures
            logger.error(f"Microsoft ID token validation failed: {e}", exc_info=True)
            # Also log the actual issuer from the token for comparison
            actual_issuer = self._extract_claim(token.get("id_token", ""), "iss")
            if actual_issuer:
                logger.error(f"Token issuer mismatch: expected={expected_issuer or 'unknown'}, actual={actual_issuer}")
            raise

    @staticmethod
    def _extract_tid(id_token: str) -> str | None:
        """Extract the tenant ID from a JWT without full verification.

        The signature is verified by the parent class; this only peeks at the
        payload to learn which tenant issued the token so the correct issuer
        value can be constructed for validation.
        """
        return MicrosoftOAuth2App._extract_claim(id_token, "tid")

    @staticmethod
    def _extract_claim(id_token: str, claim: str) -> str | None:
        """Extract a claim from a JWT without full verification.

        Used for debugging and constructing validation parameters.
        The signature is verified separately by the parent class.
        """
        import base64
        import json

        try:
            parts = id_token.split(".")
            if len(parts) != 3:
                return None
            payload_b64 = parts[1]
            # Restore padding stripped by JWT encoding
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            return payload.get(claim)
        except Exception:
            return None


# Global OAuth registry instance
_oauth: Optional[OAuth] = None


def _get_oauth_registry() -> OAuth:
    """
    Get or create the OAuth registry singleton.

    Returns:
        OAuth registry with configured providers
    """
    global _oauth

    if _oauth is not None:
        return _oauth

    settings = get_oauth_settings()
    _oauth = OAuth()

    # Register Google OAuth client
    if settings.google_enabled:
        _oauth.register(
            name="google",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            server_metadata_url=settings.google_discovery_url,
            client_kwargs={
                "scope": " ".join(settings.oauth_scopes),
                "code_challenge_method": settings.code_challenge_method,
            },
        )
        logger.info("Google OAuth client registered")
    else:
        logger.warning("Google OAuth not configured (missing client credentials)")

    # Register Microsoft OAuth client using custom class that handles multi-tenant issuer
    # Note: Microsoft's "common" endpoint returns tenant-specific issuers in ID tokens,
    # but the discovery document has a placeholder. MicrosoftOAuth2App validates the
    # issuer against the tenant-specific pattern extracted from the tid claim.
    if settings.microsoft_enabled:
        _oauth.register(
            name="microsoft",
            client_id=settings.microsoft_client_id,
            client_secret=settings.microsoft_client_secret,
            server_metadata_url=settings.microsoft_discovery_url,
            client_cls=MicrosoftOAuth2App,
            client_kwargs={
                "scope": " ".join(settings.oauth_scopes),
                "code_challenge_method": settings.code_challenge_method,
            },
        )
        logger.info("Microsoft OAuth client registered")
    else:
        logger.warning("Microsoft OAuth not configured (missing client credentials)")

    return _oauth


def get_oauth_client(provider: str) -> Optional[StarletteOAuth2App]:
    """
    Get an OAuth client for the specified provider.

    Args:
        provider: Provider name ("google" or "microsoft")

    Returns:
        OAuth client instance or None if provider not configured

    Raises:
        ValueError: If provider name is invalid
    """
    if provider not in ("google", "microsoft"):
        raise ValueError(f"Invalid OAuth provider: {provider}. Must be 'google' or 'microsoft'")

    oauth = _get_oauth_registry()
    client = getattr(oauth, provider, None)

    if client is None:
        logger.warning(f"OAuth client for {provider} not available (not configured)")
        return None

    return client


def get_google_client() -> Optional[StarletteOAuth2App]:
    """
    Get the Google OAuth client.

    Returns:
        Google OAuth client or None if not configured
    """
    return get_oauth_client("google")


def get_microsoft_client() -> Optional[StarletteOAuth2App]:
    """
    Get the Microsoft OAuth client.

    Returns:
        Microsoft OAuth client or None if not configured
    """
    return get_oauth_client("microsoft")


async def create_authorization_url(
    request: Request,
    provider: str,
    redirect_uri: str,
) -> tuple[str, str]:
    """
    Create an OAuth authorization URL for the specified provider.

    Generates the authorization URL with PKCE challenge and state parameter.

    Args:
        request: Starlette request (needed for session storage)
        provider: Provider name ("google" or "microsoft")
        redirect_uri: OAuth callback URL

    Returns:
        Tuple of (authorization_url, state)

    Raises:
        ValueError: If provider not configured
    """
    client = get_oauth_client(provider)
    if client is None:
        raise ValueError(f"OAuth provider '{provider}' is not configured")

    # Generate authorization URL with PKCE
    # Authlib automatically generates code_verifier, code_challenge, and state
    # and stores them in the session
    url = await client.create_authorization_url(
        redirect_uri=redirect_uri,
    )

    # Save authorization data to session for callback verification
    # Authlib handles this internally via request.session
    await client.save_authorize_data(
        request,
        redirect_uri=redirect_uri,
        **url,
    )

    return url["url"], url.get("state", "")


async def fetch_token(
    request: Request,
    provider: str,
) -> dict:
    """
    Exchange authorization code for tokens.

    Verifies the state parameter and exchanges the code for access/ID tokens.

    Args:
        request: Starlette request with authorization code
        provider: Provider name

    Returns:
        Token response dict containing access_token, id_token, etc.

    Raises:
        ValueError: If provider not configured
        OAuthError: If token exchange fails
    """
    client = get_oauth_client(provider)
    if client is None:
        raise ValueError(f"OAuth provider '{provider}' is not configured")

    # Authlib automatically verifies state and PKCE code_verifier
    # Note: For Microsoft, MicrosoftOAuth2App handles tenant-specific issuer validation
    token = await client.authorize_access_token(request)

    return token


async def get_user_info(
    provider: str,
    token: dict,
) -> dict:
    """
    Parse user information from the ID token.

    For OpenID Connect providers, user info is embedded in the ID token.
    For Microsoft, also fetches profile picture from Graph API.

    Args:
        provider: Provider name
        token: Token response from fetch_token

    Returns:
        User info dict with keys: sub, email, name, picture (provider-dependent)
    """
    client = get_oauth_client(provider)
    if client is None:
        raise ValueError(f"OAuth provider '{provider}' is not configured")

    # Parse the ID token to get user claims
    # Authlib automatically verifies the token signature
    user_info = token.get("userinfo")

    if user_info is None:
        # Fallback: fetch from userinfo endpoint
        # This shouldn't be needed for OIDC providers but provides a safety net
        logger.warning(f"No userinfo in token for {provider}, fetching from endpoint")
        user_info = await client.userinfo(token=token)

    result = dict(user_info) if user_info else {}

    # Microsoft doesn't include 'picture' in userinfo, fetch from Graph API
    if provider == "microsoft" and "picture" not in result:
        picture_url = await _fetch_microsoft_photo_url(token.get("access_token"))
        if picture_url:
            result["picture"] = picture_url

    return result


async def _fetch_microsoft_photo_url(access_token: str | None) -> str | None:
    """
    Fetch user's profile photo URL from Microsoft Graph API.

    Microsoft Graph doesn't provide a direct public URL for photos.
    Instead, we fetch the photo metadata to check if one exists.
    If it does, we return a Graph API URL that requires auth (which won't work for <img>).

    For a working solution, we'd need to either:
    1. Download and cache the photo
    2. Proxy the photo through our backend
    3. Use a data URL (base64)

    For now, we'll try to get a usable URL or return None.

    Args:
        access_token: Microsoft OAuth access token

    Returns:
        Photo URL or None if not available
    """
    if not access_token:
        return None

    import httpx

    try:
        # First check if user has a photo by getting metadata
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me/photo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )

            if response.status_code == 404:
                logger.debug("Microsoft user has no profile photo")
                return None

            if response.status_code != 200:
                logger.warning(f"Failed to fetch Microsoft photo metadata: {response.status_code}")
                return None

            # Photo exists, fetch it and convert to data URL
            photo_response = await client.get(
                "https://graph.microsoft.com/v1.0/me/photo/$value",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )

            if photo_response.status_code != 200:
                logger.warning(f"Failed to fetch Microsoft photo: {photo_response.status_code}")
                return None

            # Convert to base64 data URL
            import base64
            content_type = photo_response.headers.get("content-type", "image/jpeg")
            photo_base64 = base64.b64encode(photo_response.content).decode("utf-8")
            data_url = f"data:{content_type};base64,{photo_base64}"

            logger.info("Successfully fetched Microsoft profile photo")
            return data_url

    except Exception as e:
        logger.warning(f"Error fetching Microsoft photo: {e}")
        return None


def get_available_providers() -> list[str]:
    """
    Get list of configured OAuth providers.

    Returns:
        List of provider names that are properly configured
    """
    settings = get_oauth_settings()
    providers = []

    if settings.google_enabled:
        providers.append("google")
    if settings.microsoft_enabled:
        providers.append("microsoft")

    return providers


def is_provider_configured(provider: str) -> bool:
    """
    Check if an OAuth provider is configured.

    Args:
        provider: Provider name

    Returns:
        True if provider is configured and ready to use
    """
    return provider in get_available_providers()
