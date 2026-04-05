from __future__ import annotations

import asyncio

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_price_total_calculator_aggregates_processing_and_job_total(monkeypatch):
    from mold_cost.domain.pricing.calculators import price_total as module

    captured_subgraphs: list[tuple[str, list[dict]]] = []
    captured_process_descriptions: list[tuple[str, list[str]]] = []
    captured_job_totals: list[tuple[str, float]] = []

    async def fake_batch_update_subgraphs(job_id, updates):
        captured_subgraphs.append((job_id, list(updates)))

    async def fake_update_process_descriptions(job_id, subgraph_ids):
        captured_process_descriptions.append((job_id, list(subgraph_ids)))

    async def fake_update_job_total_cost(job_id, total_cost):
        captured_job_totals.append((job_id, total_cost))

    monkeypatch.setattr(module, "_batch_update_subgraphs", fake_batch_update_subgraphs)
    monkeypatch.setattr(module, "_update_process_descriptions", fake_update_process_descriptions)
    monkeypatch.setattr(module, "_update_job_total_cost", fake_update_job_total_cost)

    result = asyncio.run(
        module.calculate(
            {
                "subgraphs_cost": {
                    "job_id": "job-total-1",
                    "cost_summary": [
                        {
                            "subgraph_id": "sg-1",
                            "material_cost": 100.0,
                            "heat_treatment_cost": 20.0,
                            "slow_wire_cost": 8.0,
                            "edm_cost": 2.5,
                            "drilling_cost": 1.5,
                        }
                    ],
                }
            }
        )
    )

    assert result["job_id"] == "job-total-1"
    assert result["job_total_cost"] == pytest.approx(132.0)
    assert result["parts_count"] == 1
    assert result["results"][0]["processing_cost_total"] == pytest.approx(12.0)
    assert result["results"][0]["total_cost"] == pytest.approx(132.0)
    assert result["results"][0]["breakdown"]["slow_wire_cost"] == pytest.approx(8.0)

    assert len(captured_subgraphs) == 1
    updated_job_id, updates = captured_subgraphs[0]
    assert updated_job_id == "job-total-1"
    assert len(updates) == 1
    assert updates[0]["subgraph_id"] == "sg-1"
    assert updates[0]["total_cost"] == pytest.approx(132.0)
    assert updates[0]["processing_cost_total"] == pytest.approx(12.0)
    assert len(updates[0]["calculation_steps"]) == 3

    assert captured_process_descriptions == [("job-total-1", ["sg-1"])]
    assert len(captured_job_totals) == 1
    assert captured_job_totals[0][0] == "job-total-1"
    assert captured_job_totals[0][1] == pytest.approx(132.0)


def test_price_total_process_description_generation(monkeypatch):
    from mold_cost.domain.pricing.calculators import price_total as module

    execute_calls: list[tuple[str, tuple[object, ...]]] = []

    async def fake_fetch_all(sql, job_id, subgraph_ids):
        assert "SELECT subgraph_id" in sql
        assert job_id == "job-total-2"
        assert subgraph_ids == ["sg-2"]
        return [
            {
                "subgraph_id": "sg-2",
                "nc_roughing_time": 1.0,
                "nc_milling_time": 0.0,
                "drilling_time": None,
                "milling_machine_time": 2.0,
                "large_grinding_time": 0.0,
                "small_grinding_time": 1.0,
                "slow_wire_length": 12.0,
                "mid_wire_length": 0.0,
                "fast_wire_length": 0.0,
                "edm_time": 0.0,
                "engraving_cost": None,
            }
        ]

    async def fake_execute(sql, *params):
        execute_calls.append((sql, params))
        return None

    monkeypatch.setattr(module.db, "fetch_all", fake_fetch_all)
    monkeypatch.setattr(module.db, "execute", fake_execute)

    asyncio.run(module._update_process_descriptions("job-total-2", ["sg-2"]))

    assert len(execute_calls) == 1
    sql, params = execute_calls[0]
    assert "process_description" in sql
    assert params == ("job-total-2", "sg-2", "S-X-YM-WE-QC")


def test_price_total_handles_invalid_numeric_values():
    from mold_cost.domain.pricing.calculators import price_total as module

    result, db_data = module._calculate_part_total(
        {
            "subgraph_id": "sg-invalid",
            "material_cost": object(),
        }
    )

    assert result["subgraph_id"] == "sg-invalid"
    assert result["total_cost"] == pytest.approx(0.0)
    assert result["processing_cost_total"] == pytest.approx(0.0)
    assert "Failed to convert cost values" in result["note"]
    assert db_data["total_cost"] == pytest.approx(0.0)
    assert db_data["processing_cost_total"] == pytest.approx(0.0)
    assert db_data["calculation_steps"][0]["status"] == "failed"
