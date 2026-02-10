"""工艺规则相关的Pydantic模型"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ProcessRuleBase(BaseModel):
    """工艺规则基础模型"""
    id: str = Field(..., max_length=50, description="规则ID")
    version_id: str = Field(default="v1.0", max_length=20, description="版本号")
    feature_type: str = Field(..., max_length=50, description="特征类型")
    name: str = Field(..., max_length=100, description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    priority: int = Field(default=1, description="优先级")
    is_active: bool = Field(default=True, description="是否激活")
    conditions: str = Field(..., max_length=255, description="规则条件")
    output_params: str = Field(..., max_length=255, description="输出参数")


class CreateProcessRuleRequest(ProcessRuleBase):
    """创建工艺规则请求"""
    pass


class UpdateProcessRuleRequest(BaseModel):
    """更新工艺规则请求"""
    version_id: Optional[str] = Field(None, max_length=20)
    feature_type: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    conditions: Optional[str] = Field(None, max_length=255)
    output_params: Optional[str] = Field(None, max_length=255)


class ProcessRuleResponse(BaseModel):
    """工艺规则响应"""
    id: str
    version_id: str
    feature_type: str
    name: str
    description: Optional[str]
    priority: int
    is_active: bool
    conditions: str
    output_params: str
    created_at: datetime


class ProcessRuleListResponse(BaseModel):
    """工艺规则列表响应"""
    success: bool
    message: str
    data: dict  # {total, page, page_size, total_pages, data: List[ProcessRuleResponse]}


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    ids: List[str] = Field(..., min_items=1, description="要删除的ID列表")
