from __future__ import annotations

import asyncio
import json

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


def test_mcp_price_tool_dispatches_through_registry(monkeypatch):
    from mcp_services.cad_price_search_mcp import server

    async def fake_search(job_id, subgraph_ids):
        assert job_id == "job-mcp"
        assert subgraph_ids == ["sg-1"]
        return {"job_id": job_id, "parts": [{"subgraph_id": "sg-1"}]}

    async def fake_calculate(search_data, job_id, subgraph_ids):
        assert search_data == {"base_itemcode": {"job_id": "job-mcp", "parts": [{"subgraph_id": "sg-1"}]}}
        assert job_id == "job-mcp"
        assert subgraph_ids == ["sg-1"]
        return {"results": [{"subgraph_id": "sg-1"}]}

    monkeypatch.setitem(server.PRICING_SEARCH_LOADERS, "base_itemcode", fake_search)
    monkeypatch.setitem(
        server.PRICING_CALCULATOR_TOOLS,
        "calculate_demo_cost",
        (fake_calculate, ("base_itemcode",), {"description": "demo", "inputSchema": {"type": "object"}}),
    )

    response = asyncio.run(
        server.handle_price_tool(
            "calculate_demo_cost",
            {"job_id": "job-mcp", "subgraph_ids": ["sg-1"]},
        )
    )
    payload = json.loads(response[0].text)

    assert payload["status"] == "ok"
    assert payload["results"] == [{"subgraph_id": "sg-1"}]
