"""认证服务"""
from shared.unified_logging import get_logger
import logging
from datetime import datetime
from typing import Tuple, Optional
import asyncpg
import os
from dotenv import load_dotenv
from api_gateway.utils.account.password import verify_password, hash_password_bcrypt
from api_gateway.utils.account.jwt_helper import create_access_token
from api_gateway.config import settings

load_dotenv()

logger = get_logger(__name__)


class DatabaseConnection:
    """数据库连接管理器"""
    
    @staticmethod
    async def get_connection():
        """获取数据库连接"""
        return await asyncpg.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )


class AuthService:
    """认证服务类"""
    
    def __init__(self):
        self.max_failed_attempts = settings.MAX_FAILED_LOGIN_ATTEMPTS
    
    async def get_user_by_username(self, username: str) -> Optional[dict]:
        """
        根据用户名获取用户信息
        
        Args:
            username: 用户名
            
        Returns:
            用户信息字典，如果不存在则返回None
        """
        query = """
        SELECT user_id, username, password_hash, email, real_name, role, 
               department, is_active, is_locked, failed_login_attempts,
               last_login_at, created_at
        FROM users 
        WHERE username = $1
        """
        conn = await DatabaseConnection.get_connection()
        try:
            result = await conn.fetchrow(query, username)
            return dict(result) if result else None
        finally:
            await conn.close()
    
    async def update_login_info(self, user_id: str, client_ip: str, success: bool = True):
        """
        更新登录信息
        
        Args:
            user_id: 用户ID
            client_ip: 客户端IP
            success: 是否登录成功
        """
        try:
            conn = await DatabaseConnection.get_connection()
            try:
                if success:
                    query = """
                    UPDATE users 
                    SET last_login_at = $1, last_login_ip = $2, 
                        failed_login_attempts = 0, is_locked = false,
                        updated_at = $3
                    WHERE user_id = $4
                    """
                    params = (datetime.now(), client_ip, datetime.now(), user_id)
                else:
                    query = """
                    UPDATE users 
                    SET failed_login_attempts = failed_login_attempts + 1,
                        is_locked = CASE 
                            WHEN failed_login_attempts + 1 >= $1 THEN true 
                            ELSE is_locked 
                        END,
                        updated_at = $2
                    WHERE user_id = $3
                    """
                    params = (self.max_failed_attempts, datetime.now(), user_id)
                
                await conn.execute(query, *params)
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"更新登录信息错误: {e}")
    
    async def authenticate_user(
        self, username: str, password: str, client_ip: str
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        用户认证
        
        Args:
            username: 用户名
            password: 密码
            client_ip: 客户端IP
            
        Returns:
            (是否成功, 消息, 用户信息)
        """
        try:
            # 获取用户信息
            user = await self.get_user_by_username(username)
            if not user:
                return False, "用户名或密码错误", None
            
            # 检查账号状态
            if not user['is_active']:
                return False, "账号已被禁用", None
            
            if user['is_locked']:
                return False, "账号已被锁定，请联系管理员", None
            
            # 验证密码
            if not verify_password(password, user['password_hash']):
                # 更新失败登录信息
                await self.update_login_info(str(user['user_id']), client_ip, success=False)
                
                failed_attempts = user['failed_login_attempts'] + 1
                if failed_attempts >= self.max_failed_attempts:
                    return False, "密码错误次数过多，账号已被锁定", None
                else:
                    return False, f"用户名或密码错误，还有{self.max_failed_attempts - failed_attempts}次机会", None
            
            # 登录成功
            await self.update_login_info(str(user['user_id']), client_ip, success=True)
            
            # 准备用户信息
            user_info = {
                'user_id': str(user['user_id']),
                'username': user['username'],
                'email': user['email'],
                'real_name': user['real_name'],
                'role': user['role'],
                'department': user['department'],
                'is_active': user['is_active'],
                'last_login_at': user['last_login_at'].isoformat() if user['last_login_at'] else None,
                'created_at': user['created_at'].isoformat() if user['created_at'] else None
            }
            
            return True, "登录成功", user_info
            
        except Exception as e:
            logger.error(f"用户认证错误: {e}")
            return False, "系统错误，请稍后重试", None
    
    async def change_password(
        self, user_id: str, new_password: str
    ) -> Tuple[bool, str]:
        """
        修改密码
        
        Args:
            user_id: 用户ID
            new_password: 新密码
            
        Returns:
            (是否成功, 消息)
        """
        try:
            conn = await DatabaseConnection.get_connection()
            try:
                # 获取当前用户的密码哈希
                query_user = "SELECT password_hash, username FROM users WHERE user_id = $1"
                user = await conn.fetchrow(query_user, user_id)
                
                if not user:
                    return False, "用户不存在"
                
                # 检查新密码是否与当前密码相同
                if verify_password(new_password, user['password_hash']):
                    return False, "新密码不能与当前密码相同"
                
                # 加密新密码
                password_hash = hash_password_bcrypt(new_password)
                
                # 更新密码
                query = """
                UPDATE users 
                SET password_hash = $1, updated_at = $2
                WHERE user_id = $3
                RETURNING user_id, username
                """
                result = await conn.fetchrow(query, password_hash, datetime.now(), user_id)
                
                if result:
                    logger.info(f"用户 {result['username']} (ID: {user_id}) 修改密码成功")
                    return True, "密码修改成功"
                else:
                    return False, "用户不存在"
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"修改密码错误: {e}")
            return False, "系统错误，请稍后重试"


# 创建服务实例
auth_service = AuthService()
