"""API interface entrypoint tests."""

from __future__ import annotations

import asyncio
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
    assert "from api_gateway.services.job_service import JobService" not in source
    assert "from api_gateway.services.file_service import FileService" not in source
    assert "from api_gateway.auth import get_current_user" not in source
    assert jobs_module.router.prefix == "/jobs"
    assert jobs_module.router_legacy.prefix == "/api/jobs"


def test_files_router_uses_src_auth_dependency():
    from mold_cost.interfaces.api.routers import files as files_module

    source = Path(files_module.__file__).read_text(encoding="utf-8")
    assert "from api_gateway.auth import get_current_user" not in source
    assert "from ..dependencies.auth import get_current_user" in source


def test_api_lifespan_initializes_review_handlers_via_src_adapter(monkeypatch):
    from mold_cost.interfaces.api import app as api_app_module

    calls: list[str] = []

    class _FakeClient:
        async def connect(self):
            calls.append("connect")

        async def close(self):
            calls.append("close")

    class _FakeTask:
        def cancel(self):
            calls.append("cancel")

        def __await__(self):
            async def _done():
                calls.append("await")
                return None

            return _done().__await__()

    monkeypatch.setattr(api_app_module, "rabbitmq_client", _FakeClient())
    monkeypatch.setattr(api_app_module, "redis_client", _FakeClient())
    monkeypatch.setattr(api_app_module, "initialize_review_action_handlers", lambda: calls.append("init_handlers"))
    monkeypatch.setattr(api_app_module.manager, "start_redis_subscriber", lambda: asyncio.sleep(0))

    def _fake_create_task(coro):
        coro.close()
        return _FakeTask()

    monkeypatch.setattr(api_app_module.asyncio, "create_task", _fake_create_task)

    async def _run():
        async with api_app_module.lifespan(api_app_module.app):
            return None

    asyncio.run(_run())

    assert "init_handlers" in calls

    source = Path(api_app_module.__file__).read_text(encoding="utf-8")
    assert "from agents.action_handlers import ActionHandlerFactory" not in source
    assert "from ...infrastructure.review.action_handler_runtime import initialize_review_action_handlers" in source
