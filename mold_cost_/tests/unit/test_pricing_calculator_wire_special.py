from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()

MODULE_PATH = "mold_cost.domain.pricing.calculators.price_wire_special"


def _load_module():
    return importlib.import_module(MODULE_PATH)


def _patch_batch_upsert(monkeypatch, module):
    captured: list[tuple[list[dict], str, str]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)
    return captured


def test_wire_special_calculator_happy_path(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-wire-special-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-1",
                            "part_name": "Template Part",
                            "wire_process_note": "慢丝工艺",
                            "length_mm": 500,
                            "width_mm": 120,
                            "thickness_mm": 80,
                            "metadata": {
                                "wire_cut_details": [
                                    {"view": "front_view", "total_length": 8},
                                    {"view": "top_view", "total_length": 10},
                                ]
                            },
                        },
                        {
                            "subgraph_id": "sg-2",
                            "part_name": "Component Part",
                            "wire_process_note": "中丝工艺",
                            "length_mm": 180,
                            "width_mm": 100,
                            "thickness_mm": 60,
                            "metadata": {
                                "wire_cut_details": [
                                    {"view": "top_view", "total_length": 12},
                                ]
                            },
                        },
                    ],
                },
                "wire_special": {
                    "special_prices": [
                        {"sub_category": "template_component", "price": 250},
                        {"sub_category": "slow_template", "price": 80},
                        {"sub_category": "slow_component", "price": 40},
                        {"sub_category": "slow_side", "price": 20},
                        {"sub_category": "medium_template", "price": 60},
                        {"sub_category": "medium_component", "price": 30},
                        {"sub_category": "medium_side", "price": 10},
                        {"sub_category": "fast_template", "price": 50},
                        {"sub_category": "fast_component", "price": 25},
                        {"sub_category": "fast_side", "price": 5},
                    ],
                    "rule_prices": [],
                },
            },
            job_id="job-wire-special-1",
            subgraph_ids=["sg-1", "sg-2"],
        )
    )

    assert result["job_id"] == "job-wire-special-1"
    assert len(result["results"]) == 2

    first, second = result["results"]
    assert first["subgraph_id"] == "sg-1"
    assert first["wire_type"] == "slow"
    assert first["is_template"] is True
    assert first["has_side_cut"] is True
    assert first["special_base_cost"] == pytest.approx(100.0)

    assert second["subgraph_id"] == "sg-2"
    assert second["wire_type"] == "medium"
    assert second["is_template"] is False
    assert second["has_side_cut"] is False
    assert second["special_base_cost"] == pytest.approx(30.0)

    assert module.MCP_TOOL_META["handler"] == "calculate"
    assert module.MCP_TOOL_META["needs"] == ["base_itemcode", "wire_special"]

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "wire_special"
    assert field_name == "special_base_cost"
    assert len(updates) == 2
    assert updates[0]["job_id"] == "job-wire-special-1"
    assert updates[0]["subgraph_id"] == "sg-1"
    assert updates[0]["value"] == pytest.approx(100.0)
    assert len(updates[0]["steps"]) == 6
    assert updates[1]["subgraph_id"] == "sg-2"
    assert updates[1]["value"] == pytest.approx(30.0)


def test_wire_special_calculator_sync_wrapper_and_missing_metadata(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = module.calculate_sync(
        {
            "base_itemcode": {
                "job_id": "job-wire-special-2",
                "parts": [
                    {
                        "subgraph_id": "sg-3",
                        "part_name": "Empty Part",
                        "wire_process_note": "快丝工艺",
                        "length_mm": 100,
                        "width_mm": 50,
                        "thickness_mm": 10,
                        "metadata": None,
                    }
                ],
            },
            "wire_special": {
                "special_prices": [],
                "rule_prices": [],
            },
        }
    )

    assert result["job_id"] == "job-wire-special-2"
    assert len(result["results"]) == 1
    part = result["results"][0]
    assert part["wire_type"] == "fast"
    assert part["special_base_cost"] == pytest.approx(0.0)
    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "wire_special"
    assert field_name == "special_base_cost"
    assert len(updates) == 1
    assert updates[0]["value"] == pytest.approx(0.0)
    assert len(updates[0]["steps"]) == 1


def test_wire_special_module_no_longer_imports_legacy_script():
    from mold_cost.domain.pricing.calculators import price_wire_special as module

    source = Path(module.__file__).read_text(encoding="utf-8-sig")
    assert "scripts.calculate.price_wire_special" not in source
