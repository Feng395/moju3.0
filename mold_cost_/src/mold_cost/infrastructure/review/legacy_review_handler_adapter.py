"""Legacy review handler compatibility facade."""

from __future__ import annotations

from .review_change_applier_runtime import build_src_review_change_applier


def build_default_review_change_applier(*, state_store, review_repository):
    """兼容旧导入路径，实际转发到 src 侧 change applier runtime。"""
    # 中文注释：旧模块名继续保留，避免测试和兼容入口一次性全部改名。
    return build_src_review_change_applier(
        state_store=state_store,
        review_repository=review_repository,
    )
