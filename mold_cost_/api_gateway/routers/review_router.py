"""审核路由兼容层。

保留现有 HTTP 接口路径，
内部实现统一转发到 application/use_cases。
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from refactor_bootstrap import ensure_src_path
from shared.database import get_db
from shared.unified_logging import get_logger
from ..auth import get_current_user
from api_gateway.utils.chat_logger import (
    ensure_session_exists,
    log_assistant_message,
    log_user_message,
)

ensure_src_path()

from mold_cost.application.use_cases import (  # noqa: E402
    ConfirmReviewUseCase,
    GetReviewStateUseCase,
    ModifyReviewUseCase,
    RefreshReviewDataUseCase,
    StartReviewUseCase,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/review", tags=["review"])


class StartReviewRequest(BaseModel):
    """启动审核请求。"""

    job_id: str = Field(..., description="任务 ID")


class ModificationRequest(BaseModel):
    """审核修改请求。"""

    modification_text: str = Field(..., description="自然语言修改指令", min_length=1)


class ConfirmRequest(BaseModel):
    """确认请求。"""

    comment: Optional[str] = Field(None, description="确认备注")


@router.post("/start")
async def start_review(
    request: StartReviewRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """启动审核流程。"""
    try:
        await ensure_session_exists(
            db,
            session_id=request.job_id,
            job_id=request.job_id,
            user_id=current_user["user_id"],
            metadata={"action": "start_review"},
        )

        use_case = StartReviewUseCase()
        result = await use_case.execute(job_id=request.job_id, db_session=db)

        if result.status == "error":
            if "其他用户" in result.message:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error": "REVIEW_LOCKED", "message": result.message},
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "START_REVIEW_FAILED", "message": result.message},
            )

        await db.commit()
        return {"status": "ok", "message": result.message, "data": result.data}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("启动审核异常: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": f"服务端内部错误: {str(exc)}"},
        )


@router.post("/{job_id}/modify")
async def modify_review(
    job_id: str,
    request: ModificationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """处理审核修改。"""
    try:
        await ensure_session_exists(
            db,
            session_id=job_id,
            job_id=job_id,
            user_id=current_user["user_id"],
            metadata={"action": "modify"},
        )

        await log_user_message(
            db,
            session_id=job_id,
            content=request.modification_text,
            metadata={"user_id": current_user["user_id"], "action": "modify"},
        )
        await db.commit()

        use_case = ModifyReviewUseCase()
        result = await use_case.execute(
            job_id=job_id,
            modification_text=request.modification_text,
            user_id=current_user["user_id"],
            db_session=db,
        )

        if result.status == "error":
            if "未找到审核会话" in result.message or "审核会话已过期" in result.message:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"error": "SESSION_NOT_FOUND", "message": result.message},
                )
            if "处理修改失败" in result.message:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"error": "MODIFICATION_FAILED", "message": result.message},
                )

            await log_assistant_message(
                db,
                session_id=job_id,
                content=result.message,
                metadata={
                    "intent": result.data.get("intent") if result.data else None,
                    "action": "modify_response",
                    "is_business_error": True,
                },
            )
            await db.commit()
            return {
                "status": "ok",
                "intent": result.data.get("intent") if result.data else None,
                "message": result.message,
                "requires_confirmation": False,
                "data": result.data or {},
            }

        await log_assistant_message(
            db,
            session_id=job_id,
            content=result.message,
            metadata={
                "intent": result.data.get("intent") if result.data else None,
                "requires_confirmation": result.data.get("requires_confirmation") if result.data else False,
                "action": "modify_response",
            },
        )
        await db.commit()

        return {
            "status": "ok",
            "intent": result.data.get("intent") if result.data else None,
            "message": result.message,
            "requires_confirmation": result.data.get("requires_confirmation") if result.data else False,
            "data": result.data,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("处理审核修改异常: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": f"服务端内部错误: {str(exc)}"},
        )


@router.post("/{job_id}/confirm")
async def confirm_review(
    job_id: str,
    request: ConfirmRequest | None = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """确认审核修改并写回数据库。"""
    try:
        await ensure_session_exists(
            db,
            session_id=job_id,
            job_id=job_id,
            user_id=current_user["user_id"],
            metadata={"action": "confirm", "comment": request.comment if request else None},
        )

        use_case = ConfirmReviewUseCase()
        result = await use_case.execute(job_id=job_id, user_id=current_user["user_id"], db_session=db)

        if result.status == "error":
            if "数据已被其他系统修改" in result.message:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "VERSION_CONFLICT",
                        "message": result.message,
                        "conflicts": result.data.get("conflicts", []),
                        "suggestion": "数据已被修改，请刷新后重新审核",
                    },
                )
            if "未找到审核会话" in result.message:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"error": "SESSION_NOT_FOUND", "message": result.message},
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "CONFIRM_FAILED", "message": result.message},
            )

        await db.commit()
        return {"status": "ok", "message": result.message, "data": result.data}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("确认审核异常: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": f"服务端内部错误: {str(exc)}"},
        )


@router.post("/{job_id}/refresh")
async def refresh_review_data(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """刷新审核数据。"""
    try:
        use_case = RefreshReviewDataUseCase()
        result = await use_case.execute(job_id=job_id, db_session=db)

        if result.status == "error":
            if "其他用户" in result.message:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error": "REVIEW_LOCKED", "message": result.message},
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "REFRESH_FAILED", "message": result.message},
            )

        await db.commit()
        return {"status": "ok", "message": result.message, "data": result.data}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("刷新审核数据异常: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": f"服务端内部错误: {str(exc)}"},
        )


@router.get("/{job_id}/status")
async def get_review_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """查询审核状态。"""
    try:
        use_case = GetReviewStateUseCase()
        payload = await use_case.execute_with_lock(job_id=job_id)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "SESSION_NOT_FOUND", "message": "未找到审核会话"},
            )

        state = payload["state"]
        return {
            "status": "ok",
            "data": {
                "job_id": job_id,
                "review_status": state.get("status"),
                "is_locked": payload["is_locked"],
                "modifications_count": len(state.get("modifications", [])),
                "created_at": state.get("created_at"),
                "last_modified_at": state.get("last_modified_at"),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("查询审核状态异常: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": f"服务端内部错误: {str(exc)}"},
        )
