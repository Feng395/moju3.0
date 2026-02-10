"""FastAPI依赖注入"""
from fastapi import Header, HTTPException, Depends
from typing import Optional
from api_gateway.utils.account.jwt_helper import get_current_user_from_token


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    获取当前用户（依赖注入）
    
    Args:
        authorization: Authorization头，格式为 "Bearer {token}"
        
    Returns:
        当前用户信息字典
        
    Raises:
        HTTPException: 如果token无效或缺失
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少认证token")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token格式错误，应为: Bearer {token}")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user_from_token(token)
    
    if user is None:
        raise HTTPException(status_code=401, detail="Token无效或已过期")
    
    return user


async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    获取当前激活用户（依赖注入）
    
    Args:
        current_user: 当前用户信息
        
    Returns:
        当前激活用户信息字典
        
    Raises:
        HTTPException: 如果用户未激活
    """
    # 可以添加额外的检查，如用户是否被禁用
    # if not current_user.get("is_active"):
    #     raise HTTPException(status_code=403, detail="用户已被禁用")
    
    return current_user
