from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()

MODULE_PATH = "mold_cost.domain.pricing.calculators.price_heat"


def _load_module():
    return importlib.import_module(MODULE_PATH)


def _patch_batch_upsert(monkeypatch, module):
    captured: list[tuple[list[dict], str, str]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)
    return captured


def test_heat_calculator_happy_path_alias_and_density(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-heat-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-1",
                            "part_name": "Plate A",
                            "needs_heat_treatment": True,
                            "material": "toolox33",
                            "length_mm": 100,
                            "width_mm": 50,
                            "thickness_mm": 10,
                        }
                    ],
                },
                "heat": {
                    "heat_prices": [
                        {
                            "sub_category": "T00L0X33",
                            "price": 12.5,
                            "unit": "kg",
                        }
                    ]
                },
                "density": {
                    "density_data": [
                        {
                            "sub_category": "T00L0X33",
                            "price": 0.00000785,
                            "unit": "g/cm³",
                        }
                    ]
                },
            },
            job_id="job-heat-1",
            subgraph_ids=["sg-1"],
        )
    )

    assert result["job_id"] == "job-heat-1"
    assert len(result["results"]) == 1

    part = result["results"][0]
    assert part["subgraph_id"] == "sg-1"
    assert part["part_name"] == "Plate A"
    assert part["needs_heat_treatment"] is True
    assert part["material"] == "toolox33"
    assert part["weight"] == pytest.approx(0.3925)
    assert part["unit_price"] == pytest.approx(12.5)
    assert part["unit"] == "kg"
    assert part["heat_treatment_cost"] == pytest.approx(4.91)

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "heat"
    assert field_name == "heat_treatment_cost"
    assert len(updates) == 1
    update = updates[0]
    assert update["job_id"] == "job-heat-1"
    assert update["subgraph_id"] == "sg-1"
    assert update["value"] == pytest.approx(4.91)

    steps = update["steps"]
    assert len(steps) == 6
    assert steps[0]["step"] == "判断是否需要热处理"
    assert steps[0]["needs_heat_treatment"] is True
    assert steps[1]["step"] == "匹配热处理价格"
    assert steps[1]["material"] == "toolox33"
    assert steps[1]["matched_sub_category"] == "T00L0X33"
    assert steps[1]["unit_price"] == pytest.approx(12.5)
    assert steps[2]["step"] == "匹配材料密度"
    assert steps[2]["matched_material"] == "T00L0X33"
    assert steps[2]["density"] == pytest.approx(0.00000785)
    assert steps[3]["step"] == "获取尺寸数据"
    assert steps[3]["length_mm"] == pytest.approx(100.0)
    assert steps[3]["width_mm"] == pytest.approx(50.0)
    assert steps[3]["thickness_mm"] == pytest.approx(10.0)
    assert steps[4]["step"] == "计算重量"
    assert steps[4]["weight"] == pytest.approx(0.3925)
    assert steps[5]["step"] == "计算热处理费"
    assert steps[5]["heat_treatment_cost"] == pytest.approx(4.91)

    assert module.MCP_TOOL_META["handler"] == "calculate"
    assert module.MCP_TOOL_META["needs"] == ["base_itemcode", "heat", "density"]


def test_heat_calculator_skips_when_no_heat_treatment(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-heat-2",
                    "parts": [
                        {
                            "subgraph_id": "sg-2",
                            "part_name": "Plate B",
                            "needs_heat_treatment": False,
                            "material": "45#",
                            "length_mm": 80,
                            "width_mm": 20,
                            "thickness_mm": 5,
                        }
                    ],
                },
                "heat": {
                    "heat_prices": [
                        {
                            "sub_category": "45#",
                            "price": 8.0,
                            "unit": "kg",
                        }
                    ]
                },
                "density": {"density_data": []},
            }
        )
    )

    part = result["results"][0]
    assert part["needs_heat_treatment"] is False
    assert part["heat_treatment_cost"] == pytest.approx(0.0)
    assert part["note"] == "不需要热处理"

    steps = captured[0][0][0]["steps"]
    assert steps[0]["step"] == "判断是否需要热处理"
    assert steps[0]["needs_heat_treatment"] is False
    assert steps[0]["heat_treatment_cost"] == pytest.approx(0.0)


def test_heat_calculator_records_validation_and_price_failures(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-heat-3",
                    "parts": [
                        {
                            "subgraph_id": "sg-3",
                            "part_name": "Plate C",
                            "needs_heat_treatment": True,
                            "material": "Q235",
                            "length_mm": 100,
                            "width_mm": None,
                            "thickness_mm": 10,
                        },
                        {
                            "subgraph_id": "sg-4",
                            "part_name": "Plate D",
                            "needs_heat_treatment": True,
                            "material": "UNKNOWN",
                            "length_mm": 100,
                            "width_mm": 50,
                            "thickness_mm": 10,
                        },
                    ],
                },
                "heat": {
                    "heat_prices": [
                        {
                            "sub_category": "Q235",
                            "price": 7.0,
                            "unit": "kg",
                        }
                    ]
                },
                "density": {
                    "density_data": [
                        {
                            "sub_category": "Q235",
                            "price": 0.00000785,
                            "unit": "g/cm³",
                        }
                    ]
                },
            },
            job_id="job-heat-3",
        )
    )

    assert [item["heat_treatment_cost"] for item in result["results"]] == [0.0, 0.0]
    assert result["results"][0]["note"] == "缺少必需字段: width_mm"
    assert result["results"][1]["note"] == "未找到material对应的热处理价格: UNKNOWN"

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "heat"
    assert field_name == "heat_treatment_cost"
    assert [update["value"] for update in updates] == [0.0, 0.0]
    assert updates[0]["steps"][0]["status"] == "failed"
    assert updates[1]["steps"][0]["status"] == "failed"


def test_heat_module_no_longer_imports_legacy_script():
    from mold_cost.domain.pricing.calculators import price_heat as module

    source = Path(module.__file__).read_text(encoding="utf-8-sig")
    assert "scripts.calculate.price_heat" not in source
