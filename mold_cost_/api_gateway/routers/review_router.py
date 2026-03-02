"""
=== 文件合并信息 ===
合并日期: 2026-02-10
源文件: mold_cost_/api_gateway/routers/review_router.py (独有文件)
合并策略: 保留 mold_cost_ 版本（mold_cost-main 无此文件）
主要改动: 无改动，直接保留
说明: 审核系统路由，处理审核流程、修改确认和状态查询
=====================

审核系统路由 (Review Router)
负责人：人员B2

职责：
1. 启动审核流程
2. 处理用户修改
3. 确认修改
4. 查询审核状态

阶段2.1实现
"""
from shared.unified_logging import get_logger
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from shared.database import get_db
from ..auth import get_current_user
from agents.interaction_agent import InteractionAgent
from api_gateway.utils.chat_logger import (
    ensure_session_exists,
    log_system_message,
    log_user_message,
    log_assistant_message
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/review", tags=["review"])


# ========== 请求模型 ==========

class StartReviewRequest(BaseModel):
    """启动审核请求"""
    job_id: str = Field(..., description="任务ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class ModificationRequest(BaseModel):
    """修改请求"""
    modification_text: str = Field(..., description="自然语言修改指令", min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "modification_text": "将 UP01 的材质改为 718"
            }
        }


class ConfirmRequest(BaseModel):
    """确认请求（可选，用于扩展）"""
    comment: Optional[str] = Field(None, description="确认备注")
    
    class Config:
        json_schema_extra = {
            "example": {
                "comment": "审核通过"
            }
        }


# ========== 路由处理器 ==========

@router.post("/start")
async def start_review(
    request: StartReviewRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    启动审核流程
    
    功能：
    1. 查询 3 个表的数据
    2. 保存到 Redis
    3. 推送到前端（WebSocket）
    4. 获取分布式锁
    
    Args:
        request: 启动审核请求
        current_user: 当前用户（从JWT获取）
        db: 数据库会话
    
    Returns:
        {
            "status": "ok",
            "message": "审核已启动",
            "data": {
                "job_id": "xxx",
                "features_count": 10,
                "price_snapshots_count": 5,
                "subgraphs_count": 2
            }
        }
    
    Raises:
        400: 参数错误
        403: 权限不足
        409: 任务正在被其他用户审核
        500: 服务器错误
    """
    try:
        logger.info(f"📋 启动审核: job_id={request.job_id}, user_id={current_user['user_id']}")
        
        # 1. 确保会话存在
        await ensure_session_exists(
            db,
            session_id=request.job_id,
            job_id=request.job_id,
            user_id=current_user["user_id"],
            metadata={"action": "start_review"}
        )
        
        # 2. 创建 InteractionAgent
        agent = InteractionAgent()
        
        # 3. 启动审核
        result = await agent.start_review(
            job_id=request.job_id,
            db_session=db
        )
        
        # 4. 检查结果
        if result.status == "error":
            # 根据错误类型返回不同的HTTP状态码
            if "正在被其他用户审核" in result.message:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "REVIEW_LOCKED",
                        "message": result.message
                    }
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error": "START_REVIEW_FAILED",
                        "message": result.message
                    }
                )
        
        # 🆕 不再记录审核启动消息（前端已通过 HTTP 响应知道启动成功）
        # 前端通过 HTTP 响应知道启动成功：
        # {"status": "ok", "message": "审核流程已启动", "data": {...}}
        # 不需要再记录系统消息
        
        # await log_system_message(
        #     db,
        #     session_id=request.job_id,
        #     content=f"审核已启动，共查询到 {result.data.get('subgraphs_count', 0)} 条子图数据",
        #     metadata={
        #         "action": "start_review",
        #         "data_summary": {
        #             "features": result.data.get('features_count', 0),
        #             "price_snapshots": result.data.get('price_snapshots_count', 0),
        #             "subgraphs": result.data.get('subgraphs_count', 0)
        #         }
        #     }
        # )
        
        # 6. 提交数据库事务（保存会话和消息）
        await db.commit()
        
        logger.info(f"✅ 审核启动成功: job_id={request.job_id}")
        
        return {
            "status": "ok",
            "message": result.message,
            "data": result.data
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 启动审核异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": f"服务器内部错误: {str(e)}"
            }
        )


@router.post("/{job_id}/modify")
async def modify_review(
    job_id: str,
    request: ModificationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    提交修改指令（集成意图识别）
    
    功能：
    1. 识别用户意图（数据修改、特征识别、价格计算、查询详情、普通聊天）
    2. 根据意图类型执行相应操作
    3. 保存到 Redis
    4. 推送确认消息到前端（如果需要确认）
    
    Args:
        job_id: 任务ID
        request: 修改请求
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        {
            "status": "ok",
            "intent": "DATA_MODIFICATION",  # 新增：意图类型
            "message": "修改已应用，等待确认",
            "requires_confirmation": true,  # 新增：是否需要确认
            "data": {
                "modification_id": "mod-uuid",
                "parsed_changes": [...],
                ...
            }
        }
    
    Raises:
        400: 参数错误或解析失败
        404: 审核会话不存在
        500: 服务器错误
    """
    try:
        logger.info(f"✏️ 处理修改: job_id={job_id}, user_id={current_user['user_id']}")
        logger.debug(f"修改内容: {request.modification_text}")
        
        # 1. 确保会话存在
        await ensure_session_exists(
            db,
            session_id=job_id,
            job_id=job_id,
            user_id=current_user["user_id"],
            metadata={"action": "modify"}
        )
        
        # 2. 记录用户消息
        await log_user_message(
            db,
            session_id=job_id,
            content=request.modification_text,
            metadata={"user_id": current_user["user_id"], "action": "modify"}
        )
        
        # 🆕 2.5. 提交事务（确保历史推断能查到当前消息）
        await db.commit()
        
        # 3. 创建 InteractionAgent
        agent = InteractionAgent()
        
        # 4. 处理修改（集成意图识别）
        result = await agent.handle_modification(
            job_id=job_id,
            modification_text=request.modification_text,
            user_id=current_user["user_id"],
            db_session=db
        )
        
        # 5. 检查结果
        if result.status == "error":
            if "未找到审核会话" in result.message or "审核会话已过期" in result.message:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "SESSION_NOT_FOUND",
                        "message": result.message
                    }
                )
            elif "处理修改失败" in result.message:
                # 真正的服务器内部错误（handler 抛出了未捕获的异常）
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error": "MODIFICATION_FAILED",
                        "message": result.message
                    }
                )
            else:
                # 业务级别的错误（如：缺少参数、解析失败、查询不到数据等）
                # 作为正常 200 响应返回，让前端展示友好提示
                logger.info(f"📋 业务提示: {result.message}")
                
                # 记录助手回复（业务提示也需要记录到聊天历史）
                await log_assistant_message(
                    db,
                    session_id=job_id,
                    content=result.message,
                    metadata={
                        "intent": result.data.get('intent') if result.data else None,
                        "action": "modify_response",
                        "is_business_error": True
                    }
                )
                await db.commit()
                
                return {
                    "status": "ok",
                    "intent": result.data.get("intent") if result.data else None,
                    "message": result.message,
                    "requires_confirmation": False,
                    "data": result.data or {}
                }
        
        # 6. 记录助手回复
        await log_assistant_message(
            db,
            session_id=job_id,
            content=result.message,
            metadata={
                "intent": result.data.get('intent') if result.data else None,
                "requires_confirmation": result.data.get('requires_confirmation') if result.data else False,
                "action": "modify_response"
            }
        )
        
        # 7. 提交数据库事务（保存消息）
        await db.commit()
        
        logger.info(f"✅ 修改处理成功: job_id={job_id}, intent={result.data.get('intent')}")
        
        # 8. 返回结果（包含 intent 和 requires_confirmation）
        return {
            "status": "ok",
            "intent": result.data.get("intent") if result.data else None,  # 新增
            "message": result.message,
            "requires_confirmation": result.data.get("requires_confirmation") if result.data else False,  # 新增
            "data": result.data
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 处理修改异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": f"服务器内部错误: {str(e)}"
            }
        )


@router.post("/{job_id}/confirm")
async def confirm_review(
    job_id: str,
    request: ConfirmRequest = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    确认修改并保存到数据库
    
    功能：
    1. 获取 Redis 中的临时数据
    2. 更新数据库（事务）
    3. 释放分布式锁
    4. 清理 Redis
    5. 推送完成消息
    
    Args:
        job_id: 任务ID
        request: 确认请求（可选）
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        {
            "status": "ok",
            "message": "审核已完成，数据已保存",
            "data": {
                "modifications_count": 3,
                "updated_tables": ["features", "subgraphs"]
            }
        }
    
    Raises:
        404: 审核会话不存在
        500: 服务器错误
    """
    try:
        logger.info(f"✅ 确认审核: job_id={job_id}, user_id={current_user['user_id']}")
        
        # 1. 确保会话存在
        logger.info(f"📝 开始确保会话存在...")
        await ensure_session_exists(
            db,
            session_id=job_id,
            job_id=job_id,
            user_id=current_user["user_id"],
            metadata={"action": "confirm"}
        )
        logger.info(f"✅ 会话检查完成")
        
        # 2. 创建 InteractionAgent
        agent = InteractionAgent()
        
        # 3. 确认修改
        result = await agent.confirm_changes(
            job_id=job_id,
            user_id=current_user["user_id"],
            db_session=db
        )
        
        # 检查结果
        if result.status == "error":
            # 🆕 版本冲突
            if "数据已被其他系统修改" in result.message:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "VERSION_CONFLICT",
                        "message": result.message,
                        "conflicts": result.data.get("conflicts", []),
                        "suggestion": "数据已被修改，请点击刷新重新加载数据"
                    }
                )
            elif "未找到审核会话" in result.message:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "SESSION_NOT_FOUND",
                        "message": result.message
                    }
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error": "CONFIRM_FAILED",
                        "message": result.message
                    }
                )
        
        # 🆕 不再记录重复的系统消息（前端已通过 WebSocket 收到 operation_completed）
        # 前端通过以下方式知道操作成功：
        # 1. HTTP 响应：{"status": "ok", "message": "..."}
        # 2. WebSocket 消息：{"type": "operation_completed", ...}
        # 不需要再记录一条重复的系统消息
        
        # await log_system_message(
        #     db,
        #     session_id=job_id,
        #     content=f"修改已确认并保存到数据库，共 {result.data.get('modifications_count', 0)} 处修改",
        #     metadata={
        #         "action": "confirm",
        #         "modifications_count": result.data.get('modifications_count', 0)
        #     }
        # )
        
        # 提交数据库事务（保存消息）
        await db.commit()
        
        logger.info(f"✅ 审核确认成功: job_id={job_id}, modifications={result.data.get('modifications_count')}")
        
        return {
            "status": "ok",
            "message": result.message,
            "data": result.data
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 确认审核异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": f"服务器内部错误: {str(e)}"
            }
        )




@router.post("/{job_id}/refresh")
async def refresh_review_data(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    刷新审核数据
    
    功能：
    1. 重新从数据库查询 4 个表的数据
    2. 更新 Redis 中的数据
    3. 推送最新数据到前端
    4. 保持锁和状态不变
    
    适用场景：
    - 执行了"重新识别特征"或"重新计算"后，需要刷新数据
    - 数据库数据已更新，需要同步到 Redis
    
    Args:
        job_id: 任务ID
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        {
            "status": "ok",
            "message": "数据已刷新",
            "data": {
                "job_id": "xxx",
                "refresh_count": 1,
                "features_count": 10,
                "subgraphs_count": 5,
                ...
            }
        }
    
    Raises:
        404: 审核会话不存在
        500: 服务器错误
    """
    try:
        logger.info(f"🔄 刷新审核数据: job_id={job_id}, user_id={current_user['user_id']}")
        
        # 创建 InteractionAgent
        agent = InteractionAgent()
        
        # 刷新数据
        result = await agent.refresh_data(
            job_id=job_id,
            db_session=db
        )
        
        # 检查结果
        if result.status == "error":
            if "正在被其他用户审核" in result.message:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "REVIEW_LOCKED",
                        "message": result.message
                    }
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error": "REFRESH_FAILED",
                        "message": result.message
                    }
                )
        
        # 提交数据库事务（保存持久化的消息）
        await db.commit()
        
        logger.info(f"✅ 数据刷新成功: job_id={job_id}")
        
        return {
            "status": "ok",
            "message": result.message,
            "data": result.data
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 刷新数据异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": f"服务器内部错误: {str(e)}"
            }
        )


@router.get("/{job_id}/status")
async def get_review_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    查询审核状态
    
    功能：
    1. 从 Redis 获取审核状态
    2. 返回当前状态和修改历史
    
    Args:
        job_id: 任务ID
        current_user: 当前用户
    
    Returns:
        {
            "status": "ok",
            "data": {
                "job_id": "xxx",
                "review_status": "reviewing",
                "is_locked": true,
                "modifications_count": 2,
                "created_at": "2026-01-15T10:00:00",
                "last_modified_at": "2026-01-15T10:05:00"
            }
        }
    
    Raises:
        404: 审核会话不存在
        500: 服务器错误
    """
    try:
        logger.info(f"📊 查询审核状态: job_id={job_id}, user_id={current_user['user_id']}")
        
        # 创建 InteractionAgent
        agent = InteractionAgent()
        
        # 获取状态
        state = await agent.get_review_state(job_id)
        
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "SESSION_NOT_FOUND",
                    "message": "未找到审核会话"
                }
            )
        
        # 检查锁状态
        is_locked = await agent.check_lock(job_id)
        
        logger.info(f"✅ 状态查询成功: job_id={job_id}, status={state.get('status')}")
        
        return {
            "status": "ok",
            "data": {
                "job_id": job_id,
                "review_status": state.get("status"),
                "is_locked": is_locked,
                "modifications_count": len(state.get("modifications", [])),
                "created_at": state.get("created_at"),
                "last_modified_at": state.get("last_modified_at")
            }
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 查询状态异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": f"服务器内部错误: {str(e)}"
            }
        )
