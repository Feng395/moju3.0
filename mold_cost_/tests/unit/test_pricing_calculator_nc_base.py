from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()

MODULE_PATH = "mold_cost.domain.pricing.calculators.price_nc_base"


def _load_module():
    return importlib.import_module(MODULE_PATH)


def _patch_batch_upsert(monkeypatch, module):
    captured: list[tuple[list[dict], str, str]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)
    return captured


def test_nc_base_calculator_happy_path(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-nc-base-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-1",
                            "part_name": "Plate A",
                            "length_mm": 300,
                            "width_mm": 200,
                            "thickness_mm": 100,
                            "quantity": 1,
                            "nc_time_cost": {
                                "nc_details": [
                                    {"code": "开粗", "value": 1},
                                    {"code": "精铣", "value": 1},
                                    {"code": "钻床", "value": 1},
                                ]
                            },
                        }
                    ],
                },
                "nc": {
                    "nc_prices": [
                        {"sub_category": "nc_base", "price": 1.0},
                        {"sub_category": "nc_base", "price": 0.5},
                        {"sub_category": "work_hour", "price": 100, "unit": "元/小时"},
                        {"sub_category": "work_hour", "price": 60, "unit": "元/小时"},
                        {"sub_category": "work_hour", "price": 80, "unit": "元/小时"},
                    ]
                },
                "wire_base": {
                    "rule_prices": [{"sub_category": "template_component", "price": 400}]
                },
            },
            job_id="job-nc-base-1",
            subgraph_ids=["sg-1"],
        )
    )

    assert result["job_id"] == "job-nc-base-1"
    assert len(result["results"]) == 1

    part = result["results"][0]
    assert part["subgraph_id"] == "sg-1"
    assert part["part_type"] == "component"
    assert part["quantity"] == 1
    assert part["nc_base_roughing_cost"] == pytest.approx(30.0)
    assert part["nc_base_milling_cost"] == pytest.approx(30.0)
    assert part["nc_base_drilling_cost"] == pytest.approx(30.0)

    assert module.MCP_TOOL_META["handler"] == "calculate"
    assert module.MCP_TOOL_META["needs"] == ["base_itemcode", "nc", "wire_base"]

    assert len(captured) == 3
    categories = [item[1] for item in captured]
    assert categories == ["nc_base_roughing", "nc_base_milling", "nc_base_drilling"]
    assert all(item[0][0]["job_id"] == "job-nc-base-1" for item in captured)
    assert all(item[0][0]["subgraph_id"] == "sg-1" for item in captured)
    assert all(item[0][0]["value"] == pytest.approx(30.0) for item in captured)


def test_nc_base_calculator_skips_when_nc_time_missing(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-nc-base-2",
                    "parts": [
                        {
                            "subgraph_id": "sg-2",
                            "part_name": "Plate B",
                            "length_mm": 100,
                            "width_mm": 80,
                            "thickness_mm": 50,
                            "quantity": 1,
                            "nc_time_cost": None,
                        }
                    ],
                },
                "nc": {
                    "nc_prices": [
                        {"sub_category": "nc_base", "price": 1.0},
                        {"sub_category": "nc_base", "price": 0.5},
                        {"sub_category": "work_hour", "price": 100, "unit": "元/小时"},
                        {"sub_category": "work_hour", "price": 60, "unit": "元/小时"},
                        {"sub_category": "work_hour", "price": 80, "unit": "元/小时"},
                    ]
                },
                "wire_base": {
                    "rule_prices": [{"sub_category": "template_component", "price": 400}]
                },
            },
            job_id="job-nc-base-2",
        )
    )

    part = result["results"][0]
    assert part["nc_base_roughing_cost"] == pytest.approx(0.0)
    assert part["nc_base_milling_cost"] == pytest.approx(0.0)
    assert part["nc_base_drilling_cost"] == pytest.approx(0.0)
    assert "nc_time_cost" in part["note"]

    assert len(captured) == 3
    assert all(update[0][0]["value"] == pytest.approx(0.0) for update in captured)


def test_nc_base_module_no_longer_imports_legacy_script():
    from mold_cost.domain.pricing.calculators import price_nc_base as module

    source = Path(module.__file__).read_text(encoding="utf-8-sig")
    assert "scripts.calculate.price_nc_base" not in source
