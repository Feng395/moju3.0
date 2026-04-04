"""Pricing bridge 结构 golden 回归测试。"""

from __future__ import annotations

import importlib
import json
import re
from pathlib import Path

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
        assert module._legacy_module.__name__ == golden["legacy_targets"]["search"][module_name]
        assert callable(module.search_by_job_id)
        assert isinstance(module.MCP_TOOL_META, dict)

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
        else:
            assert legacy_module == calculator_targets[module_name]


def test_pricing_workflow_samples_have_valid_contracts():
    """验证 workflow 级 golden 样本具备 manifest + summary + rules 三件套。"""
    inventory = _load_inventory()

    for sample_entry in inventory["golden_samples"]:
        # 中文注释：样本入口只在 inventory 中登记一次，测试侧统一从这里发现。
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
