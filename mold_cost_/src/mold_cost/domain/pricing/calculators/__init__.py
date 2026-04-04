"""定价计算领域桥接包。"""

from __future__ import annotations

# 中文注释：当前阶段先桥接 legacy calculate 模块，
# 后续再把真正的算法实现逐个迁移到本目录。
from scripts.calculate import (
    judgment,
    price_add_auto_material,
    price_heat,
    price_material,
    price_nc_base,
    price_nc_time,
    price_nc_total,
    price_tooth_hole,
    price_total,
    price_water_mill_bevel_cost,
    price_water_mill_chamfer_cost,
    price_water_mill_component,
    price_water_mill_hanging_table,
    price_water_mill_high_cost,
    price_water_mill_long_strip,
    price_water_mill_oil_tank,
    price_water_mill_plate,
    price_water_mill_thread_ends,
    price_water_mill_total,
    price_weight,
    price_wire_base,
    price_wire_special,
    price_wire_standard,
    price_wire_total,
)

__all__ = [
    "judgment",
    "price_add_auto_material",
    "price_heat",
    "price_material",
    "price_nc_base",
    "price_nc_time",
    "price_nc_total",
    "price_tooth_hole",
    "price_total",
    "price_water_mill_bevel_cost",
    "price_water_mill_chamfer_cost",
    "price_water_mill_component",
    "price_water_mill_hanging_table",
    "price_water_mill_high_cost",
    "price_water_mill_long_strip",
    "price_water_mill_oil_tank",
    "price_water_mill_plate",
    "price_water_mill_thread_ends",
    "price_water_mill_total",
    "price_weight",
    "price_wire_base",
    "price_wire_special",
    "price_wire_standard",
    "price_wire_total",
]
