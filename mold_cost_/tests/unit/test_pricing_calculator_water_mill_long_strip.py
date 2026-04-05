from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def _patch_batch_upsert(monkeypatch, module):
    captured: list[tuple[list[dict], str, str]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)
    return captured


def test_long_strip_calculator_happy_path(monkeypatch):
    from mold_cost.domain.pricing.calculators import price_water_mill_long_strip as module

    captured = _patch_batch_upsert(monkeypatch, module)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-long-strip-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-1",
                            "part_name": "Long Strip Part",
                            "length_mm": 600,
                            "width_mm": 200,
                            "thickness_mm": 100,
                            "quantity": 2,
                            "has_auto_material": False,
                            "has_material_preparation": None,
                        }
                    ],
                },
                "water_mill": {
                    "l_water_mill_prices": [
                        {"sub_category": "long_strip", "price": 0.8, "unit": "小时/件", "min_num": "(0, 300)"},
                        {"sub_category": "long_strip", "price": 1.0, "unit": "小时/件", "min_num": "[300, 500)"},
                        {"sub_category": "long_strip", "price": 1.4, "unit": "小时/件", "min_num": "[500, +)"},
                    ]
                },
            }
        )
    )

    assert result["job_id"] == "job-long-strip-1"
    assert len(result["results"]) == 1
    part = result["results"][0]
    assert part["mill_type"] == "l_water_mill"
    assert part["part_type"] == "long_strip"
    assert part["max_length"] == pytest.approx(600)
    assert part["unit_price"] == pytest.approx(1.4)
    assert part["long_strip_cost"] == pytest.approx(1.4)

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "water_mill_long_strip"
    assert field_name == "long_strip_cost"
    assert len(updates) == 1
    assert updates[0]["job_id"] == "job-long-strip-1"
    assert updates[0]["subgraph_id"] == "sg-1"
    assert updates[0]["value"] == pytest.approx(1.4)
    assert len(updates[0]["steps"]) == 5


def test_long_strip_calculator_small_mill_and_non_long_strip(monkeypatch):
    from mold_cost.domain.pricing.calculators import price_water_mill_long_strip as module

    captured = _patch_batch_upsert(monkeypatch, module)

    result = module.calculate_sync(
        {
            "base_itemcode": {
                "job_id": "job-long-strip-2",
                "parts": [
                    {
                        "subgraph_id": "sg-small",
                        "part_name": "Small Mill Part",
                        "length_mm": 600,
                        "width_mm": 200,
                        "thickness_mm": 100,
                        "has_auto_material": True,
                        "has_material_preparation": False,
                    },
                    {
                        "subgraph_id": "sg-component",
                        "part_name": "Component Part",
                        "length_mm": 100,
                        "width_mm": 80,
                        "thickness_mm": 60,
                        "has_auto_material": False,
                        "has_material_preparation": None,
                    },
                ],
            },
            "water_mill": {
                "l_water_mill_prices": [
                    {"sub_category": "long_strip", "price": 1.2, "unit": "小时/件", "min_num": "[0, +]"}
                ]
            },
        }
    )

    assert result["job_id"] == "job-long-strip-2"
    assert len(result["results"]) == 2

    small_mill = result["results"][0]
    assert small_mill["mill_type"] == "s_water_mill"
    assert small_mill["long_strip_cost"] == pytest.approx(0.0)
    assert small_mill["note"] == "小水磨不计算长条费"

    component = result["results"][1]
    assert component["mill_type"] == "l_water_mill"
    assert component["part_type"] == "component"
    assert component["long_strip_cost"] == pytest.approx(0.0)
    assert component["note"] == "不是长条类型"

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "water_mill_long_strip"
    assert field_name == "long_strip_cost"
    assert len(updates) == 1
    assert updates[0]["subgraph_id"] == "sg-small"
    assert updates[0]["value"] == pytest.approx(0.0)
    assert len(updates[0]["steps"]) == 2


def test_long_strip_module_no_longer_imports_legacy_script():
    from mold_cost.domain.pricing.calculators import price_water_mill_long_strip as module

    source = Path(module.__file__).read_text(encoding="utf-8-sig")
    assert "scripts.calculate.price_water_mill_long_strip" not in source
