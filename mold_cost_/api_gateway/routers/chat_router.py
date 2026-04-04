"""审核聊天路由兼容层。"""

from __future__ import annotations

import asyncio
import json
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from refactor_bootstrap import ensure_src_path
from shared.database import get_db
from shared.unified_logging import get_logger
from ..auth import get_current_user
from api_gateway.utils.chat_logger import ensure_session_exists, log_assistant_message, log_user_message

ensure_src_path()

from mold_cost.application.use_cases import ReviewChatUseCase  # noqa: E402

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class Message(BaseModel):
    """聊天消息。"""

    role: str = Field(..., description="角色")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """聊天请求。"""

    job_id: str = Field(..., description="任务 ID")
    message: str = Field(..., description="用户消息", min_length=1)
    history: Optional[list[Message]] = Field(default=[], description="历史消息")
    stream: bool = Field(default=True, description="是否启用流式输出")


@router.post("/completions")
async def chat_completions(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """SSE 审核聊天接口。"""
    try:
        await ensure_session_exists(
            db,
            session_id=request.job_id,
            job_id=request.job_id,
            user_id=current_user["user_id"],
            metadata={"action": "chat"},
        )

        await log_user_message(
            db,
            session_id=request.job_id,
            content=request.message,
            metadata={"user_id": current_user["user_id"], "stream": request.stream},
        )
        await db.commit()

        use_case = ReviewChatUseCase()
        state = await use_case.get_state(request.job_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "SESSION_NOT_FOUND", "message": "未找到审核会话，请先启动审核"},
            )

        current_data = state.get("data") or state.get("raw_data")
        history = [message.model_dump() for message in request.history]

        if request.stream:
            async def event_stream():
                """流式输出聊天内容。"""
                full_response = ""
                message_id = str(uuid4())
                yield f"data: {json.dumps({'type': 'start', 'message_id': message_id})}\n\n"

                try:
                    async for chunk in use_case.chat_stream(
                        job_id=request.job_id,
                        message=request.message,
                        history=history,
                        current_data=current_data,
                    ):
                        yield f"data: {json.dumps({'type': 'content', 'delta': chunk})}\n\n"
                        full_response += chunk
                        await asyncio.sleep(0.01)

                    yield f"data: {json.dumps({'type': 'done', 'finish_reason': 'stop'})}\n\n"

                    async for db_stream in get_db():
                        await log_assistant_message(
                            db_stream,
                            session_id=request.job_id,
                            content=full_response,
                            metadata={"message_id": message_id, "stream": True},
                        )
                        await db_stream.commit()
                        break
                except Exception as exc:
                    logger.error("聊天流输出异常: %s", exc, exc_info=True)
                    yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        response = await use_case.chat(
            job_id=request.job_id,
            message=request.message,
            history=history,
            current_data=current_data,
        )

        await log_assistant_message(
            db,
            session_id=request.job_id,
            content=response,
            metadata={"stream": False},
        )
        await db.commit()

        return {"status": "ok", "data": {"message": response, "finish_reason": "stop"}}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("聊天接口异常: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": f"服务端内部错误: {str(exc)}"},
        )
