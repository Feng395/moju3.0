"""聊天会话相关的Pydantic模型"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class UpdateSessionNameRequest(BaseModel):
    """更新会话名称请求"""
    name: str = Field(..., max_length=200, description="会话名称")


class UpdateSessionNameByJobRequest(BaseModel):
    """根据job_id更新会话名称请求"""
    job_id: str = Field(..., description="任务ID")
    name: str = Field(..., max_length=200, description="会话名称")


class DeleteSessionByJobRequest(BaseModel):
    """根据job_id删除会话请求"""
    job_id: str = Field(..., description="任务ID")


class BatchDeleteSessionsRequest(BaseModel):
    """批量删除会话请求"""
    job_ids: List[str] = Field(..., min_items=1, max_items=100, description="任务ID列表")


class ChatSessionResponse(BaseModel):
    """聊天会话响应"""
    session_id: str
    job_id: str
    user_id: str
    name: Optional[str]
    status: str
    metadata: Optional[dict]
    created_at: datetime
    updated_at: datetime


class ChatSessionListResponse(BaseModel):
    """聊天会话列表响应"""
    success: bool
    message: str
    data: dict  # {sessions: List[ChatSessionResponse], total, limit, offset}
