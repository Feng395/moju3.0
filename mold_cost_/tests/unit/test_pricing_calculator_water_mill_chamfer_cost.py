from __future__ import annotations

import asyncio
import importlib
import json
from pathlib import Path

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()

MODULE_PATH = "mold_cost.domain.pricing.calculators.price_water_mill_chamfer_cost"


def _load_module():
    return importlib.import_module(MODULE_PATH)


def _patch_batch_upsert(monkeypatch, module):
    captured: list[tuple[list[dict], str, str]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)
    return captured


def test_water_mill_chamfer_calculator_small_and_large_paths(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-water-chamfer-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-small",
                            "part_name": "Small Part",
                            "has_auto_material": True,
                            "has_material_preparation": False,
                            "water_mill": json.dumps(
                                {
                                    "water_mill_details": [
                                        {
                                            "c1_c2_chamfer": 1,
                                            "c3_c5_chamfer": 2,
                                            "r1_r2_chamfer": 3,
                                            "r3_r5_chamfer": 4,
                                        }
                                    ]
                                }
                            ),
                        },
                        {
                            "subgraph_id": "sg-large",
                            "part_name": "Large Part",
                            "has_auto_material": False,
                            "has_material_preparation": None,
                            "water_mill": {
                                "water_mill_details": [
                                    {
                                        "c1_c2_chamfer": 9,
                                        "c3_c5_chamfer": 8,
                                        "r1_r2_chamfer": 7,
                                        "r3_r5_chamfer": 6,
                                    }
                                ]
                            },
                        },
                    ],
                },
                "water_mill": {
                    "s_water_mill_prices": [
                        {"sub_category": "c1_c2_chamfer", "price": 2.0, "unit": "min"},
                        {"sub_category": "c3_c5_chamfer", "price": 3.0, "unit": "min"},
                        {"sub_category": "r1_r2_chamfer", "price": 5.0, "unit": "min"},
                        {"sub_category": "r3_r5_chamfer", "price": 7.0, "unit": "min"},
                    ]
                },
            }
        )
    )

    assert result["job_id"] == "job-water-chamfer-1"
    assert len(result["results"]) == 2

    small = result["results"][0]
    assert small["subgraph_id"] == "sg-small"
    assert small["mill_type"] == "s_water_mill"
    assert small["chamfer_cost"] == pytest.approx(51.0)
    assert small["chamfer_costs"]["c1_c2_chamfer"] == pytest.approx(2.0)
    assert small["chamfer_costs"]["r3_r5_chamfer"] == pytest.approx(28.0)

    large = result["results"][1]
    assert large["subgraph_id"] == "sg-large"
    assert large["mill_type"] == "l_water_mill"
    assert large["chamfer_cost"] == pytest.approx(0.0)
    assert "large water mill" in large["note"]

    assert module.MCP_TOOL_META["handler"] == "calculate"
    assert module.MCP_TOOL_META["needs"] == ["base_itemcode", "water_mill"]

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "water_mill_chamfer"
    assert field_name == "chamfer_cost"
    assert len(updates) == 2
    assert updates[0]["job_id"] == "job-water-chamfer-1"
    assert updates[0]["subgraph_id"] == "sg-small"
    assert updates[0]["value"] == pytest.approx(51.0)
    assert len(updates[0]["steps"]) == 7
    assert updates[1]["subgraph_id"] == "sg-large"
    assert updates[1]["value"] == pytest.approx(0.0)


def test_water_mill_chamfer_calculator_handles_missing_details_and_sync_wrapper(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = module.calculate_sync(
        {
            "base_itemcode": {
                "job_id": "job-water-chamfer-2",
                "parts": [
                    {
                        "subgraph_id": "sg-empty",
                        "part_name": "Empty",
                        "has_auto_material": True,
                        "has_material_preparation": False,
                        "water_mill": None,
                    }
                ],
            },
            "water_mill": {"s_water_mill_prices": []},
        }
    )

    assert result["job_id"] == "job-water-chamfer-2"
    assert len(result["results"]) == 1
    part = result["results"][0]
    assert part["chamfer_cost"] == pytest.approx(0.0)
    assert "note" in part
    assert captured == []


def test_water_mill_chamfer_module_no_longer_imports_legacy_script():
    from mold_cost.domain.pricing.calculators import price_water_mill_chamfer_cost as module

    source = Path(module.__file__).read_text(encoding="utf-8-sig")
    assert "scripts.calculate.price_water_mill_chamfer_cost" not in source
