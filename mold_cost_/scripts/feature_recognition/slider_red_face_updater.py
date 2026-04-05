# -*- coding: utf-8 -*-
"""兼容入口：滑块红色面写回逻辑已迁移到 src runtime。"""

from __future__ import annotations

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.cad.slider_red_face_update_runtime import update_slider_red_face_data

__all__ = ["update_slider_red_face_data"]
