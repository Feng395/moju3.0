from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()

MODULE_PATH = "mold_cost.domain.pricing.calculators.price_water_mill_plate"


def _load_module():
    return importlib.import_module(MODULE_PATH)


def _patch_batch_upsert(monkeypatch, module):
    captured: list[tuple[list[dict], str, str]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)
    return captured


def test_water_mill_plate_calculator_happy_path_and_skip_paths(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-plate-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-small",
                            "part_name": "Small",
                            "length_mm": 200,
                            "width_mm": 120,
                            "thickness_mm": 10,
                            "has_auto_material": True,
                            "has_material_preparation": False,
                            "needs_heat_treatment": False,
                            "material": "45#",
                        },
                        {
                            "subgraph_id": "sg-plate",
                            "part_name": "Plate",
                            "length_mm": 600,
                            "width_mm": 300,
                            "thickness_mm": 20,
                            "has_auto_material": False,
                            "has_material_preparation": None,
                            "needs_heat_treatment": False,
                            "material": "45#",
                        },
                        {
                            "subgraph_id": "sg-long",
                            "part_name": "Long",
                            "length_mm": 600,
                            "width_mm": 200,
                            "thickness_mm": 100,
                            "has_auto_material": False,
                            "has_material_preparation": None,
                            "needs_heat_treatment": False,
                            "material": "Q235",
                        },
                    ],
                },
                "water_mill": {
                    "l_water_mill_prices": [
                        {"sub_category": "plate", "price": 0.15, "unit": "元/mm2"},
                        {"sub_category": "plate", "price": 1290, "unit": "mm2"},
                    ]
                },
            }
        )
    )

    assert result["job_id"] == "job-plate-1"
    assert len(result["results"]) == 3

    small, plate, long_strip = result["results"]
    assert small["mill_type"] == "s_water_mill"
    assert small["plate_cost"] == pytest.approx(0.0)
    assert "小水磨" in small["note"]

    assert plate["mill_type"] == "l_water_mill"
    assert plate["part_type"] == "plate"
    assert plate["plate_cost"] == pytest.approx(20.93)
    assert plate["unit_price"] == pytest.approx(0.15)

    assert long_strip["part_type"] == "long_strip"
    assert long_strip["plate_cost"] == pytest.approx(0.0)
    assert long_strip["note"]

    assert module.MCP_TOOL_META["handler"] == "calculate"
    assert module.MCP_TOOL_META["needs"] == ["base_itemcode", "water_mill"]

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "water_mill_plate"
    assert field_name == "plate_cost"
    assert len(updates) == 2
    assert updates[0]["subgraph_id"] == "sg-small"
    assert updates[0]["value"] == pytest.approx(0.0)
    assert updates[1]["subgraph_id"] == "sg-plate"
    assert updates[1]["value"] == pytest.approx(20.930232558139537)


def test_water_mill_plate_calculator_sync_wrapper_and_heat_branch(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = module.calculate_sync(
        {
            "base_itemcode": {
                "job_id": "job-plate-2",
                "parts": [
                    {
                        "subgraph_id": "sg-heat-45",
                        "part_name": "Heat 45",
                        "length_mm": 500,
                        "width_mm": 280,
                        "thickness_mm": 20,
                        "has_auto_material": False,
                        "has_material_preparation": None,
                        "needs_heat_treatment": True,
                        "material": "45#",
                    },
                    {
                        "subgraph_id": "sg-heat-other",
                        "part_name": "Heat Other",
                        "length_mm": 400,
                        "width_mm": 350,
                        "thickness_mm": 20,
                        "has_auto_material": False,
                        "has_material_preparation": None,
                        "needs_heat_treatment": True,
                        "material": "Cr12mov",
                    },
                ],
            },
            "water_mill": {
                "l_water_mill_prices": [
                    {"sub_category": "plate", "price": 0.17, "unit": "元/mm2"},
                    {"sub_category": "plate", "price": 0.2, "unit": "元/mm2"},
                    {"sub_category": "plate", "price": 1290, "unit": "mm2"},
                ]
            },
        }
    )

    assert result["job_id"] == "job-plate-2"
    assert len(result["results"]) == 2
    heat_45, heat_other = result["results"]
    assert heat_45["plate_cost"] == pytest.approx(18.45)
    assert heat_45["unit_price"] == pytest.approx(0.17)
    assert heat_other["plate_cost"] == pytest.approx(21.71)
    assert heat_other["unit_price"] == pytest.approx(0.2)

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "water_mill_plate"
    assert field_name == "plate_cost"
    assert len(updates) == 2
    assert updates[0]["subgraph_id"] == "sg-heat-45"
    assert updates[0]["value"] == pytest.approx(18.449612403100776)
    assert updates[1]["subgraph_id"] == "sg-heat-other"
    assert updates[1]["value"] == pytest.approx(21.705426356589148)


def test_water_mill_plate_module_no_longer_imports_legacy_script():
    from mold_cost.domain.pricing.calculators import price_water_mill_plate as module

    source = Path(module.__file__).read_text(encoding="utf-8-sig")
    assert "scripts.calculate.price_water_mill_plate" not in source
