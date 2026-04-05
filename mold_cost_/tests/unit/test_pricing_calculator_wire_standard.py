from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()

MODULE_PATH = "mold_cost.domain.pricing.calculators.price_wire_standard"


def _load_module():
    return importlib.import_module(MODULE_PATH)


def _patch_batch_upsert(monkeypatch, module):
    captured: list[tuple[list[dict], str, str]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)
    return captured


def test_wire_standard_calculator_covers_slow_middle_fast_and_missing_metadata(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-wire-standard-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-slow",
                            "part_name": "Slow Part",
                            "wire_process_note": "慢丝割一修一",
                            "wire_process": "slow_and_one",
                            "boring_num": 2,
                            "quantity": 3,
                            "metadata": {"wire_cut_details": [{"view": "top_view", "total_length": 1}]},
                        },
                        {
                            "subgraph_id": "sg-middle",
                            "part_name": "Middle Part",
                            "wire_process_note": "中丝加工",
                            "wire_process": "medium",
                            "boring_num": 1,
                            "quantity": 4,
                            "metadata": {"wire_cut_details": [{"view": "front_view", "total_length": 2}]},
                        },
                        {
                            "subgraph_id": "sg-fast",
                            "part_name": "Fast Part",
                            "wire_process_note": "快丝加工",
                            "wire_process": "fast",
                            "boring_num": 4,
                            "quantity": 2,
                            "metadata": {"wire_cut_details": [{"view": "side_view", "total_length": 3}]},
                        },
                        {
                            "subgraph_id": "sg-missing",
                            "part_name": "Missing Meta",
                            "wire_process_note": "快丝加工",
                            "wire_process": "fast",
                            "boring_num": 1,
                            "quantity": 1,
                            "metadata": None,
                        },
                    ],
                },
                "wire_standard": {
                    "base_prices": [
                        {"sub_category": "slow_and_one", "price": 5.0, "unit": "hole"},
                        {"sub_category": "medium", "price": 7.0, "unit": "hole"},
                        {"sub_category": "fast", "price": 9.0, "unit": "hole"},
                        {"sub_category": "中丝基本费", "price": 3.0, "unit": "piece"},
                        {"sub_category": "快丝基本费", "price": 5.0, "unit": "piece"},
                    ]
                },
            },
            job_id="job-wire-standard-1",
        )
    )

    assert result["job_id"] == "job-wire-standard-1"
    assert len(result["results"]) == 4

    slow, middle, fast, missing = result["results"]
    assert slow["wire_type"] == "slow"
    assert slow["standard_base_cost"] == pytest.approx(10.0)
    assert middle["wire_type"] == "middle"
    assert middle["standard_base_cost"] == pytest.approx(19.0)
    assert fast["wire_type"] == "fast"
    assert fast["standard_base_cost"] == pytest.approx(46.0)
    assert missing["standard_base_cost"] == pytest.approx(0.0)
    assert "metadata" in missing["note"]

    assert module.MCP_TOOL_META["handler"] == "calculate"
    assert module.MCP_TOOL_META["needs"] == ["base_itemcode", "wire_standard"]

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "wire_standard"
    assert field_name == "standard_base_cost"
    assert len(updates) == 4
    assert {item["subgraph_id"] for item in updates} == {"sg-slow", "sg-middle", "sg-fast", "sg-missing"}


def test_wire_standard_calculator_sync_wrapper_and_subgraph_filter(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = module.calculate_sync(
        {
            "base_itemcode": {
                "job_id": "job-wire-standard-2",
                "parts": [
                    {
                        "subgraph_id": "keep",
                        "part_name": "Keep Part",
                        "wire_process_note": "快丝加工",
                        "wire_process": "fast",
                        "boring_num": 2,
                        "quantity": 1,
                        "metadata": {"wire_cut_details": []},
                    },
                    {
                        "subgraph_id": "skip",
                        "part_name": "Skip Part",
                        "wire_process_note": "中丝加工",
                        "wire_process": "medium",
                        "boring_num": 1,
                        "quantity": 1,
                        "metadata": {"wire_cut_details": []},
                    },
                ],
            },
            "wire_standard": {
                "base_prices": [
                    {"sub_category": "fast", "price": 9.0, "unit": "hole"},
                    {"sub_category": "快丝基本费", "price": 5.0, "unit": "piece"},
                    {"sub_category": "medium", "price": 7.0, "unit": "hole"},
                    {"sub_category": "中丝基本费", "price": 3.0, "unit": "piece"},
                ]
            },
        },
        subgraph_ids=["keep"],
    )

    assert result["job_id"] == "job-wire-standard-2"
    assert len(result["results"]) == 1
    assert result["results"][0]["subgraph_id"] == "keep"
    assert result["results"][0]["standard_base_cost"] == pytest.approx(23.0)

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "wire_standard"
    assert field_name == "standard_base_cost"
    assert len(updates) == 1
    assert updates[0]["subgraph_id"] == "keep"
    assert updates[0]["value"] == pytest.approx(23.0)


def test_wire_standard_module_no_longer_imports_legacy_script():
    from mold_cost.domain.pricing.calculators import price_wire_standard as module

    source = Path(module.__file__).read_text(encoding="utf-8-sig")
    assert "scripts.calculate.price_wire_standard" not in source
