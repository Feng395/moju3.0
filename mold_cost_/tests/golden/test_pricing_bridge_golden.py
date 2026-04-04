"""Pricing bridge 结构化 golden 回归测试。"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_pricing_bridge_inventory_matches_golden():
    """验证 pricing bridge 模块清单与 golden 基线一致。"""
    golden_path = Path(__file__).with_name("pricing_bridge_inventory.json")
    golden = json.loads(golden_path.read_text(encoding="utf-8"))

    for module_name in golden["search_modules"]:
        module = importlib.import_module(f"mold_cost.domain.pricing.search.{module_name}")
        assert module is not None

    for module_name in golden["calculator_modules"]:
        module = importlib.import_module(f"mold_cost.domain.pricing.calculators.{module_name}")
        assert module is not None
