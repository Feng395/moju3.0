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

def test_get_pricing_agent_returns_cached_local_wrapper(monkeypatch):
    import agents

    monkeypatch.setattr(agents, "_pricing_agent", None)
    monkeypatch.setattr(agents, "get_progress_publisher", lambda: "publisher-factory")
    monkeypatch.setattr(
        agents,
        "check_mcp_health",
        lambda: (_ for _ in ()).throw(AssertionError("pricing factory should not probe MCP")),
    )

    agent_one = agents.get_pricing_agent()
    agent_two = agents.get_pricing_agent()

    assert agent_one is agent_two
    assert agent_one.__class__.__name__ == "PricingAgentLocal"
    assert agent_one.progress_publisher == "publisher-factory"

