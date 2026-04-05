from __future__ import annotations

import asyncio
import importlib
import json
from pathlib import Path

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()

MODULE_PATH = "mold_cost.domain.pricing.calculators.price_tooth_hole"


def _load_module():
    return importlib.import_module(MODULE_PATH)


def _patch_batch_upsert(monkeypatch, module):
    captured: list[tuple[list[dict], str, str]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)
    return captured


def test_tooth_hole_calculator_happy_path_and_missing_details(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-tooth-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-1",
                            "part_name": "Plate A",
                            "tooth_hole": json.dumps(
                                {
                                    "tooth_hole_details": [
                                        {
                                            "code": "H1",
                                            "size": "M8",
                                            "number": 2,
                                            "is_through": "t",
                                            "set_screw": "f",
                                            "view": "top_view",
                                        },
                                        {
                                            "code": "H2",
                                            "size": "M12",
                                            "number": 1,
                                            "is_through": "f",
                                            "set_screw": "t",
                                            "view": "front_view",
                                        },
                                    ]
                                }
                            ),
                        },
                        {
                            "subgraph_id": "sg-2",
                            "part_name": "Plate B",
                            "tooth_hole": {},
                        },
                    ],
                },
                "tooth_hole": {
                    "tooth_hole_prices": [
                        {"sub_category": "through_hole", "price": 0.2, "unit": "小时", "min_num": "<M10"},
                        {"sub_category": "through_hole", "price": 0.4, "unit": "小时", "min_num": ">=M10"},
                        {"sub_category": "through_hole", "price": 50.0, "unit": "元/小时"},
                        {"sub_category": "blind_hole", "price": 0.3, "unit": "小时", "min_num": "<M10"},
                        {"sub_category": "blind_hole", "price": 0.6, "unit": "小时", "min_num": ">=M10"},
                        {"sub_category": "blind_hole", "price": 60.0, "unit": "元/小时"},
                    ],
                    "screw_prices": [
                        {"sub_category": "M8", "price": 6.806, "unit": "mm"},
                    ],
                    "stop_screw_prices": [
                        {"sub_category": "M12", "price": 10.505, "unit": "mm"},
                    ],
                },
            }
        )
    )

    assert result["job_id"] == "job-tooth-1"
    assert len(result["results"]) == 2

    first, second = result["results"]
    assert first["subgraph_id"] == "sg-1"
    assert first["part_name"] == "Plate A"
    assert first["tooth_hole_cost"] == pytest.approx(56.0)
    assert first["tooth_hole_time_cost"] == pytest.approx(1.0)
    assert first["total_perimeter"] == pytest.approx(42.76, rel=1e-4)
    assert first["perimeter_by_view"]["top_view"] == pytest.approx(42.76, rel=1e-4)

    assert second["subgraph_id"] == "sg-2"
    assert second["part_name"] == "Plate B"
    assert second["tooth_hole_cost"] == pytest.approx(0.0)
    assert second["tooth_hole_time_cost"] == pytest.approx(0.0)
    assert second["total_perimeter"] == pytest.approx(0.0)
    assert "perimeter_by_view" not in second

    assert module.MCP_TOOL_META["handler"] == "calculate"
    assert module.MCP_TOOL_META["needs"] == ["base_itemcode", "tooth_hole"]

    assert len(captured) == 2
    cost_updates, cost_category, cost_field_name = captured[0]
    time_updates, time_category, time_field_name = captured[1]

    assert cost_category == "tooth_hole"
    assert cost_field_name == "tooth_hole_cost"
    assert len(cost_updates) == 1
    assert cost_updates[0]["job_id"] == "job-tooth-1"
    assert cost_updates[0]["subgraph_id"] == "sg-1"
    assert cost_updates[0]["value"] == pytest.approx(56.0)
    assert len(cost_updates[0]["steps"]) == 7

    assert time_category == "tooth_hole_time"
    assert time_field_name == "tooth_hole_time_cost"
    assert len(time_updates) == 1
    assert time_updates[0]["job_id"] == "job-tooth-1"
    assert time_updates[0]["subgraph_id"] == "sg-1"
    assert time_updates[0]["value"] == pytest.approx(1.0)
    assert time_updates[0]["steps"] == []


def test_tooth_hole_calculator_sync_wrapper_and_zero_result(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = module.calculate_sync(
        {
            "base_itemcode": {
                "job_id": "job-tooth-2",
                "parts": [
                    {
                        "subgraph_id": "sg-3",
                        "part_name": "Plate C",
                        "tooth_hole": None,
                    }
                ],
            },
            "tooth_hole": {
                "tooth_hole_prices": [],
                "screw_prices": [],
                "stop_screw_prices": [],
            },
        }
    )

    assert result["job_id"] == "job-tooth-2"
    assert len(result["results"]) == 1
    part = result["results"][0]
    assert part["tooth_hole_cost"] == pytest.approx(0.0)
    assert part["tooth_hole_time_cost"] == pytest.approx(0.0)
    assert part["total_perimeter"] == pytest.approx(0.0)
    assert captured == []


def test_tooth_hole_module_no_longer_imports_legacy_script():
    from mold_cost.domain.pricing.calculators import price_tooth_hole as module

    source = Path(module.__file__).read_text(encoding="utf-8-sig")
    assert "scripts.calculate.price_tooth_hole" not in source
