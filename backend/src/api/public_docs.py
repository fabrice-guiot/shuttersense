"""
Public API documentation endpoints for api.shuttersense.ai and docs.shuttersense.ai.

Serves filtered OpenAPI documentation that excludes internal routes
(agent, admin, auth, tokens) and presents clean API paths without
the /api/ prefix.

Endpoints:
    GET /public/api/docs         - Swagger UI with filtered schema
    GET /public/api/redoc        - ReDoc with filtered schema
    GET /public/api/openapi.json - Filtered OpenAPI 3.0 schema

Environment Variables:
    SHUSAI_PUBLIC_API_BASE_URL: Base URL for OpenAPI servers field
                                (e.g., https://api.shuttersense.ai)

Issue #159
"""

import copy
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import JSONResponse

from backend.src.config.settings import get_settings

router = APIRouter(tags=["Public Docs"])

# Path prefixes to exclude from the public API documentation.
# These routes require agent auth, super admin, session-only OAuth,
# or session-only token management — none usable with API tokens.
EXCLUDED_PATH_PREFIXES = (
    "/api/agent/",
    "/api/admin/",
    "/api/auth/",
    "/api/tokens/",
    "/api/tokens",  # exact match for /api/tokens without trailing slash
)

# Tags to remove from the public docs (associated with excluded routes)
EXCLUDED_TAGS = {
    "Agents",
    "Authentication",
    "Tokens",
    "Admin - Teams",
    "Admin - Release Manifests",
}


def _get_public_openapi_schema(full_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a filtered OpenAPI schema for the public API.

    Transforms the full internal schema by:
    1. Excluding internal routes (agent, admin, auth, tokens)
    2. Removing the /api/ prefix from all paths
    3. Setting the servers field to the public API URL
    4. Keeping only Bearer token security scheme
    5. Removing excluded tags
    6. Cleaning up unused component schemas

    Args:
        full_schema: The complete OpenAPI schema from the FastAPI app

    Returns:
        Filtered OpenAPI schema suitable for public consumption
    """
    schema = copy.deepcopy(full_schema)

    # 1. Filter paths: exclude internal routes and remove /api/ prefix
    original_paths = schema.get("paths", {})
    filtered_paths = {}
    for path, path_item in original_paths.items():
        # Skip excluded prefixes
        if any(path.startswith(prefix) for prefix in EXCLUDED_PATH_PREFIXES):
            continue

        # Skip non-API paths (health, system, docs endpoints)
        if not path.startswith("/api/"):
            continue

        # Remove /api/ prefix for clean public URLs
        public_path = path[4:]  # "/api/collections" -> "/collections"
        filtered_paths[public_path] = path_item

    schema["paths"] = filtered_paths

    # 2. Set servers field
    settings = get_settings()
    if settings.public_api_base_url:
        schema["servers"] = [
            {
                "url": settings.public_api_base_url,
                "description": "Production API",
            }
        ]
    else:
        # Fallback: remove servers field so Swagger UI uses relative URLs
        schema.pop("servers", None)

    # 3. Update security schemes - keep only Bearer token auth
    components = schema.get("components", {})
    security_schemes = components.get("securitySchemes", {})
    # Keep only BearerAuth, remove any session/cookie schemes
    filtered_schemes = {}
    for name, scheme_def in security_schemes.items():
        if scheme_def.get("scheme") == "bearer" or name == "BearerAuth":
            filtered_schemes[name] = scheme_def
    if filtered_schemes:
        components["securitySchemes"] = filtered_schemes
    elif "securitySchemes" in components:
        del components["securitySchemes"]

    # 4. Remove excluded tags from tag definitions
    if "tags" in schema:
        schema["tags"] = [
            tag for tag in schema["tags"]
            if tag.get("name") not in EXCLUDED_TAGS
        ]

    # 5. Clean up unused component schemas
    _remove_unused_schemas(schema)

    # 6. Update metadata
    schema["info"]["title"] = "ShutterSense.ai Public API"
    schema["info"]["description"] = (
        "Public REST API for ShutterSense.ai - Capture. Process. Analyze. "
        "Authenticate with a Bearer token generated from the web application."
    )

    return schema


def _remove_unused_schemas(schema: Dict[str, Any]) -> None:
    """
    Remove component schemas that are no longer referenced after path filtering.

    Iterates until no more schemas can be removed (handles transitive references).

    Args:
        schema: The OpenAPI schema (modified in place)
    """
    components = schema.get("components", {})
    schemas = components.get("schemas", {})
    if not schemas:
        return

    max_iterations = 10  # Safety limit to prevent infinite loops

    for _ in range(max_iterations):
        # Collect all $ref references from paths and remaining schemas
        referenced = _collect_refs(schema)

        # Find schemas that are not referenced
        unreferenced = set()
        for schema_name in schemas:
            ref_str = f"#/components/schemas/{schema_name}"
            if ref_str not in referenced:
                unreferenced.add(schema_name)

        if not unreferenced:
            break

        # Remove unreferenced schemas
        for name in unreferenced:
            del schemas[name]


def _collect_refs(obj: Any, refs: Optional[Set[str]] = None) -> Set[str]:
    """
    Recursively collect all $ref values from a nested dict/list structure.

    Args:
        obj: The object to traverse (dict, list, or scalar)
        refs: Accumulator set (created if None)

    Returns:
        Set of all $ref string values found
    """
    if refs is None:
        refs = set()

    if isinstance(obj, dict):
        if "$ref" in obj:
            refs.add(obj["$ref"])
        for value in obj.values():
            _collect_refs(value, refs)
    elif isinstance(obj, list):
        for item in obj:
            _collect_refs(item, refs)

    return refs


# Cache for the filtered schema (regenerated when full schema changes)
_cached_public_schema: Optional[Dict[str, Any]] = None
_cached_full_schema_id: Optional[int] = None


def get_public_openapi(app_openapi_func) -> Dict[str, Any]:
    """
    Get the cached public OpenAPI schema, regenerating if the full schema changed.

    Args:
        app_openapi_func: The FastAPI app's openapi() callable

    Returns:
        Filtered public OpenAPI schema
    """
    global _cached_public_schema, _cached_full_schema_id

    full_schema = app_openapi_func()
    full_id = id(full_schema)

    if _cached_public_schema is None or _cached_full_schema_id != full_id:
        _cached_public_schema = _get_public_openapi_schema(full_schema)
        _cached_full_schema_id = full_id

    return _cached_public_schema


@router.get("/public/api/openapi.json", include_in_schema=False)
async def public_openapi_json():
    """Serve the filtered OpenAPI schema for the public API."""
    from backend.src.main import app
    schema = get_public_openapi(app.openapi)
    return JSONResponse(content=schema)


@router.get("/public/api/docs", include_in_schema=False)
async def public_swagger_ui():
    """Serve Swagger UI with filtered public API schema."""
    return get_swagger_ui_html(
        openapi_url="/public/api/openapi.json",
        title="ShutterSense.ai Public API - Swagger UI",
        swagger_favicon_url="/favicon.svg",
    )


@router.get("/public/api/redoc", include_in_schema=False)
async def public_redoc():
    """Serve ReDoc with filtered public API schema."""
    return get_redoc_html(
        openapi_url="/public/api/openapi.json",
        title="ShutterSense.ai Public API - ReDoc",
        redoc_favicon_url="/favicon.svg",
    )
