from __future__ import annotations

import asyncio

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_pricing_agent_local_process_delegates_to_pricing_service(monkeypatch):
    from agents.pricing_agent_local import PricingAgentLocal

    captured: dict[str, object] = {}

    async def fake_calculate(context):
        captured.update(context)
        return {"status": "ok", "total_cost": 12.5}

    monkeypatch.setattr(
        "mold_cost.domain.pricing.services.pricing_service.pricing_service.calculate",
        fake_calculate,
    )

    agent = PricingAgentLocal(progress_publisher="publisher-local")
    result = asyncio.run(agent.process({"job_id": "job-1", "subgraph_ids": ["sg-1"]}))

    assert result == {"status": "ok", "total_cost": 12.5}
    assert captured["job_id"] == "job-1"
    assert captured["subgraph_ids"] == ["sg-1"]
    assert captured["_progress_publisher"] == "publisher-local"


def test_pricing_agent_process_delegates_to_pricing_service(monkeypatch):
    from agents.pricing_agent import PricingAgent

    captured: dict[str, object] = {}

    async def fake_calculate(context):
        captured.update(context)
        return {"status": "ok", "total_cost": 18.0}

    monkeypatch.setattr(
        "mold_cost.domain.pricing.services.pricing_service.pricing_service.calculate",
        fake_calculate,
    )

    agent = PricingAgent(price_search_mcp_client=object(), progress_publisher="publisher-mcp")
    result = asyncio.run(agent.process({"job_id": "job-2", "subgraph_ids": ["sg-2"]}))

    assert result == {"status": "ok", "total_cost": 18.0}
    assert captured["job_id"] == "job-2"
    assert captured["subgraph_ids"] == ["sg-2"]
    assert captured["_progress_publisher"] == "publisher-mcp"

