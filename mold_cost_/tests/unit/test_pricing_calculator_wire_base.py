from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()

MODULE_PATH = "mold_cost.domain.pricing.calculators.price_wire_base"


def _load_module():
    return importlib.import_module(MODULE_PATH)


def _patch_batch_upsert(monkeypatch, module):
    captured: list[tuple[list[dict], str, str]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)
    return captured


def test_wire_base_calculator_happy_path_with_tooth_hole_and_rules(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-wire-base-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-1",
                            "part_name": "Part A",
                            "wire_process": "fast_cut",
                            "length_mm": 100,
                            "width_mm": 50,
                            "thickness_mm": 12,
                            "has_auto_material": True,
                            "needs_heat_treatment": True,
                            "metadata": {
                                "wire_cut_details": [
                                    {
                                        "code": "W1",
                                        "view": "top_view",
                                        "total_length": 10,
                                        "slider_angle": 0,
                                        "instruction": "top",
                                        "area_num": 2,
                                        "cone": "t",
                                    },
                                    {
                                        "code": "W2",
                                        "view": "front_view",
                                        "total_length": 6,
                                        "slider_angle": 5,
                                        "instruction": "front",
                                        "area_num": 0,
                                        "cone": "f",
                                    },
                                ]
                            },
                        }
                    ],
                },
                "wire_base": {
                    "wire_parts": [
                        {
                            "conditions": "fast_cut",
                            "description": "Fast cut",
                            "price": 10,
                            "unit": "hour",
                            "min_num": "[0,+)",
                        }
                    ],
                    "rule_prices": [
                        {"sub_category": "area_num", "price": 2.0},
                        {"sub_category": "extra_thick", "price": 1.5, "min_num": "[15,20)"},
                        {"sub_category": "slider", "price": 2.0, "min_num": "[1,10)"},
                    ],
                },
                "tooth_hole": {
                    "results": [
                        {
                            "subgraph_id": "sg-1",
                            "perimeter_by_view": {"top_view": 3.0},
                        }
                    ]
                },
            },
            job_id="job-wire-base-1",
            subgraph_ids=["sg-1"],
        )
    )

    assert result["job_id"] == "job-wire-base-1"
    assert len(result["results"]) == 1

    part = result["results"][0]
    assert part["subgraph_id"] == "sg-1"
    assert part["part_name"] == "Part A"
    assert part["process_description"] == "Fast cut"
    assert part["conditions"] == "fast_cut"
    assert part["status"] == "ok"
    assert part["basic_processing_cost"] == pytest.approx(5857.5)

    assert module.MCP_TOOL_META["handler"] == "calculate"
    assert module.MCP_TOOL_META["needs"] == ["base_itemcode", "wire_base"]
    assert module.MCP_TOOL_META["optional"] == ["tooth_hole"]

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "wire_base"
    assert field_name == "basic_processing_cost"
    assert len(updates) == 1
    assert updates[0]["job_id"] == "job-wire-base-1"
    assert updates[0]["subgraph_id"] == "sg-1"
    assert updates[0]["value"] == pytest.approx(5857.5)
    assert len(updates[0]["steps"]) >= 5


def test_wire_base_calculator_handles_missing_metadata(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = module.calculate_sync(
        {
            "base_itemcode": {
                "job_id": "job-wire-base-2",
                "parts": [
                    {
                        "subgraph_id": "sg-2",
                        "part_name": "Part B",
                        "wire_process": "fast_cut",
                        "length_mm": 80,
                        "width_mm": 40,
                        "thickness_mm": 10,
                        "metadata": None,
                    }
                ],
            },
            "wire_base": {
                "wire_parts": [
                    {
                        "conditions": "fast_cut",
                        "description": "Fast cut",
                        "price": 10,
                        "unit": "hour",
                        "min_num": "[0,+)",
                    }
                ],
                "rule_prices": [],
            },
        }
    )

    assert result["job_id"] == "job-wire-base-2"
    assert len(result["results"]) == 1
    part = result["results"][0]
    assert part["basic_processing_cost"] == pytest.approx(0.0)
    assert part["status"] == "error"
    assert "metadata" in part["note"]

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "wire_base"
    assert field_name == "basic_processing_cost"
    assert updates[0]["value"] == pytest.approx(0.0)
    assert updates[0]["steps"][0]["step"] == "检查metadata"


def test_wire_base_module_no_longer_imports_legacy_script():
    from mold_cost.domain.pricing.calculators import price_wire_base as module

    source = Path(module.__file__).read_text(encoding="utf-8-sig")
    assert "scripts.calculate.price_wire_base" not in source
