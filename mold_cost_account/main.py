from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import json
import logging
from datetime import datetime, timedelta
import uuid
from config.config import get_config
from app.services.database import db_manager
from app.api.process_rules import process_rules_bp
from app.api.price_items import price_items_bp
from app.api.chat_sessions import chat_sessions_bp

# 获取配置
config = get_config()

# 尝试导入bcrypt和jwt
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    print("警告: bcrypt库未安装，无法验证bcrypt哈希密码")

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    print("警告: PyJWT库未安装，无法生成JWT token")

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(config)

# 注册蓝图
app.register_blueprint(process_rules_bp)
app.register_blueprint(price_items_bp)
app.register_blueprint(chat_sessions_bp)

# 手动处理CORS
@app.after_request
def after_request(response):
    """添加CORS头"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

@app.route('/api/login', methods=['OPTIONS'])
def handle_options():
    """处理预检请求"""
    return '', 200
    return '', 200

class AuthService:
    def __init__(self):
        self.db = db_manager
        self.max_failed_attempts = config.MAX_FAILED_LOGIN_ATTEMPTS
    
    def hash_password(self, password: str) -> str:
        """简单的密码哈希（生产环境建议使用bcrypt）"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_access_token(self, data: dict) -> str:
        """创建JWT访问令牌"""
        if not JWT_AVAILABLE:
            logger.warning("JWT库未安装，无法生成token")
            return None
            
        try:
            to_encode = data.copy()
            expire = datetime.utcnow() + timedelta(minutes=config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
            to_encode.update({"exp": expire})
            encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)
            return encoded_jwt
        except Exception as e:
            logger.error(f"JWT token生成错误: {e}")
            return None
    
    def verify_token(self, token: str) -> dict:
        """验证JWT令牌"""
        if not JWT_AVAILABLE:
            return None
            
        try:
            payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token已过期")
            return None
        except jwt.JWTError as e:
            logger.warning(f"JWT token验证失败: {e}")
            return None
    
    def verify_password(self, plain_password: str, stored_hash: str) -> bool:
        """验证密码"""
        try:
            # 检查是否是bcrypt哈希
            if stored_hash.startswith('$2b$') or stored_hash.startswith('$2a$') or stored_hash.startswith('$2y$'):
                if BCRYPT_AVAILABLE:
                    # 使用bcrypt验证
                    return bcrypt.checkpw(plain_password.encode('utf-8'), stored_hash.encode('utf-8'))
                else:
                    logger.error("数据库中存储的是bcrypt哈希，但bcrypt库未安装")
                    return False
            else:
                # 简单哈希比较（用于测试）
                return self.hash_password(plain_password) == stored_hash
        except Exception as e:
            logger.error(f"密码验证错误: {e}")
            return False
    
    def get_user_by_username(self, username: str):
        """根据用户名获取用户信息"""
        query = """
        SELECT user_id, username, password_hash, email, real_name, role, 
               department, is_active, is_locked, failed_login_attempts,
               last_login_at, created_at
        FROM users 
        WHERE username = %s
        """
        return self.db.execute_query(query, (username,), fetch_one=True)
    
    def update_login_info(self, user_id: str, client_ip: str, success: bool = True):
        """更新登录信息"""
        try:
            if success:
                query = """
                UPDATE users 
                SET last_login_at = %s, last_login_ip = %s, 
                    failed_login_attempts = 0, is_locked = false,
                    updated_at = %s
                WHERE user_id = %s
                """
                params = (datetime.now(), client_ip, datetime.now(), user_id)
            else:
                query = """
                UPDATE users 
                SET failed_login_attempts = failed_login_attempts + 1,
                    is_locked = CASE 
                        WHEN failed_login_attempts + 1 >= %s THEN true 
                        ELSE is_locked 
                    END,
                    updated_at = %s
                WHERE user_id = %s
                """
                params = (self.max_failed_attempts, datetime.now(), user_id)
            
            self.db.execute_query(query, params)
        except Exception as e:
            logger.error(f"更新登录信息错误: {e}")
    
    def authenticate_user(self, username: str, password: str, client_ip: str):
        """用户认证"""
        try:
            # 获取用户信息
            user = self.get_user_by_username(username)
            if not user:
                return False, "用户名或密码错误", None
            
            # 检查账号状态
            if not user['is_active']:
                return False, "账号已被禁用", None
            
            if user['is_locked']:
                return False, "账号已被锁定，请联系管理员", None
            
            # 验证密码
            if not self.verify_password(password, user['password_hash']):
                # 更新失败登录信息
                self.update_login_info(str(user['user_id']), client_ip, success=False)
                
                failed_attempts = user['failed_login_attempts'] + 1
                if failed_attempts >= self.max_failed_attempts:
                    return False, "密码错误次数过多，账号已被锁定", None
                else:
                    return False, f"用户名或密码错误，还有{self.max_failed_attempts - failed_attempts}次机会", None
            
            # 登录成功
            self.update_login_info(str(user['user_id']), client_ip, success=True)
            
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

# 初始化服务
auth_service = AuthService()

def get_client_ip():
    """获取客户端IP地址"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

@app.route('/')
def root():
    """根路径"""
    return jsonify({
        "message": f"{config.APP_NAME}服务正在运行",
        "version": config.APP_VERSION,
        "environment": app.config.get('ENV', 'development')
    })

@app.route('/health')
def health_check():
    """健康检查"""
    # 测试数据库连接
    db_status = db_manager.test_connection()
    
    return jsonify({
        "status": "healthy" if db_status else "unhealthy",
        "service": "login-api",
        "version": config.APP_VERSION,
        "database": "connected" if db_status else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/api/login', methods=['POST'])
def login():
    """用户登录接口"""
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "请求数据格式错误"
            }), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # 验证输入
        if not username or not password:
            return jsonify({
                "success": False,
                "message": "用户名和密码不能为空"
            }), 400
        
        # 获取客户端IP
        client_ip = get_client_ip()

        # 用户认证
        success, message, user_info = auth_service.authenticate_user(
            username, password, client_ip
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
            access_token = auth_service.create_access_token(token_data)
            
            logger.info(f"用户 {username} 登录成功，IP: {client_ip}")
            return jsonify({
                "success": True,
                "message": message,
                "token": access_token,
                "user_info": user_info
            })
        else:
            logger.warning(f"用户 {username} 登录失败: {message}，IP: {client_ip}")
            return jsonify({
                "success": False,
                "message": message
            })
            
    except Exception as e:
        logger.error(f"登录接口异常: {e}")
        return jsonify({
            "success": False,
            "message": "服务器内部错误"
        }), 500

@app.route('/api/verify-token', methods=['POST'])
def verify_token():
    """验证JWT令牌"""
    try:
        data = request.get_json()
        if not data or 'token' not in data:
            return jsonify({
                "success": False,
                "message": "缺少token参数"
            }), 400
        
        token = data['token']
        payload = auth_service.verify_token(token)
        
        if payload:
            return jsonify({
                "success": True,
                "message": "token有效",
                "payload": payload
            })
        else:
            return jsonify({
                "success": False,
                "message": "token无效或已过期"
            }), 401
            
    except Exception as e:
        logger.error(f"token验证异常: {e}")
        return jsonify({
            "success": False,
            "message": "服务器内部错误"
        }), 500

@app.route('/api/change-password', methods=['POST'])
def change_password():
    """
    修改密码接口（需要token认证）
    
    请求头:
    Authorization: Bearer <token>
    
    请求体:
    {
        "new_password": "新密码"
    }
    """
    try:
        # 获取并验证token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                "success": False,
                "message": "缺少认证token"
            }), 401
        
        token = auth_header.split(' ')[1]
        payload = auth_service.verify_token(token)
        
        if not payload:
            return jsonify({
                "success": False,
                "message": "token无效或已过期"
            }), 401
        
        # 获取用户ID
        user_id = payload.get('user_id')
        username = payload.get('sub')
        
        if not user_id:
            return jsonify({
                "success": False,
                "message": "token中缺少用户信息"
            }), 401
        
        # 获取新密码
        data = request.get_json()
        if not data or 'new_password' not in data:
            return jsonify({
                "success": False,
                "message": "缺少new_password参数"
            }), 400
        
        new_password = data['new_password'].strip()
        
        # 验证新密码
        if not new_password:
            return jsonify({
                "success": False,
                "message": "新密码不能为空"
            }), 400
        
        if len(new_password) < 6:
            return jsonify({
                "success": False,
                "message": "新密码长度不能少于6个字符"
            }), 400
        
        # 获取当前用户的密码哈希
        query_user = """
        SELECT password_hash 
        FROM users 
        WHERE user_id = %s
        """
        user = db_manager.execute_query(query_user, (user_id,), fetch_one=True)
        
        if not user:
            return jsonify({
                "success": False,
                "message": "用户不存在"
            }), 404
        
        # 检查新密码是否与当前密码相同
        current_password_hash = user['password_hash']
        if auth_service.verify_password(new_password, current_password_hash):
            return jsonify({
                "success": False,
                "message": "新密码不能与当前密码相同"
            }), 400
        
        # 加密新密码
        if BCRYPT_AVAILABLE:
            # 使用bcrypt加密
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        else:
            # 使用简单哈希（不推荐用于生产环境）
            password_hash = auth_service.hash_password(new_password)
        
        # 更新密码
        query = """
        UPDATE users 
        SET password_hash = %s, updated_at = %s
        WHERE user_id = %s
        RETURNING user_id, username
        """
        result = db_manager.execute_query(
            query, 
            (password_hash, datetime.now(), user_id), 
            fetch_one=True
        )
        
        if result:
            logger.info(f"用户 {username} (ID: {user_id}) 修改密码成功")
            return jsonify({
                "success": True,
                "message": "密码修改成功"
            })
        else:
            return jsonify({
                "success": False,
                "message": "用户不存在"
            }), 404
            
    except Exception as e:
        logger.error(f"修改密码接口异常: {e}")
        return jsonify({
            "success": False,
            "message": "服务器内部错误"
        }), 500

if __name__ == "__main__":
    # 启动时测试数据库连接
    if db_manager.test_connection():
        logger.info("数据库连接测试成功")
    else:
        logger.error("数据库连接测试失败，请检查配置")
    
    logger.info(f"启动 {config.APP_NAME} v{config.APP_VERSION}")
    logger.info(f"数据库: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
    logger.info(f"JWT过期时间: {config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES}分钟")
    
    try:
        app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
    finally:
        # 应用关闭时清理连接池
        logger.info("正在关闭数据库连接池...")
        db_manager.close_all_connections()