from __future__ import annotations

import asyncio

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_nc_total_calculator_prefers_max_costs_and_updates_subgraphs(monkeypatch):
    from mold_cost.domain.pricing.calculators import price_nc_total as module

    db_calls: list[tuple[str, tuple[object, ...]]] = []

    async def fake_execute(sql: str, *params):
        db_calls.append((sql, params))
        return None

    monkeypatch.setattr(module.db, "execute", fake_execute)

    result = asyncio.run(
        module.calculate(
            {
                "total": {
                    "job_id": "job-nc-total-1",
                    "cost_details": [
                        {
                            "subgraph_id": "sg-1",
                            "nc_roughing_cost": 100.0,
                            "nc_milling_cost": 0.0,
                            "nc_drilling_cost": 30.0,
                            "nc_base_roughing_cost": 80.0,
                            "nc_base_milling_cost": 60.0,
                            "nc_base_drilling_cost": 80.0,
                        }
                    ],
                }
            },
            job_id="job-nc-total-1",
        )
    )

    assert result["job_id"] == "job-nc-total-1"
    assert len(result["results"]) == 1
    part = result["results"][0]
    assert part["subgraph_id"] == "sg-1"
    assert part["final"]["nc_roughing_cost"] == pytest.approx(100.0)
    assert part["final"]["nc_milling_cost"] == pytest.approx(0.0)
    assert part["final"]["drilling_cost"] == pytest.approx(80.0)
    assert part["comparisons"]["roughing"]["used"] == "original"
    assert part["comparisons"]["milling"]["used"] == "none"
    assert part["comparisons"]["drilling"]["used"] == "base"

    assert len(db_calls) == 2
    assert any("UPDATE subgraphs" in sql for sql, _params in db_calls)
    assert any("processing_cost_calculation_details" in sql for sql, _params in db_calls)


def test_nc_total_calculator_returns_note_when_total_missing():
    from mold_cost.domain.pricing.calculators import price_nc_total as module

    result = asyncio.run(module.calculate({"other": {}}, job_id="job-nc-total-2"))

    assert result == {
        "job_id": "job-nc-total-2",
        "results": [],
        "note": "Missing total data, skipped NC total cost calculation",
    }
