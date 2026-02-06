"""
Tests for public API documentation endpoints (Issue #159).

Tests the filtered OpenAPI schema generation and public doc endpoints:
- Path filtering (excludes agent, admin, auth, tokens)
- /api/ prefix removal
- Servers field configuration
- Security scheme filtering
- Tag filtering
- Unused schema cleanup
- Swagger UI and ReDoc endpoint responses
"""

import pytest
from unittest.mock import patch

from backend.src.api.public_docs import (
    _get_public_openapi_schema,
    _collect_refs,
    _remove_unused_schemas,
    EXCLUDED_PATH_PREFIXES,
    EXCLUDED_TAGS,
)


# ============================================================================
# Sample OpenAPI Schema Fixture
# ============================================================================

@pytest.fixture
def sample_openapi_schema():
    """Create a minimal OpenAPI schema mimicking the real app schema."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "ShutterSense.ai API",
            "description": "Backend API for ShutterSense.ai",
            "version": "1.0.0",
        },
        "paths": {
            "/api/collections": {
                "get": {
                    "tags": ["Collections"],
                    "summary": "List collections",
                    "security": [{"BearerAuth": []}],
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/CollectionList"}
                                }
                            }
                        }
                    },
                },
                "post": {
                    "tags": ["Collections"],
                    "summary": "Create collection",
                    "security": [{"BearerAuth": []}],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/CollectionCreate"}
                            }
                        }
                    },
                },
            },
            "/api/events": {
                "get": {
                    "tags": ["Events"],
                    "summary": "List events",
                    "security": [{"BearerAuth": []}],
                },
            },
            "/api/agent/v1/heartbeat": {
                "post": {
                    "tags": ["Agents"],
                    "summary": "Agent heartbeat",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/AgentHeartbeat"}
                            }
                        }
                    },
                },
            },
            "/api/agent/v1/register": {
                "post": {
                    "tags": ["Agents"],
                    "summary": "Register agent",
                },
            },
            "/api/admin/teams": {
                "get": {
                    "tags": ["Admin - Teams"],
                    "summary": "List teams",
                },
            },
            "/api/auth/login": {
                "get": {
                    "tags": ["Authentication"],
                    "summary": "Login",
                },
            },
            "/api/auth/callback/google": {
                "get": {
                    "tags": ["Authentication"],
                    "summary": "OAuth callback",
                },
            },
            "/api/tokens": {
                "get": {
                    "tags": ["Tokens"],
                    "summary": "List tokens",
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/TokenList"}
                                }
                            }
                        }
                    },
                },
                "post": {
                    "tags": ["Tokens"],
                    "summary": "Create token",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/TokenCreate"}
                            }
                        }
                    },
                },
            },
            "/api/tokens/stats": {
                "get": {
                    "tags": ["Tokens"],
                    "summary": "Token stats",
                },
            },
            "/health": {
                "get": {
                    "tags": ["Health"],
                    "summary": "Health check",
                },
            },
            "/api/version": {
                "get": {
                    "tags": ["System"],
                    "summary": "Get version",
                },
            },
        },
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                },
                "SessionCookie": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "session",
                },
            },
            "schemas": {
                "CollectionList": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/CollectionSummary"},
                        }
                    },
                },
                "CollectionSummary": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                },
                "CollectionCreate": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                },
                "AgentHeartbeat": {
                    "type": "object",
                    "properties": {"status": {"type": "string"}},
                },
                "TokenList": {
                    "type": "object",
                    "properties": {"items": {"type": "array"}},
                },
                "TokenCreate": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                },
            },
        },
        "tags": [
            {"name": "Collections", "description": "Photo collections"},
            {"name": "Events", "description": "Calendar events"},
            {"name": "Agents", "description": "Agent operations"},
            {"name": "Authentication", "description": "OAuth"},
            {"name": "Tokens", "description": "API tokens"},
            {"name": "Admin - Teams", "description": "Team management"},
            {"name": "Admin - Release Manifests", "description": "Release management"},
            {"name": "Health", "description": "Health check"},
            {"name": "System", "description": "System info"},
        ],
    }


# ============================================================================
# Path Filtering Tests
# ============================================================================

class TestPathFiltering:
    """Tests for excluding internal routes from the public schema."""

    def test_excludes_agent_routes(self, sample_openapi_schema):
        """Agent routes (/api/agent/v1/*) should be excluded."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = ""
            result = _get_public_openapi_schema(sample_openapi_schema)

        paths = result["paths"]
        assert not any("/agent/" in p for p in paths)

    def test_excludes_admin_routes(self, sample_openapi_schema):
        """Admin routes (/api/admin/*) should be excluded."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = ""
            result = _get_public_openapi_schema(sample_openapi_schema)

        paths = result["paths"]
        assert not any("/admin/" in p for p in paths)

    def test_excludes_auth_routes(self, sample_openapi_schema):
        """Auth routes (/api/auth/*) should be excluded."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = ""
            result = _get_public_openapi_schema(sample_openapi_schema)

        paths = result["paths"]
        assert not any("/auth/" in p for p in paths)

    def test_excludes_tokens_routes(self, sample_openapi_schema):
        """Token routes (/api/tokens*) should be excluded."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = ""
            result = _get_public_openapi_schema(sample_openapi_schema)

        paths = result["paths"]
        assert not any("tokens" in p for p in paths)

    def test_excludes_health_endpoint(self, sample_openapi_schema):
        """Non-API paths like /health should be excluded (not prefixed with /api/)."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = ""
            result = _get_public_openapi_schema(sample_openapi_schema)

        paths = result["paths"]
        assert "/health" not in paths

    def test_keeps_public_api_routes(self, sample_openapi_schema):
        """Public API routes should be kept."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = ""
            result = _get_public_openapi_schema(sample_openapi_schema)

        paths = result["paths"]
        assert "/collections" in paths
        assert "/events" in paths
        assert "/version" in paths


class TestPathPrefixRemoval:
    """Tests for removing the /api/ prefix from paths."""

    def test_removes_api_prefix(self, sample_openapi_schema):
        """/api/collections should become /collections."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = ""
            result = _get_public_openapi_schema(sample_openapi_schema)

        paths = result["paths"]
        assert "/collections" in paths
        assert "/api/collections" not in paths

    def test_preserves_path_methods(self, sample_openapi_schema):
        """HTTP methods should be preserved after prefix removal."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = ""
            result = _get_public_openapi_schema(sample_openapi_schema)

        collections = result["paths"]["/collections"]
        assert "get" in collections
        assert "post" in collections


# ============================================================================
# Servers Field Tests
# ============================================================================

class TestServersField:
    """Tests for the OpenAPI servers field configuration."""

    def test_sets_servers_when_configured(self, sample_openapi_schema):
        """Servers field should be set when PUBLIC_API_BASE_URL is configured."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = "https://api.shuttersense.ai"
            result = _get_public_openapi_schema(sample_openapi_schema)

        assert result["servers"] == [
            {"url": "https://api.shuttersense.ai", "description": "Production API"}
        ]

    def test_removes_servers_when_not_configured(self, sample_openapi_schema):
        """Servers field should be absent when PUBLIC_API_BASE_URL is empty."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = ""
            result = _get_public_openapi_schema(sample_openapi_schema)

        assert "servers" not in result


# ============================================================================
# Security Scheme Tests
# ============================================================================

class TestSecuritySchemes:
    """Tests for filtering security schemes to Bearer-only."""

    def test_keeps_bearer_auth(self, sample_openapi_schema):
        """BearerAuth scheme should be preserved."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = ""
            result = _get_public_openapi_schema(sample_openapi_schema)

        schemes = result["components"]["securitySchemes"]
        assert "BearerAuth" in schemes
        assert schemes["BearerAuth"]["scheme"] == "bearer"

    def test_removes_session_auth(self, sample_openapi_schema):
        """Session/cookie authentication should be removed."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = ""
            result = _get_public_openapi_schema(sample_openapi_schema)

        schemes = result["components"]["securitySchemes"]
        assert "SessionCookie" not in schemes


# ============================================================================
# Tag Filtering Tests
# ============================================================================

class TestTagFiltering:
    """Tests for removing excluded tags from the schema."""

    def test_removes_excluded_tags(self, sample_openapi_schema):
        """Internal tags (Agents, Auth, Tokens, Admin) should be removed."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = ""
            result = _get_public_openapi_schema(sample_openapi_schema)

        tag_names = {t["name"] for t in result["tags"]}
        for excluded in EXCLUDED_TAGS:
            assert excluded not in tag_names

    def test_keeps_public_tags(self, sample_openapi_schema):
        """Public tags should be preserved."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = ""
            result = _get_public_openapi_schema(sample_openapi_schema)

        tag_names = {t["name"] for t in result["tags"]}
        assert "Collections" in tag_names
        assert "Events" in tag_names


# ============================================================================
# Unused Schema Cleanup Tests
# ============================================================================

class TestUnusedSchemaCleanup:
    """Tests for removing schemas no longer referenced after filtering."""

    def test_removes_agent_schemas(self, sample_openapi_schema):
        """Schemas only referenced by agent routes should be removed."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = ""
            result = _get_public_openapi_schema(sample_openapi_schema)

        schemas = result["components"]["schemas"]
        assert "AgentHeartbeat" not in schemas

    def test_removes_token_schemas(self, sample_openapi_schema):
        """Schemas only referenced by token routes should be removed."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = ""
            result = _get_public_openapi_schema(sample_openapi_schema)

        schemas = result["components"]["schemas"]
        assert "TokenList" not in schemas
        assert "TokenCreate" not in schemas

    def test_keeps_referenced_schemas(self, sample_openapi_schema):
        """Schemas still referenced by public routes should be kept."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = ""
            result = _get_public_openapi_schema(sample_openapi_schema)

        schemas = result["components"]["schemas"]
        assert "CollectionList" in schemas
        assert "CollectionSummary" in schemas  # Referenced transitively
        assert "CollectionCreate" in schemas

    def test_handles_transitive_removal(self):
        """Schemas referenced only by other removed schemas should also be removed."""
        schema = {
            "openapi": "3.1.0",
            "info": {"title": "Test", "description": "Test", "version": "1.0.0"},
            "paths": {
                "/api/items": {
                    "get": {
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ItemList"}
                                    }
                                }
                            }
                        }
                    }
                },
            },
            "components": {
                "schemas": {
                    "ItemList": {
                        "properties": {
                            "items": {
                                "items": {"$ref": "#/components/schemas/Item"}
                            }
                        }
                    },
                    "Item": {"properties": {"name": {"type": "string"}}},
                    "OrphanParent": {
                        "properties": {
                            "child": {"$ref": "#/components/schemas/OrphanChild"}
                        }
                    },
                    "OrphanChild": {"properties": {"x": {"type": "string"}}},
                }
            },
        }

        _remove_unused_schemas(schema)
        schemas = schema["components"]["schemas"]
        assert "ItemList" in schemas
        assert "Item" in schemas
        assert "OrphanParent" not in schemas
        assert "OrphanChild" not in schemas


# ============================================================================
# Metadata Tests
# ============================================================================

class TestMetadata:
    """Tests for updated schema metadata."""

    def test_updates_title(self, sample_openapi_schema):
        """Schema title should be updated for public API."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = ""
            result = _get_public_openapi_schema(sample_openapi_schema)

        assert result["info"]["title"] == "ShutterSense.ai Public API"

    def test_updates_description(self, sample_openapi_schema):
        """Schema description should mention Bearer token auth."""
        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = ""
            result = _get_public_openapi_schema(sample_openapi_schema)

        assert "Bearer token" in result["info"]["description"]


# ============================================================================
# Deep Copy Safety Test
# ============================================================================

class TestDeepCopy:
    """Tests that the original schema is not mutated."""

    def test_does_not_mutate_original(self, sample_openapi_schema):
        """Filtering should not modify the original schema."""
        import copy
        original = copy.deepcopy(sample_openapi_schema)

        with patch("backend.src.api.public_docs.get_settings") as mock:
            mock.return_value.public_api_base_url = "https://api.test.com"
            _get_public_openapi_schema(sample_openapi_schema)

        assert sample_openapi_schema == original


# ============================================================================
# Collect Refs Helper Tests
# ============================================================================

class TestCollectRefs:
    """Tests for the _collect_refs utility function."""

    def test_collects_from_nested_dict(self):
        obj = {"a": {"$ref": "#/components/schemas/Foo"}, "b": {"$ref": "#/components/schemas/Bar"}}
        refs = _collect_refs(obj)
        assert refs == {"#/components/schemas/Foo", "#/components/schemas/Bar"}

    def test_collects_from_list(self):
        obj = [{"$ref": "#/components/schemas/A"}, {"$ref": "#/components/schemas/B"}]
        refs = _collect_refs(obj)
        assert refs == {"#/components/schemas/A", "#/components/schemas/B"}

    def test_handles_empty(self):
        assert _collect_refs({}) == set()
        assert _collect_refs([]) == set()
        assert _collect_refs("string") == set()

    def test_deeply_nested(self):
        obj = {"a": {"b": {"c": [{"$ref": "#/deep"}]}}}
        refs = _collect_refs(obj)
        assert refs == {"#/deep"}


# ============================================================================
# Endpoint Integration Tests
# ============================================================================

class TestPublicDocsEndpoints:
    """Integration tests for the public docs HTTP endpoints."""

    def test_public_openapi_json_returns_200(self, test_client):
        """GET /public/api/openapi.json should return 200 with JSON."""
        response = test_client.get("/public/api/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data

    def test_public_openapi_json_excludes_internal_routes(self, test_client):
        """The public schema should not contain internal routes."""
        response = test_client.get("/public/api/openapi.json")
        data = response.json()
        paths = data["paths"]

        for path in paths:
            assert not path.startswith("/api/"), f"Path should not have /api/ prefix: {path}"
            assert "/agent/" not in path, f"Agent route should be excluded: {path}"
            assert "/admin/" not in path, f"Admin route should be excluded: {path}"
            assert "/auth/" not in path, f"Auth route should be excluded: {path}"

    def test_public_openapi_json_has_bearer_auth(self, test_client):
        """The public schema should include BearerAuth security scheme."""
        response = test_client.get("/public/api/openapi.json")
        data = response.json()
        schemes = data.get("components", {}).get("securitySchemes", {})
        assert "BearerAuth" in schemes

    def test_public_swagger_ui_returns_200(self, test_client):
        """GET /public/api/docs should return Swagger UI HTML."""
        response = test_client.get("/public/api/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "swagger-ui" in response.text.lower()

    def test_public_swagger_ui_references_public_schema(self, test_client):
        """Swagger UI should load the public OpenAPI schema URL."""
        response = test_client.get("/public/api/docs")
        assert "/public/api/openapi.json" in response.text

    def test_public_redoc_returns_200(self, test_client):
        """GET /public/api/redoc should return ReDoc HTML."""
        response = test_client.get("/public/api/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "redoc" in response.text.lower()

    def test_public_redoc_references_public_schema(self, test_client):
        """ReDoc should load the public OpenAPI schema URL."""
        response = test_client.get("/public/api/redoc")
        assert "/public/api/openapi.json" in response.text

    def test_public_schema_has_collections_path(self, test_client):
        """The public schema should include /collections (without /api/ prefix)."""
        response = test_client.get("/public/api/openapi.json")
        data = response.json()
        assert "/collections" in data["paths"]

    def test_public_schema_no_tokens_path(self, test_client):
        """The public schema should not include token management routes."""
        response = test_client.get("/public/api/openapi.json")
        data = response.json()
        for path in data["paths"]:
            assert "tokens" not in path, f"Token route should be excluded: {path}"

    def test_public_docs_not_in_main_schema(self, test_client):
        """Public doc endpoints should not appear in the main OpenAPI schema."""
        response = test_client.get("/openapi.json")
        data = response.json()
        paths = data.get("paths", {})
        assert "/public/api/docs" not in paths
        assert "/public/api/redoc" not in paths
        assert "/public/api/openapi.json" not in paths
