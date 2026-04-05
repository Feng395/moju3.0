"""API interface entrypoint tests."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI


def test_src_api_app_is_real_entrypoint():
    from mold_cost.interfaces.api import app as api_app_module

    assert isinstance(api_app_module.app, FastAPI)
    assert api_app_module.get_app() is api_app_module.app

    source = Path(api_app_module.__file__).read_text(encoding="utf-8")
    assert "from api_gateway.main import app" not in source

    route_paths = {route.path for route in api_app_module.app.routes}
    assert any(path.startswith("/jobs") for path in route_paths)
    assert any(path.startswith("/api/jobs") for path in route_paths)
    assert "/health" in route_paths


def test_legacy_api_gateway_reexports_new_app():
    import api_gateway.main as legacy_main
    from mold_cost.interfaces.api.app import app as new_app

    assert legacy_main.app is new_app
    assert legacy_main.get_app() is new_app


def test_jobs_router_is_implemented_in_src_package():
    from mold_cost.interfaces.api.routers import jobs as jobs_module

    source = Path(jobs_module.__file__).read_text(encoding="utf-8")
    assert "from api_gateway.routers.jobs import router" not in source
    assert "from api_gateway.routers.jobs import router_legacy" not in source
    assert jobs_module.router.prefix == "/jobs"
    assert jobs_module.router_legacy.prefix == "/api/jobs"
