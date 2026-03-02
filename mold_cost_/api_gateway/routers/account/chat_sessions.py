"""聊天会话路由"""
from shared.unified_logging import get_logger
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from api_gateway.models.account.chat_session_models import (
    UpdateSessionNameRequest,
    UpdateSessionNameByJobRequest,
    DeleteSessionByJobRequest,
    BatchDeleteSessionsRequest,
    ChatSessionResponse,
    ChatSessionListResponse
)
from api_gateway.services.account.chat_session_service import chat_session_service
from api_gateway.dependencies import get_current_user

logger = get_logger(__name__)
router = APIRouter()


@router.put("/update-name", tags=["聊天会话"])
async def update_session_name_by_job(
    request: UpdateSessionNameByJobRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    根据任务ID更新会话名称
    
    **请求头**:
    - Authorization: Bearer {token}
    
    **请求体**:
    - job_id: 任务ID
    - name: 新的会话名称
    
    **响应**:
    ```json
    {
        "success": true,
        "message": "会话名称更新成功",
        "data": {
            "session_id": "xxx",
            "job_id": "xxx",
            "user_id": "xxx",
            "name": "新的会话名称",
            "status": "active",
            "metadata": {},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
    }
    ```
    """
    try:
        user_id = current_user.get('user_id')
        
        # 更新会话名称
        success, message, session = await chat_session_service.update_session_name_by_job_id(
            job_id=request.job_id,
            name=request.name,
            user_id=user_id
        )
        
        if success:
            return {
                "success": True,
                "message": message,
                "data": session
            }
        else:
            status_code = 404 if '不存在' in message or '无权访问' in message else 400
            return JSONResponse(
                status_code=status_code,
                content={
                    "success": False,
                    "message": message
                }
            )
            
    except Exception as e:
        logger.error(f"根据job_id更新会话名称接口异常: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "服务器内部错误"
            }
        )


@router.put("/{session_id}/name", tags=["聊天会话"])
async def update_session_name(
    session_id: str,
    request: UpdateSessionNameRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    更新会话名称
    
    **请求头**:
    - Authorization: Bearer {token}
    
    **路径参数**:
    - session_id: 会话ID
    
    **请求体**:
    - name: 新的会话名称
    
    **响应**:
    ```json
    {
        "success": true,
        "message": "会话名称更新成功",
        "data": {
            "session_id": "xxx",
            "job_id": "xxx",
            "user_id": "xxx",
            "name": "新的会话名称",
            "status": "active",
            "metadata": {},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
    }
    ```
    """
    try:
        user_id = current_user.get('user_id')
        
        # 更新会话名称
        success, message, session = await chat_session_service.update_session_name(
            session_id=session_id,
            name=request.name,
            user_id=user_id
        )
        
        if success:
            return {
                "success": True,
                "message": message,
                "data": session
            }
        else:
            status_code = 404 if '不存在' in message else \
                         403 if '无权' in message else \
                         400
            return JSONResponse(
                status_code=status_code,
                content={
                    "success": False,
                    "message": message
                }
            )
            
    except Exception as e:
        logger.error(f"更新会话名称接口异常: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "服务器内部错误"
            }
        )


@router.get("/{session_id}", tags=["聊天会话"])
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    获取会话详情
    
    **请求头**:
    - Authorization: Bearer {token}
    
    **路径参数**:
    - session_id: 会话ID
    
    **响应**:
    ```json
    {
        "success": true,
        "message": "获取成功",
        "data": {
            "session_id": "xxx",
            "job_id": "xxx",
            "user_id": "xxx",
            "name": "会话名称",
            "status": "active",
            "metadata": {},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
    }
    ```
    """
    try:
        user_id = current_user.get('user_id')
        
        # 获取会话信息
        session = await chat_session_service.get_session_by_id(session_id)
        
        if not session:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "会话不存在"
                }
            )
        
        # 验证权限
        if session['user_id'] != user_id:
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "message": "无权访问此会话"
                }
            )
        
        return {
            "success": True,
            "message": "获取成功",
            "data": session
        }
        
    except Exception as e:
        logger.error(f"获取会话详情接口异常: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "服务器内部错误"
            }
        )


@router.get("/", tags=["聊天会话"])
async def get_user_sessions(
    status: Optional[str] = Query(None, description="会话状态过滤"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: dict = Depends(get_current_user)
):
    """
    获取当前用户的会话列表
    
    **请求头**:
    - Authorization: Bearer {token}
    
    **查询参数**:
    - status: 会话状态过滤（可选）
    - limit: 返回数量限制（默认50，最大100）
    - offset: 偏移量（默认0）
    
    **响应**:
    ```json
    {
        "success": true,
        "message": "获取成功",
        "data": {
            "sessions": [...],
            "total": 100,
            "limit": 50,
            "offset": 0
        }
    }
    ```
    """
    try:
        user_id = current_user.get('user_id')
        
        # 获取会话列表
        sessions, total = await chat_session_service.get_user_sessions(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "message": "获取成功",
            "data": {
                "sessions": sessions,
                "total": total,
                "limit": limit,
                "offset": offset
            }
        }
        
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "参数格式错误"
            }
        )
    except Exception as e:
        logger.error(f"获取会话列表接口异常: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "服务器内部错误"
            }
        )


@router.delete("/delete-by-job", tags=["聊天会话"])
async def delete_session_by_job(
    request: DeleteSessionByJobRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    根据任务ID删除会话及所有相关数据（级联删除）
    
    **请求头**:
    - Authorization: Bearer {token}
    
    **请求体**:
    - job_id: 任务ID
    
    **响应**:
    ```json
    {
        "success": true,
        "message": "会话删除成功，共删除 X 条记录: ...",
        "data": {
            "job_id": "xxx",
            "deleted_tables": ["chat_sessions", "jobs", "subgraphs", ...],
            "total_deleted": 123
        }
    }
    ```
    """
    try:
        user_id = current_user.get('user_id')
        
        # 删除会话及相关数据
        success, message = await chat_session_service.delete_session_by_job_id(
            job_id=request.job_id,
            user_id=user_id
        )
        
        if success:
            # 解析删除统计信息
            deleted_tables = []
            total_deleted = 0
            
            if "共删除" in message and "条记录:" in message:
                parts = message.split("条记录:")
                if len(parts) > 1:
                    total_part = parts[0].split("共删除")[-1].strip()
                    try:
                        total_deleted = int(total_part)
                    except:
                        pass
                    
                    # 提取表名
                    tables_part = parts[1].strip()
                    import re
                    table_matches = re.findall(r'(\w+)\(\d+条\)', tables_part)
                    deleted_tables = table_matches
            
            return {
                "success": True,
                "message": message,
                "data": {
                    "job_id": request.job_id,
                    "deleted_tables": deleted_tables,
                    "total_deleted": total_deleted
                }
            }
        else:
            status_code = 404 if '不存在' in message or '无权访问' in message else 400
            return JSONResponse(
                status_code=status_code,
                content={
                    "success": False,
                    "message": message
                }
            )
            
    except Exception as e:
        logger.error(f"删除会话接口异常: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "服务器内部错误"
            }
        )


@router.post("/batch-delete-by-job", tags=["聊天会话"])
async def batch_delete_sessions_by_job(
    request: BatchDeleteSessionsRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    批量删除多个任务的会话及相关数据（异步处理）
    
    **请求头**:
    - Authorization: Bearer {token}
    
    **请求体**:
    - job_ids: 任务ID列表（最多100个）
    
    **响应**:
    ```json
    {
        "success": true,
        "message": "批量删除完成: 总数=10, 成功=8, 失败=2",
        "data": {
            "total": 10,
            "success_count": 8,
            "failed_count": 2,
            "total_deleted": 1234,
            "elapsed_seconds": 5.678,
            "results": [
                {
                    "job_id": "xxx",
                    "success": true,
                    "message": "删除成功",
                    "deleted_count": 123
                },
                {
                    "job_id": "yyy",
                    "success": false,
                    "message": "会话不存在或无权访问",
                    "deleted_count": 0
                }
            ]
        }
    }
    ```
    """
    try:
        user_id = current_user.get('user_id')
        
        # 验证输入
        if not request.job_ids:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "job_ids不能为空"
                }
            )
        
        # 过滤空字符串
        job_ids = [jid.strip() for jid in request.job_ids if jid and jid.strip()]
        
        if not job_ids:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "没有有效的任务ID"
                }
            )
        
        # 执行批量删除
        result = await chat_session_service.delete_sessions_by_job_ids_batch(
            job_ids=job_ids,
            user_id=user_id
        )
        
        # 构建响应消息
        message = f"批量删除完成: 总数={result['total']}, 成功={result['success_count']}, 失败={result['failed_count']}"
        
        return {
            "success": True,
            "message": message,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"批量删除会话接口异常: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "服务器内部错误"
            }
        )


@router.delete("/{session_id}", tags=["聊天会话"])
async def delete_session_by_id(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    根据会话ID删除会话及所有相关数据（级联删除）
    
    **请求头**:
    - Authorization: Bearer {token}
    
    **路径参数**:
    - session_id: 会话ID
    
    **响应**:
    ```json
    {
        "success": true,
        "message": "会话删除成功，共删除 X 条记录: ...",
        "data": {
            "session_id": "xxx",
            "deleted_tables": ["chat_sessions", "jobs", "subgraphs", ...],
            "total_deleted": 123
        }
    }
    ```
    """
    try:
        user_id = current_user.get('user_id')
        
        # 删除会话及相关数据
        success, message = await chat_session_service.delete_session_by_id(
            session_id=session_id,
            user_id=user_id
        )
        
        if success:
            # 解析删除统计信息
            deleted_tables = []
            total_deleted = 0
            
            if "共删除" in message and "条记录:" in message:
                parts = message.split("条记录:")
                if len(parts) > 1:
                    total_part = parts[0].split("共删除")[-1].strip()
                    try:
                        total_deleted = int(total_part)
                    except:
                        pass
                    
                    # 提取表名
                    tables_part = parts[1].strip()
                    import re
                    table_matches = re.findall(r'(\w+)\(\d+条\)', tables_part)
                    deleted_tables = table_matches
            
            return {
                "success": True,
                "message": message,
                "data": {
                    "session_id": session_id,
                    "deleted_tables": deleted_tables,
                    "total_deleted": total_deleted
                }
            }
        else:
            status_code = 404 if '不存在' in message else \
                         403 if '无权' in message else 400
            return JSONResponse(
                status_code=status_code,
                content={
                    "success": False,
                    "message": message
                }
            )
            
    except Exception as e:
        logger.error(f"删除会话接口异常: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "服务器内部错误"
            }
        )
