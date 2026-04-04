"""定价搜索迁移测试。"""

from __future__ import annotations

import asyncio
import importlib

import pytest

from refactor_bootstrap import ensure_src_path

ensure_src_path()

SEARCH_CASES = (
    {
        "module_name": "density_search",
        "legacy_module": "scripts.search.density_search",
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
        "categories": ("heat",),
        "columns": ("sub_category", "price", "unit"),
        "rows": [
            {"sub_category": "真空热处理", "price": 2.3, "unit": "kg"},
        ],
    },
    {
        "module_name": "material_search",
        "legacy_module": "scripts.search.material_search",
        "categories": ("material",),
        "columns": ("sub_category", "price", "unit"),
        "rows": [
            {"sub_category": "45#", "price": 9.1, "unit": "kg"},
        ],
    },
    {
        "module_name": "nc_search",
        "legacy_module": "scripts.search.nc_search",
        "categories": ("NC",),
        "columns": ("category", "sub_category", "price", "unit", "min_num"),
        "rows": [
            {"category": "NC", "sub_category": "work_hour", "price": 60, "unit": "hour", "min_num": 1},
            {"category": "NC", "sub_category": "nc_base", "price": 120, "unit": "set", "min_num": 2},
        ],
    },
    {
        "module_name": "wire_standard_search",
        "legacy_module": "scripts.search.wire_standard_search",
        "categories": ("base",),
        "columns": ("sub_category", "price", "unit"),
        "rows": [
            {"sub_category": "base_fee", "price": 25, "unit": "piece"},
            {"sub_category": "boring_fee", "price": 8, "unit": "hole"},
        ],
    },
)


@pytest.mark.parametrize("case", SEARCH_CASES, ids=[case["module_name"] for case in SEARCH_CASES])
def test_migrated_pricing_search_matches_legacy_behavior(monkeypatch, case):
    """验证已迁出搜索模块与 legacy 输出保持一致。"""
    legacy_module = importlib.import_module(case["legacy_module"])
    domain_module = importlib.import_module(f"mold_cost.domain.pricing.search.{case['module_name']}")
    legacy_calls: list[dict] = []
    domain_calls: list[dict] = []

    async def fake_legacy_fetch_all(query, job_id, *args):
        legacy_calls.append({"query": query, "job_id": job_id, "args": args})
        return [dict(row) for row in case["rows"]]

    async def fake_domain_fetch_snapshots(*, job_id, categories, columns):
        domain_calls.append(
            {
                "job_id": job_id,
                "categories": tuple(categories),
                "columns": tuple(columns),
            }
        )
        return [dict(row) for row in case["rows"]]

    monkeypatch.setattr(legacy_module.db, "fetch_all", fake_legacy_fetch_all)
    monkeypatch.setattr(
        domain_module.pricing_snapshot_search_service,
        "fetch_snapshots",
        fake_domain_fetch_snapshots,
    )

    legacy_result = asyncio.run(legacy_module.search_by_job_id("job-search", ["sub-1"]))
    domain_result = asyncio.run(domain_module.search_by_job_id("job-search", ["sub-1"]))

    assert domain_result == legacy_result
    assert legacy_calls[0]["job_id"] == "job-search"
    assert domain_calls == [
        {
            "job_id": "job-search",
            "categories": case["categories"],
            "columns": case["columns"],
        }
    ]


def test_migrated_pricing_search_modules_do_not_expose_legacy_module():
    """验证本轮迁出的搜索模块已经去掉 legacy bridge。"""
    migrated_modules = (
        "density_search",
        "heat_search",
        "material_search",
        "nc_search",
        "wire_standard_search",
    )

    for module_name in migrated_modules:
        module = importlib.import_module(f"mold_cost.domain.pricing.search.{module_name}")
        assert not hasattr(module, "_legacy_module")
