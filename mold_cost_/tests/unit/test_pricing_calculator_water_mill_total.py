from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()

MODULE_PATH = "mold_cost.domain.pricing.calculators.price_water_mill_total"


def _load_module():
    return importlib.import_module(MODULE_PATH)


def _patch_batch_upsert(monkeypatch, module):
    captured: list[tuple[list[dict], str, str | None]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)
    return captured


def test_water_mill_total_calculator_small_and_large_paths(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)
    updated_subgraphs: list[tuple[str, list[dict]]] = []

    async def fake_batch_update_subgraphs(job_id, updates):
        updated_subgraphs.append((job_id, list(updates)))

    monkeypatch.setattr(module, "_batch_update_subgraphs", fake_batch_update_subgraphs)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-water-total-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-small",
                            "part_name": "Insert A",
                            "quantity": 2,
                            "has_auto_material": True,
                            "has_material_preparation": False,
                        },
                        {
                            "subgraph_id": "sg-large",
                            "part_name": "Plate B",
                            "quantity": 3,
                            "has_auto_material": False,
                            "has_material_preparation": None,
                        },
                    ],
                },
                "total": {
                    "cost_details": [
                        {
                            "subgraph_id": "sg-small",
                            "thread_ends_cost": 10.0,
                            "hanging_table_cost": 5.0,
                            "high_cost": 2.0,
                            "chamfer_cost": 30.0,
                            "bevel_cost": 15.0,
                            "oil_tank_cost": 1.5,
                        },
                        {
                            "subgraph_id": "sg-large",
                            "plate_cost": 8.0,
                            "long_strip_cost": 1.0,
                            "component_cost": 0.5,
                        },
                    ]
                },
                "water_mill": {
                    "s_water_mill_prices": [
                        {"sub_category": "water_mill", "price": 50.0, "unit": "yuan/hour"},
                    ],
                    "l_water_mill_prices": [
                        {"sub_category": "water_mill", "price": 60.0, "unit": "yuan/hour"},
                    ],
                },
            }
        )
    )

    assert result["job_id"] == "job-water-total-1"
    assert len(result["results"]) == 2

    small = result["results"][0]
    assert small["subgraph_id"] == "sg-small"
    assert small["mill_type"] == "s_water_mill"
    assert small["small_grinding_cost"] == pytest.approx(242.0)
    assert small["small_grinding_time"] == pytest.approx(4.5)
    assert small["large_grinding_cost"] == pytest.approx(0.0)
    assert small["large_grinding_time"] == pytest.approx(0.0)

    large = result["results"][1]
    assert large["subgraph_id"] == "sg-large"
    assert large["mill_type"] == "l_water_mill"
    assert large["small_grinding_cost"] == pytest.approx(0.0)
    assert large["small_grinding_time"] == pytest.approx(0.0)
    assert large["large_grinding_cost"] == pytest.approx(294.0)
    assert large["large_grinding_time"] == pytest.approx(4.5)

    assert module.MCP_TOOL_META["handler"] == "calculate"
    assert module.MCP_TOOL_META["needs"] == ["base_itemcode", "total", "water_mill"]

    assert len(captured) == 2
    small_updates, small_category, small_field_name = captured[0]
    large_updates, large_category, large_field_name = captured[1]

    assert small_category == "water_mill_total_small"
    assert small_field_name is None
    assert len(small_updates) == 1
    assert small_updates[0]["job_id"] == "job-water-total-1"
    assert small_updates[0]["subgraph_id"] == "sg-small"
    assert small_updates[0]["value"] == pytest.approx(242.0)
    assert len(small_updates[0]["steps"]) == 4

    assert large_category == "water_mill_total_large"
    assert large_field_name is None
    assert len(large_updates) == 1
    assert large_updates[0]["subgraph_id"] == "sg-large"
    assert large_updates[0]["value"] == pytest.approx(294.0)
    assert len(large_updates[0]["steps"]) == 3

    assert len(updated_subgraphs) == 1
    assert updated_subgraphs[0][0] == "job-water-total-1"
    assert len(updated_subgraphs[0][1]) == 2


def test_water_mill_total_calculator_sync_wrapper_and_subgraph_filter(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)
    updated_subgraphs: list[tuple[str, list[dict]]] = []

    async def fake_batch_update_subgraphs(job_id, updates):
        updated_subgraphs.append((job_id, list(updates)))

    monkeypatch.setattr(module, "_batch_update_subgraphs", fake_batch_update_subgraphs)

    result = module.calculate_sync(
        {
            "base_itemcode": {
                "job_id": "job-water-total-2",
                "parts": [
                    {
                        "subgraph_id": "keep",
                        "part_name": "Keep Me",
                        "quantity": 1,
                        "has_auto_material": False,
                        "has_material_preparation": None,
                    },
                    {
                        "subgraph_id": "skip",
                        "part_name": "Skip Me",
                        "quantity": 1,
                        "has_auto_material": True,
                        "has_material_preparation": True,
                    },
                ],
            },
            "total": {
                "cost_details": [
                    {
                        "subgraph_id": "keep",
                        "plate_cost": 4.0,
                        "long_strip_cost": 0.25,
                        "component_cost": 0.25,
                    },
                    {
                        "subgraph_id": "skip",
                        "thread_ends_cost": 1.0,
                        "hanging_table_cost": 1.0,
                        "high_cost": 1.0,
                        "chamfer_cost": 10.0,
                        "bevel_cost": 20.0,
                        "oil_tank_cost": 0.5,
                    },
                ]
            },
            "water_mill": {
                "s_water_mill_prices": [{"sub_category": "s-1", "price": 50.0}],
                "l_water_mill_prices": [{"sub_category": "l-1", "price": 60.0}],
            },
        },
        subgraph_ids=["keep"],
    )

    assert result["job_id"] == "job-water-total-2"
    assert len(result["results"]) == 1
    part = result["results"][0]
    assert part["subgraph_id"] == "keep"
    assert part["large_grinding_cost"] == pytest.approx(34.0)
    assert part["large_grinding_time"] == pytest.approx(0.5)
    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "water_mill_total_large"
    assert field_name is None
    assert len(updates) == 1
    assert updates[0]["job_id"] == "job-water-total-2"
    assert updates[0]["subgraph_id"] == "keep"
    assert updates[0]["value"] == pytest.approx(34.0)
    assert len(updates[0]["steps"]) == 3
    assert updated_subgraphs[0][0] == "job-water-total-2"
    assert len(updated_subgraphs[0][1]) == 1


def test_water_mill_total_module_no_longer_imports_legacy_script():
    from mold_cost.domain.pricing.calculators import price_water_mill_total as module

    source = Path(module.__file__).read_text(encoding="utf-8-sig")
    assert "scripts.calculate.price_water_mill_total" not in source
