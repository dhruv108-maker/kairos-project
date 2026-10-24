"""Guard the public route surface while API assembly is modularized."""

from app.main import app


def test_application_registers_legacy_and_modular_routes() -> None:
    # Use OpenAPI's resolved path map instead of iterating internal route objects:
    # newer FastAPI versions may represent included routers lazily.
    paths = set(app.openapi()["paths"])

    # Existing API surface remains mounted at the configured v1 prefix.
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/institutions/resolve" in paths
    assert "/api/v1/institutions/public" in paths
    assert "/api/v1/students/me" in paths
    assert "/api/v1/internships/opportunities" in paths

    # The modular internship implementation remains opt-in and separately mounted.
    assert "/api/v1/modules/internships/opportunities" in paths
    assert "/health" in paths
