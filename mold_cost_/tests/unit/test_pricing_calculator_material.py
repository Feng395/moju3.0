from __future__ import annotations

import asyncio
import importlib

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()


MODULE_PATH = "mold_cost.domain.pricing.calculators.price_material"


def _load_module():
    return importlib.import_module(MODULE_PATH)


def _patch_batch_upsert(monkeypatch, module):
    captured: list[tuple[list[dict], str, str]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)
    return captured


def test_material_calculator_happy_path_alias_and_density(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-material-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-1",
                            "part_name": "Plate A",
                            "material": "toolox33",
                            "length_mm": 100,
                            "width_mm": 50,
                            "thickness_mm": 10,
                        }
                    ],
                },
                "material": {
                    "material_prices": [
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
            job_id="job-material-1",
            subgraph_ids=["sg-1"],
        )
    )

    assert result["job_id"] == "job-material-1"
    assert len(result["results"]) == 1

    part = result["results"][0]
    assert part["subgraph_id"] == "sg-1"
    assert part["part_name"] == "Plate A"
    assert part["material"] == "toolox33"
    assert part["weight"] == pytest.approx(0.3925)
    assert part["unit_price"] == pytest.approx(12.5)
    assert part["unit"] == "kg"
    assert part["material_cost"] == pytest.approx(4.91)

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "material"
    assert field_name == "material_cost"
    assert len(updates) == 1
    update = updates[0]
    assert update["job_id"] == "job-material-1"
    assert update["subgraph_id"] == "sg-1"
    assert update["value"] == pytest.approx(4.91)

    steps = update["steps"]
    assert len(steps) == 5
    assert steps[0]["step"] == "匹配材料价格"
    assert steps[0]["material"] == "toolox33"
    assert steps[0]["matched_sub_category"] == "T00L0X33"
    assert steps[0]["unit_price"] == pytest.approx(12.5)
    assert steps[0]["unit"] == "kg"
    assert steps[1]["step"] == "匹配材料密度"
    assert steps[1]["matched_material"] == "T00L0X33"
    assert steps[1]["density"] == pytest.approx(0.00000785)
    assert steps[1]["unit"] == "g/cm³"
    assert steps[2]["step"] == "获取尺寸数据"
    assert steps[2]["length_mm"] == pytest.approx(100.0)
    assert steps[2]["width_mm"] == pytest.approx(50.0)
    assert steps[2]["thickness_mm"] == pytest.approx(10.0)
    assert steps[3]["step"] == "计算重量"
    assert steps[3]["weight"] == pytest.approx(0.3925)
    assert steps[4]["step"] == "计算材料费"
    assert steps[4]["material_cost"] == pytest.approx(4.91)
    assert module.MCP_TOOL_META["handler"] == "calculate"
    assert module.MCP_TOOL_META["needs"] == ["base_itemcode", "material", "density"]


def test_material_calculator_uses_default_density_when_missing(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-material-2",
                    "parts": [
                        {
                            "subgraph_id": "sg-2",
                            "part_name": "Plate B",
                            "material": "45#",
                            "length_mm": 80,
                            "width_mm": 20,
                            "thickness_mm": 5,
                        }
                    ],
                },
                "material": {
                    "material_prices": [
                        {
                            "sub_category": "45#",
                            "price": 9.1,
                            "unit": "kg",
                        }
                    ]
                },
                "density": {"density_data": []},
            }
        )
    )

    part = result["results"][0]
    assert part["weight"] == pytest.approx(0.0628)
    assert part["material_cost"] == pytest.approx(0.57)

    steps = captured[0][0][0]["steps"]
    assert steps[1]["matched_material"] == "45#(使用默认密度)"
    assert steps[1]["density"] == pytest.approx(0.00000785)


def test_material_calculator_records_validation_and_price_failures(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-material-3",
                    "parts": [
                        {
                            "subgraph_id": "sg-3",
                            "part_name": "Plate C",
                            "material": "Q235",
                            "length_mm": 100,
                            "width_mm": None,
                            "thickness_mm": 10,
                        },
                        {
                            "subgraph_id": "sg-4",
                            "part_name": "Plate D",
                            "material": "UNKNOWN",
                            "length_mm": 100,
                            "width_mm": 50,
                            "thickness_mm": 10,
                        },
                    ],
                },
                "material": {
                    "material_prices": [
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
            job_id="job-material-3",
        )
    )

    assert [item["material_cost"] for item in result["results"]] == [0.0, 0.0]
    assert result["results"][0]["note"] == "缺少必需字段: width_mm"
    assert result["results"][1]["note"] == "未找到material对应的价格: UNKNOWN"

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "material"
    assert field_name == "material_cost"
    assert [update["value"] for update in updates] == [0.0, 0.0]
    assert updates[0]["steps"][0]["status"] == "failed"
    assert updates[1]["steps"][0]["status"] == "failed"
