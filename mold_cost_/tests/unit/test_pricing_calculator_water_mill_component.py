from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_water_mill_component_calculator_happy_path_and_multiplier(monkeypatch):
    from mold_cost.domain.pricing.calculators import price_water_mill_component as module

    captured: list[tuple[list[dict], str, str]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-comp-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-1",
                            "part_name": "Component A",
                            "length_mm": 100,
                            "width_mm": 80,
                            "thickness_mm": 60,
                            "has_auto_material": False,
                            "has_material_preparation": None,
                            "water_mill": {"water_mill_details": [{"grinding": 6}]},
                        },
                        {
                            "subgraph_id": "sg-2",
                            "part_name": "Component B",
                            "length_mm": 120,
                            "width_mm": 70,
                            "thickness_mm": 50,
                            "has_auto_material": False,
                            "has_material_preparation": None,
                            "water_mill": json.dumps({"water_mill_details": [{"grinding": 4}]}),
                        },
                    ],
                },
                "water_mill": {
                    "l_water_mill_prices": [
                        {"sub_category": "component", "price": "1", "unit": "hour", "min_num": "6, (0,200)"},
                        {"sub_category": "component", "price": "1/2", "unit": "hour", "min_num": "4"},
                    ]
                },
            }
        )
    )

    assert result["job_id"] == "job-comp-1"
    assert len(result["results"]) == 2

    first, second = result["results"]
    assert first["subgraph_id"] == "sg-1"
    assert first["mill_type"] == "l_water_mill"
    assert first["part_type"] == "component"
    assert first["grinding"] == 6
    assert first["component_cost"] == pytest.approx(1.0)

    assert second["subgraph_id"] == "sg-2"
    assert second["component_cost"] == pytest.approx(0.5)

    assert module.MCP_TOOL_META["handler"] == "calculate"
    assert module.MCP_TOOL_META["needs"] == ["base_itemcode", "water_mill"]

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "water_mill_component"
    assert field_name == "component_cost"
    assert len(updates) == 2
    assert updates[0]["job_id"] == "job-comp-1"
    assert updates[0]["subgraph_id"] == "sg-1"
    assert updates[0]["value"] == pytest.approx(1.0)
    assert updates[1]["subgraph_id"] == "sg-2"
    assert updates[1]["value"] == pytest.approx(0.5)


def test_water_mill_component_calculator_sync_wrapper_and_zero_result(monkeypatch):
    from mold_cost.domain.pricing.calculators import price_water_mill_component as module

    captured: list[tuple[list[dict], str, str]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)

    result = module.calculate_sync(
        {
            "base_itemcode": {
                "job_id": "job-comp-2",
                "parts": [
                    {
                        "subgraph_id": "keep",
                        "part_name": "Plate",
                        "length_mm": 500,
                        "width_mm": 400,
                        "thickness_mm": 100,
                        "has_auto_material": False,
                        "has_material_preparation": None,
                        "water_mill": {"water_mill_details": [{"grinding": 6}]},
                    },
                    {
                        "subgraph_id": "skip",
                        "part_name": "Skip",
                        "length_mm": 80,
                        "width_mm": 60,
                        "thickness_mm": 40,
                        "has_auto_material": True,
                        "has_material_preparation": None,
                        "water_mill": {"water_mill_details": [{"grinding": 6}]},
                    },
                ],
            },
            "water_mill": {
                "l_water_mill_prices": [
                    {"sub_category": "component", "price": 1.0, "unit": "hour", "min_num": "6, (0,200)"},
                ]
            },
        },
        subgraph_ids=["keep"],
    )

    assert result["job_id"] == "job-comp-2"
    assert len(result["results"]) == 1
    part = result["results"][0]
    assert part["subgraph_id"] == "keep"
    assert part["part_type"] == "plate"
    assert part["component_cost"] == pytest.approx(0.0)
    assert captured == []


def test_water_mill_component_module_no_longer_imports_legacy_script():
    from mold_cost.domain.pricing.calculators import price_water_mill_component as module

    source = Path(module.__file__).read_text(encoding="utf-8-sig")
    assert "scripts.calculate.price_water_mill_component" not in source
