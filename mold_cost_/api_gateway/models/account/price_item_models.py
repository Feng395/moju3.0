"""价格项相关的Pydantic模型"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class PriceItemBase(BaseModel):
    """价格项基础模型"""
    id: str = Field(..., max_length=50, description="价格项ID")
    version_id: Optional[str] = Field(None, max_length=20, description="版本号")
    category: Optional[str] = Field(None, max_length=50, description="类别")
    sub_category: Optional[str] = Field(None, max_length=100, description="子类别")
    price: Optional[Decimal] = Field(None, description="价格")
    unit: Optional[str] = Field(None, max_length=20, description="单位")
    work_hours: Optional[Decimal] = Field(None, description="工时")
    min_num: Optional[Decimal] = Field(None, description="最小数量")
    add_price: Optional[Decimal] = Field(None, description="附加价格")
    weight_num: Optional[Decimal] = Field(None, description="重量系数")
    note: Optional[str] = Field(None, description="备注")
    instruction: Optional[str] = Field(None, description="说明")
    is_active: bool = Field(default=True, description="是否激活")
    created_by: Optional[str] = Field(None, max_length=50, description="创建人")


class CreatePriceItemRequest(PriceItemBase):
    """创建价格项请求"""
    pass


class UpdatePriceItemRequest(BaseModel):
    """更新价格项请求"""
    version_id: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    price: Optional[Decimal] = None
    unit: Optional[str] = None
    work_hours: Optional[Decimal] = None
    min_num: Optional[Decimal] = None
    add_price: Optional[Decimal] = None
    weight_num: Optional[Decimal] = None
    note: Optional[str] = None
    instruction: Optional[str] = None
    is_active: Optional[bool] = None
    created_by: Optional[str] = None


class PriceItemResponse(BaseModel):
    """价格项响应"""
    id: str
    version_id: Optional[str]
    category: Optional[str]
    sub_category: Optional[str]
    price: Optional[Decimal]
    unit: Optional[str]
    work_hours: Optional[Decimal]
    min_num: Optional[Decimal]
    add_price: Optional[Decimal]
    weight_num: Optional[Decimal]
    note: Optional[str]
    instruction: Optional[str]
    is_active: bool
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime


class PriceItemListResponse(BaseModel):
    """价格项列表响应"""
    success: bool
    message: str
    data: dict  # {total, page, page_size, total_pages, data: List[PriceItemResponse]}
