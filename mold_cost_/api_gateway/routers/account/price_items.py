"""价格项路由"""
from shared.unified_logging import get_logger
from fastapi import APIRouter, Request, HTTPException
from api_gateway.models.account.price_item_models import (
    CreatePriceItemRequest,
    UpdatePriceItemRequest,
    PriceItemResponse,
    PriceItemListResponse
)
from api_gateway.services.account.price_item_service import price_item_service
import logging

logger = get_logger(__name__)
router = APIRouter()


@router.post("", status_code=201, tags=["价格项"])
async def create_item(request: CreatePriceItemRequest):
    """
    创建价格项
    
    请求体:
    {
        "id": "P001",
        "version_id": "v1.0",
        "category": "wire",
        "sub_category": "线割加工",
        "price": "100.00",
        "unit": "元/小时",
        "work_hours": "1.5",
        "min_num": "50",
        "add_price": "10.00",
        "weight_num": "1.2",
        "note": "备注信息",
        "instruction": "计算说明",
        "is_active": true,
        "created_by": "admin"
    }
    """
    try:
        item_data = request.dict()
        success, message, result = await price_item_service.create_item(item_data)
        
        if success:
            return {
                'success': True,
                'message': message,
                'data': result
            }
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建价格项接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.get("/{item_id}", tags=["价格项"])
async def get_item(item_id: str):
    """获取单个价格项详情"""
    try:
        success, message, result = await price_item_service.get_item_by_id(item_id)
        
        if success:
            return {
                'success': True,
                'message': message,
                'data': result
            }
        else:
            raise HTTPException(status_code=404, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取价格项接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.get("", tags=["价格项"])
async def get_items(
    page: int = 1,
    page_size: int = 20,
    version_id: str = None,
    category: str = None,
    sub_category: str = None,
    is_active: bool = None
):
    """
    获取价格项列表（支持分页和筛选）
    
    查询参数:
    - page: 页码（默认1）
    - page_size: 每页数量（默认20）
    - version_id: 版本号筛选
    - category: 类别筛选（wire/special/base）
    - sub_category: 子类筛选（模糊搜索）
    - is_active: 是否激活筛选
    """
    try:
        # 构建筛选参数
        filters = {}
        if version_id:
            filters['version_id'] = version_id
        if category:
            filters['category'] = category
        if sub_category:
            filters['sub_category'] = sub_category
        if is_active is not None:
            filters['is_active'] = is_active
        
        success, message, result = await price_item_service.get_items(filters, page, page_size)
        
        if success:
            return {
                'success': True,
                'message': message,
                'data': result
            }
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取价格项列表接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.put("/{item_id}", tags=["价格项"])
async def update_item(item_id: str, request: UpdatePriceItemRequest):
    """
    更新价格项
    
    请求体（所有字段可选）:
    {
        "version_id": "v1.1",
        "category": "special",
        "sub_category": "特殊加工",
        "price": "150.00",
        "unit": "元/件",
        "work_hours": "2.0",
        "min_num": "100",
        "add_price": "20.00",
        "weight_num": "1.5",
        "note": "更新后的备注",
        "instruction": "更新后的说明",
        "is_active": false,
        "created_by": "admin"
    }
    """
    try:
        update_data = request.dict(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(status_code=400, detail="请求体不能为空")
        
        success, message, result = await price_item_service.update_item(item_id, update_data)
        
        if success:
            return {
                'success': True,
                'message': message,
                'data': result
            }
        else:
            status_code = 404 if '不存在' in message else 400
            raise HTTPException(status_code=status_code, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新价格项接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.delete("/{item_id}", tags=["价格项"])
async def delete_item(item_id: str):
    """删除价格项（硬删除）"""
    try:
        success, message, _ = await price_item_service.delete_item(item_id)
        
        if success:
            return {
                'success': True,
                'message': message
            }
        else:
            raise HTTPException(status_code=404, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除价格项接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.put("/{item_id}/soft-delete", tags=["价格项"])
@router.patch("/{item_id}/soft-delete", tags=["价格项"])
async def soft_delete_item(item_id: str):
    """
    软删除价格项（将is_active设为false）
    
    使用PUT或PATCH方法访问: /api/price-items/{item_id}/soft-delete
    """
    try:
        success, message, result = await price_item_service.soft_delete_item(item_id)
        
        if success:
            return {
                'success': True,
                'message': message,
                'data': result
            }
        else:
            raise HTTPException(status_code=404, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"软删除价格项接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.post("/batch-delete", tags=["价格项"])
async def batch_delete_items(request: dict):
    """
    批量删除价格项（硬删除）
    
    请求体:
    {
        "ids": ["P001", "P002", "P003"]
    }
    """
    try:
        item_ids = request.get('ids', [])
        
        if not item_ids or not isinstance(item_ids, list) or len(item_ids) == 0:
            raise HTTPException(status_code=400, detail="ids必须是非空数组")
        
        success, message, result = await price_item_service.batch_delete_items(item_ids)
        
        if success:
            return {
                'success': True,
                'message': message,
                'data': result
            }
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量删除价格项接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.post("/batch-soft-delete", tags=["价格项"])
async def batch_soft_delete_items(request: dict):
    """
    批量软删除价格项（将is_active设为false）
    
    请求体:
    {
        "ids": ["P001", "P002", "P003"]
    }
    """
    try:
        item_ids = request.get('ids', [])
        
        if not item_ids or not isinstance(item_ids, list) or len(item_ids) == 0:
            raise HTTPException(status_code=400, detail="ids必须是非空数组")
        
        success, message, result = await price_item_service.batch_soft_delete_items(item_ids)
        
        if success:
            return {
                'success': True,
                'message': message,
                'data': result
            }
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量软删除价格项接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.get("/by-version-category", tags=["价格项"])
async def get_items_by_version_and_category(
    version_id: str,
    category: str,
    active_only: bool = True
):
    """
    根据版本和类别获取价格项
    
    查询参数:
    - version_id: 版本号（必填）
    - category: 类别（必填）
    - active_only: 是否只返回激活的价格项（默认true）
    """
    try:
        if not version_id or not category:
            raise HTTPException(status_code=400, detail="缺少必填参数: version_id 和 category")
        
        success, message, result = await price_item_service.get_items_by_version_and_category(
            version_id, category, active_only
        )
        
        if success:
            return {
                'success': True,
                'message': message,
                'data': result
            }
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取价格项接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")
