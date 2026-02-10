"""认证相关的Pydantic模型"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    password: str = Field(..., min_length=1, description="密码")


class LoginResponse(BaseModel):
    """登录响应"""
    success: bool
    message: str
    token: Optional[str] = None
    user_info: Optional[dict] = None


class VerifyTokenRequest(BaseModel):
    """验证Token请求"""
    token: str = Field(..., description="JWT令牌")


class VerifyTokenResponse(BaseModel):
    """验证Token响应"""
    success: bool
    message: str
    payload: Optional[dict] = None


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    new_password: str = Field(..., min_length=6, description="新密码（至少6个字符）")


class ChangePasswordResponse(BaseModel):
    """修改密码响应"""
    success: bool
    message: str
