from __future__ import annotations

import asyncio
import importlib

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()


MODULE_PATH = "mold_cost.domain.pricing.calculators.price_weight"


def _load_module():
    return importlib.import_module(MODULE_PATH)


def test_weight_calculator_happy_path_alias_and_default_density(monkeypatch):
    module = _load_module()
    db_calls: list[tuple[str, tuple[object, ...]]] = []

    async def fake_execute(sql: str, *params):
        db_calls.append((sql, params))
        return None

    monkeypatch.setattr(module.db, "execute", fake_execute)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-weight-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-1",
                            "part_name": "Plate A",
                            "material": "toolox33",
                            "length_mm": 100,
                            "width_mm": 50,
                            "thickness_mm": 10,
                        },
                        {
                            "subgraph_id": "sg-2",
                            "part_name": "Plate B",
                            "material": "45#",
                            "length_mm": 80,
                            "width_mm": 20,
                            "thickness_mm": 5,
                        },
                    ],
                },
                "density": {
                    "density_data": [
                        {
                            "sub_category": "T00L0X33",
                            "price": 0.00000785,
                            "unit": "g/cm3",
                        }
                    ]
                },
            },
            job_id="job-weight-1",
            subgraph_ids=["sg-1", "sg-2"],
        )
    )

    assert result["job_id"] == "job-weight-1"
    assert len(result["results"]) == 2

    first, second = result["results"]
    assert first["subgraph_id"] == "sg-1"
    assert first["part_name"] == "Plate A"
    assert first["weight"] == pytest.approx(0.393)
    assert second["subgraph_id"] == "sg-2"
    assert second["part_name"] == "Plate B"
    assert second["weight"] == pytest.approx(0.063)

    assert module.MCP_TOOL_META["handler"] == "calculate"
    assert module.MCP_TOOL_META["needs"] == ["base_itemcode", "density"]

    assert len(db_calls) == 6
    insert_sqls = [sql for sql, _params in db_calls if "processing_cost_calculation_details" in sql]
    subgraph_sqls = [sql for sql, _params in db_calls if "UPDATE subgraphs" in sql]
    feature_sqls = [sql for sql, _params in db_calls if "UPDATE features" in sql]
    assert len(insert_sqls) == 2
    assert len(subgraph_sqls) == 2
    assert len(feature_sqls) == 2


def test_weight_calculator_records_validation_failure(monkeypatch):
    module = _load_module()
    db_calls: list[tuple[str, tuple[object, ...]]] = []

    async def fake_execute(sql: str, *params):
        db_calls.append((sql, params))
        return None

    monkeypatch.setattr(module.db, "execute", fake_execute)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-weight-2",
                    "parts": [
                        {
                            "subgraph_id": "sg-3",
                            "part_name": "Plate C",
                            "material": "Q235",
                            "length_mm": 100,
                            "width_mm": None,
                            "thickness_mm": 10,
                        }
                    ],
                },
                "density": {"density_data": []},
            },
            job_id="job-weight-2",
        )
    )

    assert result["results"][0]["weight"] == pytest.approx(0.0)
    assert result["results"][0]["note"] == "缺少必需字段: width_mm"

    assert len(db_calls) == 3
    assert any("processing_cost_calculation_details" in sql for sql, _params in db_calls)
    assert any("UPDATE subgraphs" in sql for sql, _params in db_calls)
    assert any("UPDATE features" in sql for sql, _params in db_calls)
