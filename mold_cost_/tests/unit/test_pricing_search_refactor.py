"""Pricing search migration tests."""

from __future__ import annotations

import asyncio
import importlib

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()

SEARCH_CASES = (
    {
        "module_name": "base_itemcode_search",
        "legacy_module": "scripts.search.base_itemcode_search",
        "service_method": "fetch_base_itemcode_parts",
        "rows": [
            {
                "subgraph_id": "sg-1",
                "part_name": "Punch A",
                "part_code": "PA-01",
                "wire_process_note": "note-a",
                "wire_process": "wire-a",
                "length_mm": 100.0,
                "width_mm": 50.0,
                "thickness_mm": 10.0,
                "metadata": {"color": "blue"},
                "water_mill": {"enabled": True},
                "quantity": 2,
                "boring_num": 3,
                "material": "Cr12mov",
                "has_auto_material": True,
                "has_material_preparation": False,
                "needs_heat_treatment": True,
                "tooth_hole": {"count": 4},
                "nc_time_cost": {"hours": 1.5},
            }
        ],
    },
    {
        "module_name": "density_search",
        "legacy_module": "scripts.search.density_search",
        "service_method": "fetch_snapshots",
        "categories": ("density",),
        "columns": ("sub_category", "price", "unit"),
        "rows": [
            {"sub_category": "SKD11", "price": 7.8, "unit": "kg"},
            {"sub_category": "NAK80", "price": 12.5, "unit": "kg"},
        ],
    },
    {
        "module_name": "heat_search",
        "legacy_module": "scripts.search.heat_search",
        "service_method": "fetch_snapshots",
        "categories": ("heat",),
        "columns": ("sub_category", "price", "unit"),
        "rows": [
            {"sub_category": "?????", "price": 2.3, "unit": "kg"},
        ],
    },
    {
        "module_name": "material_search",
        "legacy_module": "scripts.search.material_search",
        "service_method": "fetch_snapshots",
        "categories": ("material",),
        "columns": ("sub_category", "price", "unit"),
        "rows": [
            {"sub_category": "45#", "price": 9.1, "unit": "kg"},
        ],
    },
    {
        "module_name": "nc_search",
        "legacy_module": "scripts.search.nc_search",
        "service_method": "fetch_snapshots",
        "categories": ("NC",),
        "columns": ("category", "sub_category", "price", "unit", "min_num"),
        "rows": [
            {"category": "NC", "sub_category": "work_hour", "price": 60, "unit": "hour", "min_num": 1},
            {"category": "NC", "sub_category": "nc_base", "price": 120, "unit": "set", "min_num": 2},
        ],
    },
    {
        "module_name": "tooth_hole_search",
        "legacy_module": "scripts.search.tooth_hole_search",
        "service_method": "fetch_snapshots",
        "categories": ("tooth_hole", "screw", "stop_screw"),
        "columns": ("category", "sub_category", "price", "unit", "min_num"),
        "rows": [
            {"category": "tooth_hole", "sub_category": "std", "price": 3.5, "unit": "hole", "min_num": 1},
            {"category": "screw", "sub_category": "m6", "price": 0.8, "unit": "piece", "min_num": 10},
            {"category": "stop_screw", "sub_category": "m8", "price": 1.2, "unit": "piece", "min_num": 5},
        ],
    },
    {
        "module_name": "water_mill_search",
        "legacy_module": "scripts.search.water_mill_search",
        "service_method": "fetch_snapshots",
        "categories": ("S_water_mill", "L_water_mill"),
        "columns": ("category", "sub_category", "price", "unit", "min_num"),
        "rows": [
            {"category": "S_water_mill", "sub_category": "s-1", "price": 11.0, "unit": "piece", "min_num": 1},
            {"category": "L_water_mill", "sub_category": "l-1", "price": 18.0, "unit": "piece", "min_num": 1},
        ],
    },
    {
        "module_name": "wire_base_search",
        "legacy_module": "scripts.search.wire_base_search",
        "service_method": "fetch_snapshots",
        "categories": ("wire", "rule"),
        "columns": ("category", "sub_category", "price", "unit", "note", "min_num"),
        "rows": [
            {"category": "wire", "sub_category": "wire-a", "price": 15.0, "unit": "meter", "note": "Wire A", "min_num": 1},
            {"category": "wire", "sub_category": "wire-b", "price": 20.0, "unit": "meter", "note": None, "min_num": 2},
            {"category": "rule", "sub_category": "rule-a", "price": 5.0, "unit": "set", "note": None, "min_num": 1},
        ],
    },
    {
        "module_name": "wire_special_search",
        "legacy_module": "scripts.search.wire_special_search",
        "service_method": "fetch_snapshots",
        "categories": ("special", "rule"),
        "columns": ("category", "sub_category", "price", "unit"),
        "rows": [
            {"category": "special", "sub_category": "special-a", "price": 31.0, "unit": "piece"},
            {"category": "rule", "sub_category": "rule-a", "price": 4.0, "unit": "set"},
        ],
    },
    {
        "module_name": "wire_standard_search",
        "legacy_module": "scripts.search.wire_standard_search",
        "service_method": "fetch_snapshots",
        "categories": ("base",),
        "columns": ("sub_category", "price", "unit"),
        "rows": [
            {"sub_category": "base_fee", "price": 25, "unit": "piece"},
            {"sub_category": "boring_fee", "price": 8, "unit": "hole"},
        ],
    },
    {
        "module_name": "search",
        "legacy_module": "scripts.search.search",
        "service_method": "fetch_subgraph_cost_summary",
        "rows": [
            {
                "subgraph_id": "sg-1",
                "material_cost": 10.0,
                "heat_treatment_cost": 3.0,
                "large_grinding_cost": 1.0,
                "small_grinding_cost": 2.0,
                "slow_wire_cost": 4.0,
                "slow_wire_side_cost": 5.0,
                "mid_wire_cost": 6.0,
                "fast_wire_cost": 7.0,
                "edm_cost": 8.0,
                "nc_roughing_cost": 9.0,
                "nc_milling_cost": 11.0,
                "drilling_cost": 12.0,
            }
        ],
    },
    {
        "module_name": "total_search",
        "legacy_module": "scripts.search.total_search",
        "service_method": "fetch_processing_cost_details",
        "rows": [
            {
                "subgraph_id": "sg-1",
                "weight": 5.664,
                "basic_processing_cost": 1.0,
                "special_base_cost": 2.0,
                "standard_base_cost": 3.0,
                "material_additional_cost": 4.0,
                "material_cost": 66.83,
                "heat_treatment_cost": 21.52,
                "thread_ends_cost": 5.0,
                "hanging_table_cost": 6.0,
                "chamfer_cost": 7.0,
                "bevel_cost": 8.0,
                "oil_tank_cost": 9.0,
                "high_cost": 10.0,
                "grinding_cost": 11.0,
                "plate_cost": 12.0,
                "long_strip_cost": 13.0,
                "component_cost": 14.0,
                "tooth_hole_cost": 15.0,
                "tooth_hole_time_cost": 16.0,
                "nc_roughing_cost": 17.0,
                "nc_milling_cost": 18.0,
                "nc_drilling_cost": 19.0,
                "nc_base_roughing_cost": 20.0,
                "nc_base_milling_cost": 21.0,
                "nc_base_drilling_cost": 22.0,
                "calculation_steps": [{"category": "wire", "steps": [{"step": "base"}]}],
            }
        ],
    },
    {
        "module_name": "wire_total_search",
        "legacy_module": "scripts.search.wire_total_search",
        "service_method": "fetch_processing_cost_details",
        "rows": [
            {
                "subgraph_id": "sg-1",
                "weight": 5.664,
                "basic_processing_cost": 1.0,
                "special_base_cost": 2.0,
                "standard_base_cost": 3.0,
                "material_additional_cost": 4.0,
                "material_cost": 66.83,
                "heat_treatment_cost": 21.52,
                "thread_ends_cost": 5.0,
                "hanging_table_cost": 6.0,
                "chamfer_cost": 7.0,
                "bevel_cost": 8.0,
                "oil_tank_cost": 9.0,
                "high_cost": 10.0,
                "grinding_cost": 11.0,
                "plate_cost": 12.0,
                "long_strip_cost": 13.0,
                "component_cost": 14.0,
                "tooth_hole_cost": 15.0,
                "tooth_hole_time_cost": 16.0,
                "nc_roughing_cost": 17.0,
                "nc_milling_cost": 18.0,
                "nc_drilling_cost": 19.0,
                "nc_base_roughing_cost": 20.0,
                "nc_base_milling_cost": 21.0,
                "nc_base_drilling_cost": 22.0,
                "calculation_steps": [{"category": "wire", "steps": [{"step": "base"}]}],
            }
        ],
    },
)


@pytest.mark.parametrize("case", SEARCH_CASES, ids=[case["module_name"] for case in SEARCH_CASES])
def test_migrated_pricing_search_matches_legacy_behavior(monkeypatch, case):
    """Verify migrated modules keep the expected domain contract."""
    domain_module = importlib.import_module(f"mold_cost.domain.pricing.search.{case['module_name']}")
    domain_calls: list[dict] = []

    if case["service_method"] == "fetch_base_itemcode_parts":
        async def fake_domain_fetch_base_itemcode_parts(*, job_id, subgraph_ids):
            domain_calls.append({"job_id": job_id, "subgraph_ids": tuple(subgraph_ids)})
            return [dict(row) for row in case["rows"]]

        monkeypatch.setattr(
            domain_module.pricing_snapshot_search_service,
            "fetch_base_itemcode_parts",
            fake_domain_fetch_base_itemcode_parts,
        )
    elif case["service_method"] == "fetch_processing_cost_details":
        async def fake_domain_fetch_processing_cost_details(*, job_id, subgraph_ids):
            domain_calls.append({"job_id": job_id, "subgraph_ids": tuple(subgraph_ids)})
            return [dict(row) for row in case["rows"]]

        monkeypatch.setattr(
            domain_module.pricing_snapshot_search_service,
            "fetch_processing_cost_details",
            fake_domain_fetch_processing_cost_details,
        )
    elif case["service_method"] == "fetch_subgraph_cost_summary":
        async def fake_domain_fetch_subgraph_cost_summary(*, job_id, subgraph_ids):
            domain_calls.append({"job_id": job_id, "subgraph_ids": tuple(subgraph_ids)})
            return [dict(row) for row in case["rows"]]

        monkeypatch.setattr(
            domain_module.pricing_snapshot_search_service,
            "fetch_subgraph_cost_summary",
            fake_domain_fetch_subgraph_cost_summary,
        )
    else:
        async def fake_domain_fetch_snapshots(*, job_id, categories, columns):
            domain_calls.append(
                {
                    "job_id": job_id,
                    "categories": tuple(categories),
                    "columns": tuple(columns),
                }
            )
            return [dict(row) for row in case["rows"]]

        monkeypatch.setattr(
            domain_module.pricing_snapshot_search_service,
            "fetch_snapshots",
            fake_domain_fetch_snapshots,
        )

    domain_result = asyncio.run(domain_module.search_by_job_id("job-search", ["sub-1"]))

    assert domain_result == _expected_domain_result(case, job_id="job-search")

    if case["service_method"] == "fetch_base_itemcode_parts":
        assert domain_calls == [{"job_id": "job-search", "subgraph_ids": ("sub-1",)}]
    elif case["service_method"] in {"fetch_processing_cost_details", "fetch_subgraph_cost_summary"}:
        assert domain_calls == [{"job_id": "job-search", "subgraph_ids": ("sub-1",)}]
    else:
        assert domain_calls == [
            {
                "job_id": "job-search",
                "categories": case["categories"],
                "columns": case["columns"],
            }
        ]


def test_migrated_pricing_search_modules_do_not_expose_legacy_module():
    """Verify migrated modules no longer expose a legacy bridge object."""
    migrated_modules = (
        "base_itemcode_search",
        "density_search",
        "heat_search",
        "material_search",
        "nc_search",
        "search",
        "tooth_hole_search",
        "total_search",
        "water_mill_search",
        "wire_base_search",
        "wire_special_search",
        "wire_standard_search",
        "wire_total_search",
    )

    for module_name in migrated_modules:
        module = importlib.import_module(f"mold_cost.domain.pricing.search.{module_name}")
        assert not hasattr(module, "_legacy_module")
        assert callable(module.search_by_job_id)
        assert callable(module.search_by_job_id_sync)
        assert isinstance(module.MCP_TOOL_META, dict)


def _expected_domain_result(case: dict, *, job_id: str) -> dict:
    rows = [dict(row) for row in case["rows"]]
    module_name = case["module_name"]

    if module_name == "base_itemcode_search":
        return {
            "data_type": "base_itemcode",
            "job_id": job_id,
            "parts": rows,
        }
    if module_name == "density_search":
        return {
            "data_type": "density",
            "job_id": job_id,
            "density_data": rows,
        }
    if module_name == "heat_search":
        return {
            "data_type": "heat",
            "job_id": job_id,
            "heat_prices": rows,
        }
    if module_name == "material_search":
        return {
            "data_type": "material",
            "job_id": job_id,
            "material_prices": rows,
        }
    if module_name == "nc_search":
        return {
            "data_type": "nc",
            "job_id": job_id,
            "nc_prices": rows,
        }
    if module_name == "tooth_hole_search":
        return {
            "data_type": "tooth_hole",
            "job_id": job_id,
            "tooth_hole_prices": [row for row in rows if row.get("category") == "tooth_hole"],
            "screw_prices": [row for row in rows if row.get("category") == "screw"],
            "stop_screw_prices": [row for row in rows if row.get("category") == "stop_screw"],
        }
    if module_name == "water_mill_search":
        return {
            "data_type": "water_mill",
            "job_id": job_id,
            "s_water_mill_prices": [row for row in rows if row.get("category") == "S_water_mill"],
            "l_water_mill_prices": [row for row in rows if row.get("category") == "L_water_mill"],
        }
    if module_name == "wire_base_search":
        wire_prices = [row for row in rows if row.get("category") == "wire"]
        rule_prices = [row for row in rows if row.get("category") == "rule"]
        wire_parts = []
        for price_info in wire_prices:
            sub_category = price_info.get("sub_category")
            note = price_info.get("note") or sub_category
            wire_parts.append(
                {
                    "name": note,
                    "conditions": sub_category,
                    "description": note,
                    "price": price_info.get("price"),
                    "unit": price_info.get("unit"),
                    "min_num": price_info.get("min_num"),
                }
            )
        return {
            "data_type": "wire_base",
            "job_id": job_id,
            "wire_parts": wire_parts,
            "rule_prices": rule_prices,
        }
    if module_name == "wire_special_search":
        return {
            "data_type": "wire_special",
            "job_id": job_id,
            "special_prices": [row for row in rows if row.get("category") == "special"],
            "rule_prices": [row for row in rows if row.get("category") == "rule"],
        }
    if module_name == "wire_standard_search":
        return {
            "data_type": "wire_standard",
            "job_id": job_id,
            "base_prices": rows,
        }
    if module_name == "search":
        return {
            "data_type": "subgraphs_cost",
            "job_id": job_id,
            "cost_summary": rows,
        }
    if module_name == "total_search":
        return {
            "data_type": "total",
            "job_id": job_id,
            "cost_details": rows,
        }
    if module_name == "wire_total_search":
        return {
            "data_type": "total",
            "job_id": job_id,
            "cost_details": [
                {
                    "subgraph_id": row["subgraph_id"],
                    "weight": row["weight"],
                    "basic_processing_cost": row["basic_processing_cost"],
                    "special_base_cost": row["special_base_cost"],
                    "standard_base_cost": row["standard_base_cost"],
                    "material_additional_cost": row["material_additional_cost"],
                    "material_cost": row["material_cost"],
                    "heat_treatment_cost": row["heat_treatment_cost"],
                    "calculation_steps": row["calculation_steps"],
                }
                for row in rows
            ],
        }
    raise AssertionError(f"Unsupported module_name: {module_name}")
