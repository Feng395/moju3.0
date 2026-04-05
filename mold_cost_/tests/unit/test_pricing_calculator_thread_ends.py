from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()

MODULE_PATH = "mold_cost.domain.pricing.calculators.price_water_mill_thread_ends"


def _load_module():
    return importlib.import_module(MODULE_PATH)


def _patch_batch_upsert(monkeypatch, module):
    captured: list[tuple[list[dict], str, str]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)
    return captured


def test_thread_ends_calculator_small_and_large_paths(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-thread-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-small",
                            "part_name": "Small Part",
                            "has_auto_material": True,
                            "has_material_preparation": False,
                            "water_mill": {"water_mill_details": [{"thread_ends": 4}]},
                        },
                        {
                            "subgraph_id": "sg-large",
                            "part_name": "Large Part",
                            "length_mm": 600,
                            "width_mm": 200,
                            "thickness_mm": 100,
                            "has_auto_material": False,
                            "has_material_preparation": None,
                            "water_mill": {"water_mill_details": [{"thread_ends": 2}]},
                        },
                    ],
                },
                "water_mill": {
                    "s_water_mill_prices": [
                        {"sub_category": "thread_ends", "price": 6.0, "unit": "piece"}
                    ],
                    "l_water_mill_prices": [],
                },
            }
        )
    )

    assert result["job_id"] == "job-thread-1"
    assert len(result["results"]) == 2

    small = result["results"][0]
    assert small["subgraph_id"] == "sg-small"
    assert small["mill_type"] == "s_water_mill"
    assert small["part_type"] is None
    assert small["thread_ends_count"] == 4
    assert small["thread_ends_cost"] == pytest.approx(24.0)

    large = result["results"][1]
    assert large["subgraph_id"] == "sg-large"
    assert large["mill_type"] == "l_water_mill"
    assert large["part_type"] == "long_strip"
    assert large["thread_ends_count"] == 2
    assert large["thread_ends_cost"] == pytest.approx(0.0)

    assert module.MCP_TOOL_META["handler"] == "calculate"
    assert module.MCP_TOOL_META["needs"] == ["base_itemcode", "water_mill"]

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "water_mill_thread_ends"
    assert field_name == "thread_ends_cost"
    assert len(updates) == 2
    assert updates[0]["job_id"] == "job-thread-1"
    assert updates[0]["subgraph_id"] == "sg-small"
    assert updates[0]["value"] == pytest.approx(24.0)
    assert len(updates[0]["steps"]) == 4
    assert updates[1]["subgraph_id"] == "sg-large"
    assert updates[1]["value"] == pytest.approx(0.0)
    assert len(updates[1]["steps"]) == 5


def test_thread_ends_calculator_sync_wrapper_and_missing_data(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = module.calculate_sync(
        {
            "base_itemcode": {
                "job_id": "job-thread-2",
                "parts": [
                    {
                        "subgraph_id": "sg-missing",
                        "part_name": "Missing Part",
                        "has_auto_material": True,
                        "has_material_preparation": True,
                        "water_mill": {},
                    }
                ],
            },
            "water_mill": {"s_water_mill_prices": []},
        },
        subgraph_ids=["sg-missing"],
    )

    assert result["job_id"] == "job-thread-2"
    assert len(result["results"]) == 1
    assert result["results"][0]["thread_ends_cost"] == pytest.approx(0.0)
    assert "no water_mill_details" in result["results"][0]["note"]
    assert captured == []


def test_thread_ends_module_no_longer_imports_legacy_script():
    from mold_cost.domain.pricing.calculators import price_water_mill_thread_ends as module

    source = Path(module.__file__).read_text(encoding="utf-8-sig")
    assert "scripts.calculate.price_water_mill_thread_ends" not in source
