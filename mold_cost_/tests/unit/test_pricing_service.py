from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_pricing_service_calculate_routes_single_batch(monkeypatch):
    from mold_cost.domain.pricing.services.pricing_service import pricing_service

    captured = {}
    publisher = object()

    async def fake_single_batch(*, job_id, subgraph_ids, progress_publisher=None, publish_progress=True):
        captured["job_id"] = job_id
        captured["subgraph_ids"] = subgraph_ids
        captured["progress_publisher"] = progress_publisher
        captured["publish_progress"] = publish_progress
        return {"status": "ok", "total_cost": 88.0}

    monkeypatch.setattr(pricing_service, "_process_single_batch", fake_single_batch)

    result = asyncio.run(
        pricing_service.calculate(
            {
                "job_id": "job-pricing-service-2",
                "subgraph_ids": ["sg-1", "sg-2"],
                "pricing_batch_size": 10,
                "_progress_publisher": publisher,
            }
        )
    )

    assert result == {"status": "ok", "total_cost": 88.0}
    assert captured == {
        "job_id": "job-pricing-service-2",
        "subgraph_ids": ["sg-1", "sg-2"],
        "progress_publisher": publisher,
        "publish_progress": True,
    }


def test_pricing_service_calculate_routes_multiple_batches(monkeypatch):
    from mold_cost.domain.pricing.services.pricing_service import pricing_service

    captured = {}

    async def fake_multiple_batches(*, job_id, subgraph_ids, batch_size, progress_publisher=None):
        captured["job_id"] = job_id
        captured["subgraph_ids"] = subgraph_ids
        captured["batch_size"] = batch_size
        captured["progress_publisher"] = progress_publisher
        return {"status": "ok", "batch_count": 2}

    monkeypatch.setattr(pricing_service, "_process_multiple_batches", fake_multiple_batches)

    result = asyncio.run(
        pricing_service.calculate(
            {
                "job_id": "job-pricing-service-3",
                "subgraph_ids": ["sg-1", "sg-2", "sg-3"],
                "pricing_batch_size": 2,
            }
        )
    )

    assert result == {"status": "ok", "batch_count": 2}
    assert captured == {
        "job_id": "job-pricing-service-3",
        "subgraph_ids": ["sg-1", "sg-2", "sg-3"],
        "batch_size": 2,
        "progress_publisher": None,
    }


def test_pricing_service_update_job_total_cost_uses_script_db(monkeypatch):
    from mold_cost.domain.pricing.services import pricing_service as pricing_service_module
    from mold_cost.domain.pricing.services.pricing_service import pricing_service

    captured: list[tuple[str, tuple[object, ...]]] = []

    async def fake_fetch_one(sql, *params):
        assert "SUM(total_cost)" in sql
        captured.append(("fetch_one", params))
        return {"total_cost": 123.45}

    async def fake_execute(sql, *params):
        assert "UPDATE jobs" in sql
        captured.append(("execute", params))
        return None

    monkeypatch.setattr(pricing_service_module.db, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(pricing_service_module.db, "execute", fake_execute)

    total_cost = asyncio.run(pricing_service.update_job_total_cost("job-pricing-service-1"))

    assert total_cost == 123.45
    assert captured == [
        ("fetch_one", ("job-pricing-service-1",)),
        ("execute", ("job-pricing-service-1", 123.45)),
    ]


def test_pricing_agent_local_process_delegates_to_pricing_service(monkeypatch):
    agent_path = Path(__file__).resolve().parents[2] / "agents" / "pricing_agent_local.py"
    spec = importlib.util.spec_from_file_location("pricing_agent_local_test", agent_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    captured: list[dict[str, object]] = []

    async def fake_calculate(context):
        captured.append(context)
        return {"status": "ok", "message": "delegated"}

    monkeypatch.setattr(module.pricing_service, "calculate", fake_calculate)

    agent = module.PricingAgentLocal(progress_publisher="publisher")
    result = asyncio.run(agent.process({"job_id": "job-agent", "subgraph_ids": ["sg-1"]}))

    assert result == {"status": "ok", "message": "delegated"}
    assert captured == [
        {
            "job_id": "job-agent",
            "subgraph_ids": ["sg-1"],
            "_progress_publisher": "publisher",
        }
    ]
