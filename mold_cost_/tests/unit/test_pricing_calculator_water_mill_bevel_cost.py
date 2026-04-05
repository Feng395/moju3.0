from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()

MODULE_PATH = "mold_cost.domain.pricing.calculators.price_water_mill_bevel_cost"


def _load_module():
    return importlib.import_module(MODULE_PATH)


def _patch_batch_upsert(monkeypatch, module):
    captured: list[tuple[list[dict], str, str]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)
    return captured


def test_water_mill_bevel_calculator_small_and_large_paths(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-bevel-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-small",
                            "part_name": "Small",
                            "has_auto_material": True,
                            "has_material_preparation": False,
                            "water_mill": {
                                "water_mill_details": [
                                    {"bevel": [4, 12]},
                                ]
                            },
                        },
                        {
                            "subgraph_id": "sg-large",
                            "part_name": "Large",
                            "has_auto_material": False,
                            "has_material_preparation": None,
                            "water_mill": {
                                "water_mill_details": [
                                    {"bevel": 6},
                                ]
                            },
                        },
                    ],
                },
                "water_mill": {
                    "s_water_mill_prices": [
                        {"sub_category": "bevel", "price": 15.0, "unit": "piece", "min_num": "(0,10)"},
                        {"sub_category": "bevel", "price": 20.0, "unit": "piece", "min_num": "[10,9999)"},
                    ]
                },
            }
        )
    )

    assert result["job_id"] == "job-bevel-1"
    assert len(result["results"]) == 2

    small = result["results"][0]
    assert small["subgraph_id"] == "sg-small"
    assert small["mill_type"] == "s_water_mill"
    assert small["bevel_cost"] == pytest.approx(35.0)
    assert len(small["bevel_details"]) == 2

    large = result["results"][1]
    assert large["subgraph_id"] == "sg-large"
    assert large["mill_type"] == "l_water_mill"
    assert large["bevel_cost"] == pytest.approx(0.0)
    assert large["note"] == "large water mill does not calculate bevel cost"

    assert module.MCP_TOOL_META["handler"] == "calculate"
    assert module.MCP_TOOL_META["needs"] == ["base_itemcode", "water_mill"]

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "water_mill_bevel"
    assert field_name == "bevel_cost"
    assert len(updates) == 2
    assert updates[0]["job_id"] == "job-bevel-1"
    assert updates[0]["subgraph_id"] == "sg-small"
    assert updates[0]["value"] == pytest.approx(35.0)
    assert len(updates[0]["steps"]) == 4
    assert updates[1]["job_id"] == "job-bevel-1"
    assert updates[1]["subgraph_id"] == "sg-large"
    assert updates[1]["value"] == pytest.approx(0.0)
    assert len(updates[1]["steps"]) == 2


def test_water_mill_bevel_calculator_sync_wrapper_and_missing_data(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = module.calculate_sync(
        {
            "base_itemcode": {
                "job_id": "job-bevel-2",
                "parts": [
                    {
                        "subgraph_id": "sg-missing",
                        "part_name": "Missing",
                        "has_auto_material": True,
                        "has_material_preparation": True,
                        "water_mill": {},
                    }
                ],
            },
            "water_mill": {
                "s_water_mill_prices": [],
            },
        },
        subgraph_ids=["sg-missing"],
    )

    assert result["job_id"] == "job-bevel-2"
    assert len(result["results"]) == 1
    assert result["results"][0]["bevel_cost"] == pytest.approx(0.0)
    assert result["results"][0]["note"] == "missing water_mill_details"
    assert captured == []


def test_water_mill_bevel_module_no_longer_imports_legacy_script():
    from mold_cost.domain.pricing.calculators import price_water_mill_bevel_cost as module

    source = Path(module.__file__).read_text(encoding="utf-8-sig")
    assert "scripts.calculate.price_water_mill_bevel_cost" not in source
