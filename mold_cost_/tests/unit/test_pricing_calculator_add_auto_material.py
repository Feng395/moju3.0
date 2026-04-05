from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()

MODULE_PATH = "mold_cost.domain.pricing.calculators.price_add_auto_material"


def _load_module():
    return importlib.import_module(MODULE_PATH)


def _patch_batch_upsert(monkeypatch, module):
    captured: list[tuple[list[dict], str, str]] = []

    async def fake_batch_upsert_with_steps(updates, category, field_name):
        captured.append((list(updates), category, field_name))

    monkeypatch.setattr(module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)
    return captured


def test_add_auto_material_calculator_happy_path_and_skip_non_auto_material(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-add-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-1",
                            "part_name": "Plate A",
                            "has_auto_material": True,
                            "material": "TooLox33",
                            "length_mm": 100,
                            "width_mm": 50,
                            "thickness_mm": 10,
                        },
                        {
                            "subgraph_id": "sg-2",
                            "part_name": "Plate B",
                            "has_auto_material": False,
                            "material": "Q235",
                            "length_mm": 100,
                            "width_mm": 50,
                            "thickness_mm": 10,
                        },
                    ],
                },
                "material": {
                    "material_prices": [
                        {"sub_category": "T00L0X33", "price": 20.0, "unit": "kg"},
                    ]
                },
                "density": {
                    "density_data": [
                        {"sub_category": "T00L0X33", "price": 0.00001, "unit": "g/cm3"},
                    ]
                },
            },
            job_id="job-add-1",
            subgraph_ids=["sg-1", "sg-2"],
        )
    )

    assert result["job_id"] == "job-add-1"
    assert len(result["results"]) == 2

    first, second = result["results"]
    assert first["subgraph_id"] == "sg-1"
    assert first["part_name"] == "Plate A"
    assert first["has_auto_material"] is True
    assert first["weight"] == pytest.approx(0.5)
    assert first["material_additional_cost"] == pytest.approx(10.0)

    assert second["subgraph_id"] == "sg-2"
    assert second["part_name"] == "Plate B"
    assert second["has_auto_material"] is False
    assert second["material_additional_cost"] == pytest.approx(0.0)
    assert "不是自找料" in second["note"]

    assert module.MCP_TOOL_META["handler"] == "calculate"
    assert module.MCP_TOOL_META["needs"] == ["base_itemcode", "material", "density"]

    assert len(captured) == 1
    updates, category, field_name = captured[0]
    assert category == "add_auto_material"
    assert field_name == "material_additional_cost"
    assert len(updates) == 2
    assert updates[0]["job_id"] == "job-add-1"
    assert updates[0]["subgraph_id"] == "sg-1"
    assert updates[0]["value"] == pytest.approx(10.0)
    assert len(updates[0]["steps"]) == 6
    assert updates[1]["value"] == pytest.approx(0.0)


def test_add_auto_material_calculator_sync_wrapper_and_failure_path(monkeypatch):
    module = _load_module()
    captured = _patch_batch_upsert(monkeypatch, module)

    result = module.calculate_sync(
        {
            "base_itemcode": {
                "job_id": "job-add-2",
                "parts": [
                    {
                        "subgraph_id": "sg-3",
                        "part_name": "Plate C",
                        "has_auto_material": True,
                        "material": "",
                        "length_mm": 100,
                        "width_mm": 50,
                        "thickness_mm": 10,
                    }
                ],
            },
            "material": {"material_prices": []},
            "density": {"density_data": []},
        }
    )

    assert result["job_id"] == "job-add-2"
    assert len(result["results"]) == 1
    part = result["results"][0]
    assert part["material_additional_cost"] == pytest.approx(0.0)
    assert "material为空" in part["note"]
    assert len(captured) == 1
    assert captured[0][1] == "add_auto_material"
    assert captured[0][2] == "material_additional_cost"
    assert captured[0][0][0]["value"] == pytest.approx(0.0)


def test_add_auto_material_module_no_longer_imports_legacy_script():
    from mold_cost.domain.pricing.calculators import price_add_auto_material as module

    source = Path(module.__file__).read_text(encoding="utf-8-sig")
    assert "scripts.calculate.price_add_auto_material" not in source
