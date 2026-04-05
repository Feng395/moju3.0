from __future__ import annotations

import asyncio
from pathlib import Path

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_judgment_cleanup_material_preparation_and_empty_metadata(monkeypatch):
    from mold_cost.domain.pricing.calculators import judgment as module

    execute_calls: list[tuple[str, tuple[object, ...]]] = []

    async def fake_execute(sql, *params):
        execute_calls.append((sql, params))
        return None

    monkeypatch.setattr(module.db, "execute", fake_execute)

    result = asyncio.run(
        module.calculate(
            {
                "base_itemcode": {
                    "job_id": "job-judgment-1",
                    "parts": [
                        {
                            "subgraph_id": "sg-1",
                            "part_name": "Part A",
                            "has_material_preparation": "shared-stock",
                            "metadata": None,
                        }
                    ],
                }
            }
        )
    )

    assert result["job_id"] == "job-judgment-1"
    assert len(result["results"]) == 1
    part = result["results"][0]
    assert part["subgraph_id"] == "sg-1"
    assert len(part["cleanup_actions"]) == 2
    assert part["cleanup_actions"][0]["type"] == "material_preparation"
    assert part["cleanup_actions"][1]["type"] == "wire_data"

    assert len(execute_calls) == 4
    assert execute_calls[0][1] == ("job-judgment-1", "sg-1")
    assert execute_calls[1][1] == ("job-judgment-1", "sg-1", "该物料备料于: shared-stock")
    assert execute_calls[2][1] == ("job-judgment-1", "sg-1")
    assert execute_calls[3][1] == ("job-judgment-1", "sg-1")


def test_judgment_cleanup_keeps_valid_wire_metadata_and_filters_subgraphs(monkeypatch):
    from mold_cost.domain.pricing.calculators import judgment as module

    execute_calls: list[tuple[str, tuple[object, ...]]] = []

    async def fake_execute(sql, *params):
        execute_calls.append((sql, params))
        return None

    monkeypatch.setattr(module.db, "execute", fake_execute)

    result = module.calculate_sync(
        {
            "base_itemcode": {
                "job_id": "job-judgment-2",
                "parts": [
                    {
                        "subgraph_id": "keep",
                        "part_name": "Keep",
                        "metadata": {"wire_cut_details": [{"total_length": 12.5}]},
                    },
                    {
                        "subgraph_id": "skip",
                        "part_name": "Skip",
                        "metadata": None,
                    },
                ],
            }
        },
        subgraph_ids=["keep"],
    )

    assert result["job_id"] == "job-judgment-2"
    assert len(result["results"]) == 1
    assert result["results"][0]["subgraph_id"] == "keep"
    assert result["results"][0]["cleanup_actions"] == []
    assert execute_calls == []


def test_judgment_module_no_longer_imports_legacy_script():
    from mold_cost.domain.pricing.calculators import judgment as module

    source = Path(module.__file__).read_text(encoding="utf-8-sig")
    assert "scripts.calculate.judgment" not in source
