"""工艺规则路由"""
from fastapi import APIRouter, Request, HTTPException
from api_gateway.models.account.process_rule_models import (
    CreateProcessRuleRequest,
    UpdateProcessRuleRequest,
    ProcessRuleResponse,
    ProcessRuleListResponse,
    BatchDeleteRequest
)
from api_gateway.services.account.process_rule_service import process_rule_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", status_code=201, tags=["工艺规则"])
async def create_rule(request: CreateProcessRuleRequest):
    """
    创建工艺规则
    
    请求体（简化版）:
    {
        "id": "R001",
        "name": "线割规则1",
        "feature_type": "wire",
        "description": "中丝割一修一"
    }
    
    或完整版:
    {
        "id": "R001",
        "version_id": "v1.0",
        "feature_type": "WIRE",
        "name": "线割规则1",
        "description": "规则描述",
        "priority": 10,
        "is_active": true,
        "conditions": "条件字符串",
        "output_params": "输出参数字符串"
    }
    
    支持的description规则:
    - 慢丝割一修一 -> slow_and_one
    - 慢丝割一刀 -> slow_cut
    - 快丝割一刀 -> fast_cut
    - 中丝割一修一 -> middle_and_one
    """
    try:
        # 验证字段长度
        if len(request.conditions) > 255:
            raise HTTPException(status_code=400, detail="conditions字段长度不能超过255")
        
        if len(request.output_params) > 255:
            raise HTTPException(status_code=400, detail="output_params字段长度不能超过255")
        
        rule_data = request.dict()
        success, message, result = await process_rule_service.create_rule(rule_data)
        
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
        logger.error(f"创建规则接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.get("/{rule_id}", tags=["工艺规则"])
async def get_rule(rule_id: str):
    """获取单个规则详情"""
    try:
        success, message, result = await process_rule_service.get_rule_by_id(rule_id)
        
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
        logger.error(f"获取规则接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.get("", tags=["工艺规则"])
async def get_rules(
    page: int = 1,
    page_size: int = 20,
    version_id: str = None,
    feature_type: str = None,
    is_active: bool = None,
    name: str = None
):
    """
    获取规则列表（支持分页和筛选）
    
    查询参数:
    - page: 页码（默认1）
    - page_size: 每页数量（默认20）
    - version_id: 版本号筛选
    - feature_type: 特征类型筛选
    - is_active: 是否激活筛选
    - name: 名称模糊搜索
    """
    try:
        # 构建筛选参数
        filters = {}
        if version_id:
            filters['version_id'] = version_id
        if feature_type:
            filters['feature_type'] = feature_type
        if is_active is not None:
            filters['is_active'] = is_active
        if name:
            filters['name'] = name
        
        success, message, result = await process_rule_service.get_rules(filters, page, page_size)
        
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
        logger.error(f"获取规则列表接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.put("/{rule_id}", tags=["工艺规则"])
async def update_rule(rule_id: str, request: UpdateProcessRuleRequest):
    """
    更新规则
    
    请求体（所有字段可选）:
    {
        "version_id": "v1.1",
        "feature_type": "NC",
        "name": "更新后的名称",
        "description": "更新后的描述",
        "priority": 20,
        "is_active": false,
        "conditions": "新条件",
        "output_params": "新输出参数"
    }
    """
    try:
        update_data = request.dict(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(status_code=400, detail="请求体不能为空")
        
        # 验证字段长度
        if 'conditions' in update_data and len(update_data['conditions']) > 255:
            raise HTTPException(status_code=400, detail="conditions字段长度不能超过255")
        
        if 'output_params' in update_data and len(update_data['output_params']) > 255:
            raise HTTPException(status_code=400, detail="output_params字段长度不能超过255")
        
        success, message, result = await process_rule_service.update_rule(rule_id, update_data)
        
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
        logger.error(f"更新规则接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.delete("/{rule_id}", tags=["工艺规则"])
async def delete_rule(rule_id: str):
    """删除规则（硬删除）"""
    try:
        success, message, _ = await process_rule_service.delete_rule(rule_id)
        
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
        logger.error(f"删除规则接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.put("/{rule_id}/soft-delete", tags=["工艺规则"])
@router.patch("/{rule_id}/soft-delete", tags=["工艺规则"])
async def soft_delete_rule(rule_id: str):
    """
    软删除规则（将is_active设为false）
    
    使用PUT或PATCH方法访问: /api/process-rules/{rule_id}/soft-delete
    """
    try:
        success, message, result = await process_rule_service.soft_delete_rule(rule_id)
        
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
        logger.error(f"软删除规则接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.post("/batch-delete", tags=["工艺规则"])
async def batch_delete_rules(request: BatchDeleteRequest):
    """
    批量删除规则（硬删除）
    
    请求体:
    {
        "ids": ["R001", "R002", "R003"]
    }
    """
    try:
        if not request.ids or len(request.ids) == 0:
            raise HTTPException(status_code=400, detail="ids必须是非空数组")
        
        success, message, result = await process_rule_service.batch_delete_rules(request.ids)
        
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
        logger.error(f"批量删除规则接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.post("/batch-soft-delete", tags=["工艺规则"])
async def batch_soft_delete_rules(request: BatchDeleteRequest):
    """
    批量软删除规则（将is_active设为false）
    
    请求体:
    {
        "ids": ["R001", "R002", "R003"]
    }
    """
    try:
        if not request.ids or len(request.ids) == 0:
            raise HTTPException(status_code=400, detail="ids必须是非空数组")
        
        success, message, result = await process_rule_service.batch_soft_delete_rules(request.ids)
        
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
        logger.error(f"批量软删除规则接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.get("/by-version-type", tags=["工艺规则"])
async def get_rules_by_version_and_type(
    version_id: str,
    feature_type: str,
    active_only: bool = True
):
    """
    根据版本和特征类型获取规则
    
    查询参数:
    - version_id: 版本号（必填）
    - feature_type: 特征类型（必填）
    - active_only: 是否只返回激活的规则（默认true）
    """
    try:
        if not version_id or not feature_type:
            raise HTTPException(status_code=400, detail="缺少必填参数: version_id 和 feature_type")
        
        success, message, result = await process_rule_service.get_rules_by_version_and_type(
            version_id, feature_type, active_only
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
        logger.error(f"获取规则接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")
