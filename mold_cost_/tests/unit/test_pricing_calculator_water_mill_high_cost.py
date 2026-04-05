from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_water_mill_high_cost_calculator_paths(monkeypatch):
    from mold_cost.domain.pricing.calculators import price_water_mill_high_cost as module

    captured: list[tuple[list[dict], str, str]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    fetch_calls: list[tuple[str, tuple[object, ...]]] = []

    async def fake_fetch_one(sql, *params):
        fetch_calls.append((sql, params))
        if "FROM subgraphs" in sql:
            return {"subgraph_id": "sg-prep"}
        if "FROM features" in sql:
            return {"thickness_mm": 12.0}
        return None

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)
    monkeypatch.setattr(module.db, "fetch_one", fake_fetch_one)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-high-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-small",
                            "part_name": "Small",
                            "has_auto_material": True,
                            "has_material_preparation": "B02",
                            "thickness_mm": 8.0,
                            "quantity": 3,
                        },
                        {
                            "subgraph_id": "sg-large",
                            "part_name": "Large",
                            "has_auto_material": False,
                            "has_material_preparation": None,
                            "thickness_mm": 20.0,
                            "quantity": 2,
                        },
                    ],
                },
                "water_mill": {
                    "s_water_mill_prices": [
                        {"sub_category": "high", "price": 2.5, "unit": "piece"},
                    ]
                },
            }
        )
    )

    assert result["job_id"] == "job-high-1"
    assert len(result["results"]) == 2

    small = result["results"][0]
    assert small["subgraph_id"] == "sg-small"
    assert small["mill_type"] == "s_water_mill"
    assert small["high_cost"] == pytest.approx(7.5)
    assert small["material_thickness"] == pytest.approx(12.0)
    assert small["current_thickness"] == pytest.approx(8.0)

    large = result["results"][1]
    assert large["subgraph_id"] == "sg-large"
    assert large["mill_type"] == "l_water_mill"
    assert large["high_cost"] == pytest.approx(0.0)
    assert large["note"] == "large water mill does not calculate high cost"

    assert module.MCP_TOOL_META["handler"] == "calculate"
    assert module.MCP_TOOL_META["needs"] == ["base_itemcode", "water_mill"]

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "water_mill_high"
    assert field_name == "high_cost"
    assert len(updates) == 2
    assert updates[0]["job_id"] == "job-high-1"
    assert updates[0]["subgraph_id"] == "sg-small"
    assert updates[0]["value"] == pytest.approx(7.5)
    assert len(updates[0]["steps"]) >= 6
    assert updates[1]["subgraph_id"] == "sg-large"
    assert updates[1]["value"] == pytest.approx(0.0)
    assert len(updates[1]["steps"]) == 2
    assert len(fetch_calls) == 2


def test_water_mill_high_cost_calculator_sync_wrapper_and_missing_preparation(monkeypatch):
    from mold_cost.domain.pricing.calculators import price_water_mill_high_cost as module

    captured: list[tuple[list[dict], str, str]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)

    result = module.calculate_sync(
        {
            "base_itemcode": {
                "job_id": "job-high-2",
                "parts": [
                    {
                        "subgraph_id": "sg-missing",
                        "part_name": "Missing",
                        "has_auto_material": True,
                        "has_material_preparation": None,
                        "thickness_mm": 10.0,
                        "quantity": 1,
                    }
                ],
            },
            "water_mill": {
                "s_water_mill_prices": [],
            },
        },
        subgraph_ids=["sg-missing"],
    )

    assert result["job_id"] == "job-high-2"
    assert len(result["results"]) == 1
    assert result["results"][0]["high_cost"] == pytest.approx(0.0)
    assert result["results"][0]["note"] == "missing material preparation"
    assert captured == []


def test_water_mill_high_cost_module_no_longer_imports_legacy_script():
    from mold_cost.domain.pricing.calculators import price_water_mill_high_cost as module

    source = Path(module.__file__).read_text(encoding="utf-8-sig")
    assert "scripts.calculate.price_water_mill_high_cost" not in source
