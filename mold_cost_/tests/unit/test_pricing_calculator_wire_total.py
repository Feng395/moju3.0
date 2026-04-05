from __future__ import annotations

import asyncio

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_wire_total_calculator_runs_real_domain_logic(monkeypatch):
    from mold_cost.domain.pricing.calculators import price_wire_total as module

    db_calls: list[tuple[str, tuple[object, ...]]] = []

    async def fake_execute(sql: str, *params):
        db_calls.append((sql, params))
        return None

    monkeypatch.setattr(module.db, "execute", fake_execute)

    result = asyncio.run(
        module.calculate(
            search_data={
                "base_itemcode": {
                    "job_id": "job-wire-total",
                    "parts": [
                        {
                            "subgraph_id": "sg-1",
                            "part_name": "Wire Part",
                            "quantity": 2,
                            "metadata": {
                                "wire_cut_details": [
                                    {"view": "top_view", "total_length": 10},
                                    {"view": "side_view", "total_length": 5},
                                    {"view": "front_view", "total_length": 3},
                                ]
                            },
                        }
                    ],
                },
                "total": {
                    "job_id": "job-wire-total",
                    "cost_details": [
                        {
                            "subgraph_id": "sg-1",
                            "weight": 1.25,
                            "basic_processing_cost": 10.0,
                            "special_base_cost": 12.0,
                            "standard_base_cost": 11.0,
                            "material_additional_cost": 2.0,
                            "material_cost": 8.0,
                            "heat_treatment_cost": 1.0,
                            "tooth_hole_cost": 7.0,
                            "tooth_hole_time_cost": 0.5,
                            "calculation_steps": [
                                {
                                    "category": "wire_special",
                                    "steps": [
                                        {
                                            "step": "判断线割类型",
                                            "wire_type": "slow",
                                        }
                                    ],
                                },
                                {
                                    "category": "material",
                                    "steps": [
                                        {
                                            "step": "匹配材料价格",
                                            "unit_price": 9.75,
                                        }
                                    ],
                                },
                                {
                                    "category": "heat",
                                    "steps": [
                                        {
                                            "step": "匹配材料价格",
                                            "unit_price": 1.25,
                                        }
                                    ],
                                },
                            ],
                        }
                    ],
                },
            },
            job_id="job-wire-total",
            subgraph_ids=["sg-1"],
        )
    )

    assert result["job_id"] == "job-wire-total"
    assert len(result["results"]) == 1

    part = result["results"][0]
    assert part["subgraph_id"] == "sg-1"
    assert part["quantity"] == 2
    assert part["weight_kg"] == pytest.approx(2.5)
    assert part["material_cost"] == pytest.approx(16.0)
    assert part["heat_treatment_cost"] == pytest.approx(2.0)
    assert part["slow_wire_cost"] == pytest.approx(28.0)
    assert part["mid_wire_cost"] == pytest.approx(0.0)
    assert part["fast_wire_cost"] == pytest.approx(0.0)
    assert part["material_unit_price"] == pytest.approx(9.75)
    assert part["heat_treatment_unit_price"] == pytest.approx(1.25)
    assert part["slow_wire_length"] == pytest.approx(18.0)
    assert part["mid_wire_length"] == pytest.approx(0.0)
    assert part["fast_wire_length"] == pytest.approx(0.0)
    assert part["wire_type"] == "慢丝"
    assert part["wire_cost_source"] == "special_base_cost"
    assert part["edm_cost"] == pytest.approx(7.0)
    assert part["edm_time"] == pytest.approx(0.5)

    assert len(db_calls) == 2
    assert any("UPDATE subgraphs" in sql for sql, _params in db_calls)
    assert any("processing_cost_calculation_details" in sql for sql, _params in db_calls)


def test_wire_total_module_no_longer_imports_legacy_script():
    from pathlib import Path
    from mold_cost.domain.pricing.calculators import price_wire_total as module

    source = Path(module.__file__).read_text(encoding="utf-8-sig")
    assert "scripts.calculate.price_wire_total" not in source
