"""Pricing bridge 结构 golden 回归测试。"""

from __future__ import annotations

import asyncio
import importlib
import json
import re
from pathlib import Path

import pytest

from refactor_bootstrap import ensure_src_path
from tools.diagnostics.golden_workflow import (
    assert_manifest_contract,
    evaluate_assertion_rules,
    iter_repo_artifacts,
    load_sample_bundle,
)

ensure_src_path()

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = Path(__file__).with_name("pricing_bridge_inventory.json")
DIRECT_SCRIPTS_IMPORT_PATTERNS = (
    r"^\s*from\s+scripts\.(?:search|calculate)\b",
    r"^\s*import\s+scripts\.(?:search|calculate)\b",
)


def _load_inventory() -> dict:
    """读取 pricing bridge 的 golden inventory。"""
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def _read_repo_text(relative_path: str) -> str:
    """按仓库相对路径读取源码文本，供静态断言使用。"""
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _load_workflow_sample_bundle() -> dict:
    """中文注释：workflow golden 目前只登记一组样本，统一从 inventory 入口装载，避免测试侧写死路径。"""
    inventory = _load_inventory()
    return load_sample_bundle(inventory["golden_samples"][0])


def _load_real_pricing_part_sample() -> dict:
    """中文注释：从已提交的真实特征导出中锁定 DIE-06，保证数值回归挂钩真实零件样本而不是纯手工夹具。"""
    feature_export_path = ROOT / "scripts" / "features_export.json"
    records = json.loads(feature_export_path.read_text(encoding="utf-8"))
    return next(
        record
        for record in records
        if record.get("part_code") == "DIE-06"
        and record.get("material") == "Cr12mov"
        and record.get("heat_treatment") == "HRC50-"
    )


def test_pricing_bridge_inventory_matches_golden():
    """验证模块级 bridge 清单、包级导出和 legacy 映射保持一致。"""
    golden = _load_inventory()
    search_package = importlib.import_module("mold_cost.domain.pricing.search")
    calculator_package = importlib.import_module("mold_cost.domain.pricing.calculators")

    assert golden["pricing_driver"] == "bridge"
    assert len(golden["search_modules"]) == golden["bridge_assertions"]["search_module_count"]
    assert len(golden["calculator_modules"]) == golden["bridge_assertions"]["calculator_module_count"]
    assert sorted(search_package.__all__) == sorted(golden["search_modules"])
    assert sorted(calculator_package.__all__) == sorted(golden["calculator_modules"])

    for module_name in golden["search_modules"]:
        module = importlib.import_module(f"mold_cost.domain.pricing.search.{module_name}")
        assert getattr(search_package, module_name) is module
        assert callable(module.search_by_job_id)
        assert isinstance(module.MCP_TOOL_META, dict)
        if hasattr(module, "_legacy_module"):
            assert module._legacy_module.__name__ == golden["legacy_targets"]["search"][module_name]
        else:
            # 中文注释：已迁出模块不再桥接 legacy scripts，实现文件中也不应残留直接引用。
            module_source = Path(module.__file__).read_text(encoding="utf-8")
            assert "scripts.search." not in module_source

    for module_name in golden["calculator_modules"]:
        module = importlib.import_module(f"mold_cost.domain.pricing.calculators.{module_name}")
        assert getattr(calculator_package, module_name) is module
        assert module._legacy_module.__name__ == golden["legacy_targets"]["calculators"][module_name]
        assert callable(module.calculate)
        assert isinstance(module.MCP_TOOL_META, dict)


def test_pricing_bridge_entrypoints_do_not_import_legacy_scripts_directly():
    """验证外部入口继续只依赖 domain.pricing bridge，而不是回退到 scripts.*。"""
    golden = _load_inventory()

    for relative_path in golden["bridge_entrypoints"]:
        text = _read_repo_text(relative_path)
        for pattern in DIRECT_SCRIPTS_IMPORT_PATTERNS:
            assert re.search(pattern, text, re.MULTILINE) is None, relative_path


def test_pricing_bridge_residual_api_gateway_inventory_matches_code():
    """验证 inventory 中记录的 legacy api_gateway 反向依赖与实际代码一致。"""
    golden = _load_inventory()

    for kind, legacy_targets in golden["legacy_targets"].items():
        actual_residuals = []
        for module_name, legacy_module in legacy_targets.items():
            legacy_path = ROOT / Path(*legacy_module.split("."))
            legacy_code = legacy_path.with_suffix(".py").read_text(encoding="utf-8")
            if "api_gateway." in legacy_code:
                actual_residuals.append(module_name)

        assert sorted(actual_residuals) == sorted(golden["legacy_api_gateway_dependencies"][kind])


def test_pricing_bridge_next_extract_candidates_remain_actionable():
    """验证下一批迁移候选仍然存在、可导入，并且仍落在 legacy 脚本实现里。"""
    golden = _load_inventory()
    candidates = golden["next_extract_candidates"]
    search_targets = golden["legacy_targets"]["search"]
    calculator_targets = golden["legacy_targets"]["calculators"]
    legacy_db_markers = (
        "mold_cost.infrastructure.db.repositories.script_db",
        "batch_upsert_with_steps",
        "db.fetch_all(",
        "db.execute(",
    )

    assert 3 <= len(candidates) <= 5

    for candidate in candidates:
        module_path = candidate["module"]
        legacy_module = candidate["legacy_module"]
        reason = candidate["reason"]
        module_name = module_path.rsplit(".", 1)[-1]
        legacy_code = (ROOT / Path(*legacy_module.split("."))).with_suffix(".py").read_text(encoding="utf-8")

        imported = importlib.import_module(module_path)
        assert imported is not None
        assert reason.strip()
        assert any(marker in legacy_code for marker in legacy_db_markers)

        if ".search." in module_path:
            assert legacy_module == search_targets[module_name]
            assert hasattr(imported, "_legacy_module")
        else:
            assert legacy_module == calculator_targets[module_name]


def test_pricing_workflow_samples_have_valid_contracts():
    """验证 workflow 级 golden 样本具备 manifest + summary + rules 三件套。"""
    inventory = _load_inventory()

    for sample_entry in inventory["golden_samples"]:
        # 中文注释：样本入口只在 inventory 中登记一次，测试统一从这里发现，避免定义分叉。
        bundle = load_sample_bundle(sample_entry)
        manifest = bundle["manifest"]

        assert manifest["sample_id"] == sample_entry["sample_id"]
        assert_manifest_contract(manifest)

        for _stage_name, _artifact, resolved_path in iter_repo_artifacts(manifest):
            assert resolved_path.exists()

        evaluate_assertion_rules(
            manifest=manifest,
            expected_summary=bundle["expected_summary"],
            assertion_rules=bundle["assertion_rules"],
            inventory=inventory,
        )


def test_pricing_workflow_sample_baseline_matches_legacy_cost_calculators(monkeypatch):
    """验证真实 DIE-06 样本在当前 baseline pricing 输入下，关键费用字段保持数值稳定。"""
    bundle = _load_workflow_sample_bundle()
    expected_baseline = bundle["expected_summary"]["business_outcome"]["pricing_baseline"]
    real_part = _load_real_pricing_part_sample()

    assert real_part["part_code"] == expected_baseline["part_code"]
    assert real_part["material"] == expected_baseline["material"]
    assert real_part["heat_treatment"] == expected_baseline["heat_treatment"]
    assert real_part["length_mm"] == expected_baseline["dimensions_mm"]["length"]
    assert real_part["width_mm"] == expected_baseline["dimensions_mm"]["width"]
    assert real_part["thickness_mm"] == expected_baseline["dimensions_mm"]["thickness"]

    price_wire_total_module = importlib.import_module("scripts.calculate.price_wire_total")
    price_total_module = importlib.import_module("scripts.calculate.price_total")

    async def fake_batch_update_subgraphs(*args, **kwargs):
        # 中文注释：golden 只验证计算结果，不触碰数据库落盘。
        return None

    async def fake_batch_upsert_with_steps(*args, **kwargs):
        # 中文注释：计算步骤在业务模块里生成即可，这里跳过持久化副作用。
        return None

    async def fake_update_process_descriptions(*args, **kwargs):
        return None

    async def fake_update_job_total_cost(*args, **kwargs):
        return None

    monkeypatch.setattr(price_wire_total_module, "_batch_update_subgraphs", fake_batch_update_subgraphs)
    monkeypatch.setattr(price_wire_total_module, "batch_upsert_with_steps", fake_batch_upsert_with_steps)
    monkeypatch.setattr(price_total_module, "_batch_update_subgraphs", fake_batch_update_subgraphs)
    monkeypatch.setattr(price_total_module, "_update_process_descriptions", fake_update_process_descriptions)
    monkeypatch.setattr(price_total_module, "_update_job_total_cost", fake_update_job_total_cost)

    subgraph_id = "workflow_pricing_m250286_p3::DIE-06"
    wire_total_result = asyncio.run(
        price_wire_total_module.calculate(
            search_data={
                "base_itemcode": {
                    "job_id": "workflow-pricing-golden",
                    "parts": [
                        {
                            "subgraph_id": subgraph_id,
                            "part_name": real_part["part_code"],
                            "quantity": expected_baseline["quantity"],
                            "metadata": {},
                        }
                    ],
                },
                "total": {
                    "job_id": "workflow-pricing-golden",
                    "cost_details": [
                        {
                            "subgraph_id": subgraph_id,
                            "weight": expected_baseline["weight_kg"],
                            "basic_processing_cost": 0.0,
                            "special_base_cost": 0.0,
                            "standard_base_cost": 0.0,
                            "material_additional_cost": 0.0,
                            "material_cost": expected_baseline["material_cost"],
                            "heat_treatment_cost": expected_baseline["heat_treatment_cost"],
                            "tooth_hole_cost": 0.0,
                            "tooth_hole_time_cost": 0.0,
                            "calculation_steps": [],
                        }
                    ],
                },
            },
            job_id="workflow-pricing-golden",
            subgraph_ids=[subgraph_id],
        )
    )
    wire_total_part = wire_total_result["results"][0]

    assert wire_total_part["weight_kg"] == pytest.approx(expected_baseline["weight_kg"])
    assert wire_total_part["material_cost"] == pytest.approx(expected_baseline["material_cost"])
    assert wire_total_part["heat_treatment_cost"] == pytest.approx(expected_baseline["heat_treatment_cost"])
    assert wire_total_part["fast_wire_cost"] == pytest.approx(0.0)
    assert wire_total_part["edm_cost"] == pytest.approx(0.0)

    final_total_result = asyncio.run(
        price_total_module.calculate(
            search_data={
                "subgraphs_cost": {
                    "job_id": "workflow-pricing-golden",
                    "cost_summary": [
                        {
                            "subgraph_id": subgraph_id,
                            "material_cost": wire_total_part["material_cost"],
                            "heat_treatment_cost": wire_total_part["heat_treatment_cost"],
                            "large_grinding_cost": 0.0,
                            "small_grinding_cost": 0.0,
                            "slow_wire_cost": wire_total_part["slow_wire_cost"],
                            "slow_wire_side_cost": 0.0,
                            "mid_wire_cost": wire_total_part["mid_wire_cost"],
                            "fast_wire_cost": wire_total_part["fast_wire_cost"],
                            "edm_cost": wire_total_part["edm_cost"],
                            "nc_roughing_cost": 0.0,
                            "nc_milling_cost": 0.0,
                            "drilling_cost": 0.0,
                        }
                    ],
                }
            },
            job_id="workflow-pricing-golden",
            subgraph_ids=[subgraph_id],
        )
    )
    final_total_part = final_total_result["results"][0]

    assert final_total_part["processing_cost_total"] == pytest.approx(expected_baseline["processing_cost_total"])
    assert final_total_part["total_cost"] == pytest.approx(expected_baseline["total_cost"])
    assert final_total_result["job_total_cost"] == pytest.approx(expected_baseline["total_cost"])
