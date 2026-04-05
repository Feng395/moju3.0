from __future__ import annotations

import asyncio
import importlib
import json
from pathlib import Path

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()

MODULE_PATH = "mold_cost.domain.pricing.calculators.price_nc_time"


def _load_module():
    return importlib.import_module(MODULE_PATH)


def _patch_batch_upsert(monkeypatch, module):
    captured: list[tuple[list[dict], str, str]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)
    return captured


def test_nc_time_calculator_happy_path(monkeypatch):
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
                    "job_id": "job-nc-time-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-1",
                            "part_name": "Plate A",
                            "length_mm": 2200,
                            "width_mm": 1300,
                            "thickness_mm": 1200,
                            "quantity": 2,
                            "nc_time_cost": json.dumps(
                                {
                                    "nc_details": [
                                        {"code": "开粗", "value": 30},
                                        {"code": "精铣", "value": 60},
                                        {"code": "ABC", "value": 90},
                                    ]
                                }
                            ),
                        },
                        {
                            "subgraph_id": "sg-2",
                            "part_name": "Plate B",
                            "length_mm": 100,
                            "width_mm": 80,
                            "thickness_mm": 40,
                            "quantity": 1,
                            "nc_time_cost": None,
                        },
                    ],
                },
                "nc": {
                    "nc_prices": [
                        {"sub_category": "work_hour", "price": 60.0, "unit": "元/小时", "min_num": "S:[0,1500), L:[0,2000)"},
                        {"sub_category": "work_hour", "price": 100.0, "unit": "元/小时", "min_num": "S:[1200,9999), L:[2000,9999)"},
                    ]
                },
            }
        )
    )

    assert result["job_id"] == "job-nc-time-1"
    assert len(result["results"]) == 2

    part = result["results"][0]
    assert part["subgraph_id"] == "sg-1"
    assert part["quantity"] == 2
    assert part["nc_roughing_cost"] == pytest.approx(100.0)
    assert part["nc_milling_cost"] == pytest.approx(200.0)
    assert part["nc_drilling_cost"] == pytest.approx(300.0)
    assert part["total_cost"] == pytest.approx(600.0)

    skipped = result["results"][1]
    assert skipped["subgraph_id"] == "sg-2"
    assert skipped["nc_roughing_cost"] == pytest.approx(0.0)
    assert skipped["nc_milling_cost"] == pytest.approx(0.0)
    assert skipped["nc_drilling_cost"] == pytest.approx(0.0)

    assert module.MCP_TOOL_META["handler"] == "calculate"
    assert module.MCP_TOOL_META["needs"] == ["base_itemcode", "nc"]

    assert len(captured) == 3
    assert [item[1] for item in captured] == ["nc_roughing", "nc_milling", "nc_drilling"]
    assert all(len(item[0]) == 2 for item in captured)
    assert captured[0][0][0]["value"] == pytest.approx(100.0)
    assert captured[1][0][0]["value"] == pytest.approx(200.0)
    assert captured[2][0][0]["value"] == pytest.approx(300.0)

    assert len(updated_subgraphs) == 1
    assert updated_subgraphs[0][0] == "job-nc-time-1"
    assert len(updated_subgraphs[0][1]) == 2


def test_nc_time_calculator_sync_wrapper_and_filter(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)
    updated_subgraphs: list[tuple[str, list[dict]]] = []

    async def fake_batch_update_subgraphs(job_id, updates):
        updated_subgraphs.append((job_id, list(updates)))

    monkeypatch.setattr(module, "_batch_update_subgraphs", fake_batch_update_subgraphs)

    result = module.calculate_sync(
        {
            "base_itemcode": {
                "job_id": "job-nc-time-2",
                "parts": [
                    {
                        "subgraph_id": "keep",
                        "part_name": "Keep",
                        "length_mm": 900,
                        "width_mm": 700,
                        "thickness_mm": 30,
                        "quantity": 1,
                        "nc_time_cost": {"nc_details": [{"code": "M1", "value": 120}]},
                    },
                    {
                        "subgraph_id": "skip",
                        "part_name": "Skip",
                        "length_mm": 2200,
                        "width_mm": 1300,
                        "thickness_mm": 50,
                        "quantity": 1,
                        "nc_time_cost": {"nc_details": [{"code": "开粗", "value": 60}]},
                    },
                ],
            },
            "nc": {
                "nc_prices": [
                    {"sub_category": "work_hour", "price": 60.0, "min_num": "S:[0,9999), L:[0,9999)"},
                ]
            },
        },
        subgraph_ids=["keep"],
    )

    assert result["job_id"] == "job-nc-time-2"
    assert len(result["results"]) == 1
    part = result["results"][0]
    assert part["subgraph_id"] == "keep"
    assert part["nc_drilling_cost"] == pytest.approx(120.0)
    assert len(captured) == 3
    assert all(len(item[0]) == 1 for item in captured)
    assert updated_subgraphs[0][0] == "job-nc-time-2"
    assert len(updated_subgraphs[0][1]) == 1


def test_nc_time_module_no_longer_imports_legacy_script():
    from mold_cost.domain.pricing.calculators import price_nc_time as module

    source = Path(module.__file__).read_text(encoding="utf-8-sig")
    assert "scripts.calculate.price_nc_time" not in source
