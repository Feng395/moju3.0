from __future__ import annotations

import asyncio

from refactor_bootstrap import ensure_src_path

ensure_src_path()


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
