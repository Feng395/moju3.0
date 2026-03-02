"""认证路由"""
from shared.unified_logging import get_logger
from fastapi import APIRouter, Request, Depends, HTTPException
from api_gateway.models.account.auth_models import (
    LoginRequest, LoginResponse,
    VerifyTokenRequest, VerifyTokenResponse,
    ChangePasswordRequest, ChangePasswordResponse
)
from api_gateway.services.account.auth_service import auth_service
from api_gateway.utils.account.jwt_helper import create_access_token, verify_token
from api_gateway.dependencies import get_current_user
import logging

logger = get_logger(__name__)
router = APIRouter()


def get_client_ip(request: Request) -> str:
    """
    获取客户端IP地址
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        客户端IP地址
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/api/login", response_model=LoginResponse, tags=["认证"])
async def login(login_request: LoginRequest, request: Request):
    """
    用户登录接口
    
    **请求体**:
    - username: 用户名
    - password: 密码
    
    **响应**:
    - success: 是否成功
    - message: 消息
    - token: JWT令牌（成功时返回）
    - user_info: 用户信息（成功时返回）
    
    **示例**:
    ```json
    {
        "username": "admin",
        "password": "admin123"
    }
    ```
    
    **注意**: 
    - 无论成功或失败，都返回200状态码
    - 通过 success 字段判断是否成功
    """
    client_ip = get_client_ip(request)
    
    # 用户认证
    success, message, user_info = await auth_service.authenticate_user(
        login_request.username, login_request.password, client_ip
    )
    
    if success:
        # 创建JWT令牌
        token_data = {
            "sub": user_info["username"],
            "user_id": user_info["user_id"],
            "role": user_info["role"],
            "email": user_info.get("email"),
            "real_name": user_info.get("real_name")
        }
        access_token = create_access_token(token_data)
        
        logger.info(f"用户 {login_request.username} 登录成功，IP: {client_ip}")
        return LoginResponse(
            success=True,
            message=message,
            token=access_token,
            user_info=user_info
        )
    else:
        logger.warning(f"用户 {login_request.username} 登录失败: {message}，IP: {client_ip}")
        # 注意：登录失败也返回200状态码，通过success字段判断
        return LoginResponse(success=False, message=message)


@router.post("/api/verify-token", response_model=VerifyTokenResponse, tags=["认证"], status_code=200)
async def verify_token_endpoint(verify_request: VerifyTokenRequest):
    """
    验证JWT令牌
    
    **请求体**:
    - token: JWT令牌
    
    **响应**:
    - success: 是否有效
    - message: 消息
    - payload: 令牌载荷（有效时返回）
    
    **状态码**:
    - 200: token有效
    - 401: token无效或已过期
    - 400: 缺少token参数
    
    **示例**:
    ```json
    {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    ```
    """
    payload = verify_token(verify_request.token)
    
    if payload:
        return VerifyTokenResponse(
            success=True,
            message="token有效",
            payload=payload
        )
    else:
        # token无效时返回401状态码
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "message": "token无效或已过期"
            }
        )


@router.post("/api/change-password", tags=["认证"])
async def change_password(
    change_request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    修改密码接口（需要token认证）
    
    **请求头**:
    - Authorization: Bearer {token}
    
    **请求体**:
    - new_password: 新密码（至少6个字符）
    
    **响应**:
    - success: 是否成功
    - message: 消息
    
    **状态码**:
    - 200: 修改成功
    - 400: 参数错误或新密码与旧密码相同
    - 401: token无效
    - 404: 用户不存在
    
    **示例**:
    ```json
    {
        "new_password": "newpassword123"
    }
    ```
    """
    user_id = current_user.get("user_id")
    username = current_user.get("username")
    
    if not user_id:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "message": "token中缺少用户信息"
            }
        )
    
    # 修改密码
    success, message = await auth_service.change_password(user_id, change_request.new_password)
    
    if success:
        logger.info(f"用户 {username} (ID: {user_id}) 修改密码成功")
        return {"success": True, "message": message}
    else:
        # 根据错误消息返回不同的状态码
        from fastapi.responses import JSONResponse
        if "不存在" in message:
            status_code = 404
        elif "相同" in message:
            status_code = 400
        else:
            status_code = 400
        
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "message": message
            }
        )


@router.options("/api/login")
async def login_options():
    """处理登录接口的OPTIONS预检请求"""
    return {"message": "OK"}
