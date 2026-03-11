"""
功能：发布任务进度到Redis，供WebSocket监听
"""
from shared.unified_logging import get_logger
import redis
import json
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = get_logger(__name__)


class ProgressPublisher:
    """
    进度发布器
    
    负责将任务进度发布到Redis Pub/Sub频道
    WebSocket服务会订阅这些频道，实时推送给前端
    
    频道格式: job:{job_id}:progress
    消息格式:
    {
        "stage": "cad_split_completed",
        "progress": 20,
        "message": "拆图完成，生成5个子图",
        "timestamp": "2026-01-14T13:52:03.730523",
        "details": {
            "subgraph_count": 5
        }
    }
    """
    
    def __init__(self, redis_url: str = None):
        """
        初始化进度发布器
        
        Args:
            redis_url: Redis连接URL，如果不提供则从环境变量读取
        """
        from api_gateway.config import settings
        self.redis_url = redis_url or os.getenv("REDIS_URL", settings.REDIS_URL)
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """连接到Redis（支持降级模式）"""
        # 检查是否启用降级模式（跳过 Redis）
        skip_redis_value = os.getenv("SKIP_REDIS", "false")
        # 确保 skip_redis_value 是字符串
        if isinstance(skip_redis_value, str):
            skip_redis = skip_redis_value.lower() in ("true", "1", "yes")
        else:
            skip_redis = False
        
        if skip_redis:
            logger.warning("⚠️ Redis 已禁用（SKIP_REDIS=true），进度将不会发布")
            self.redis_client = None
            return
        
        try:
            # 解析Redis URL
            # 格式: redis://host:port/db 或 redis://:password@host:port/db
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=30,  # 增加到 30 秒
                socket_timeout=30,          # 增加到 30 秒
                socket_keepalive=True,
                health_check_interval=30,
                retry_on_timeout=True,      # 超时时重试
                retry_on_error=[redis.ConnectionError, redis.TimeoutError]  # 连接错误时重试
            )
            
            # 测试连接
            self.redis_client.ping()
            logger.info(f"✅ Redis连接成功: {self.redis_url}")
            
        except redis.ConnectionError as e:
            logger.error(f"❌ Redis连接失败: {e}")
            logger.error("请检查:")
            logger.error("1. Redis服务是否启动")
            logger.error("2. REDIS_URL环境变量是否正确")
            logger.error("3. 网络连接是否正常")
            logger.error("4. 或设置 SKIP_REDIS=true 跳过 Redis（仅用于测试）")
            raise
        except Exception as e:
            logger.error(f"❌ Redis初始化失败: {e}")
            raise
    
    def publish_progress(
        self,
        job_id: str,
        stage: str,
        progress: int,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        发布进度消息
        
        Args:
            job_id: 任务ID
            stage: 阶段名称（使用 ProgressStage 常量）
            progress: 进度百分比 0-100
            message: 进度消息
            details: 额外的详细信息（可选）
        """
        # 如果 Redis 未初始化（降级模式），只记录日志
        if not self.redis_client:
            logger.warning(
                f"⚠️ Redis 未连接，跳过进度发布: job_id={job_id}, stage={stage}, "
                f"progress={progress}%, message={message}"
            )
            return
        
        try:
            # 构建频道名称
            channel = f"job:{job_id}:progress"
            
            # 构建消息体
            payload = {
                "stage": stage,
                "progress": progress,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "details": details or {}
            }
            
            # 发布到Redis
            subscribers = self.redis_client.publish(channel, json.dumps(payload))
            
            logger.info(
                f"📤 进度发布: job_id={job_id}, stage={stage}, "
                f"progress={progress}%, subscribers={subscribers}"
            )
            logger.debug(f"   消息内容: {message}")
            if details:
                logger.debug(f"   详细信息: {details}")
            
        except redis.RedisError as e:
            logger.error(f"❌ 发布进度失败: {e}")
            logger.error(f"   job_id={job_id}, stage={stage}")
        except Exception as e:
            logger.error(f"❌ 发布进度异常: {e}")
    
    def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            try:
                self.redis_client.close()
                logger.info("Redis连接已关闭")
            except Exception as e:
                logger.error(f"关闭Redis连接失败: {e}")


# 使用示例
if __name__ == "__main__":
    # 配置日志
    # 日志已统一配置，无需重复初始化
    # logging.basicConfig(...)
    
    # 创建发布器
    publisher = ProgressPublisher()
    
    # 发布测试消息
    test_job_id = "test_job_123"
    
    publisher.publish_progress(
        job_id=test_job_id,
        stage="cad_split_started",
        progress=5,
        message="开始拆图..."
    )
    
    publisher.publish_progress(
        job_id=test_job_id,
        stage="cad_split_completed",
        progress=20,
        message="拆图完成，生成5个子图",
        details={"subgraph_count": 5}
    )
    
    publisher.close()
    
    print(f"\n✅ 测试完成！")
    print(f"💡 在浏览器中打开 WebSocket 测试页面，输入 job_id: {test_job_id}")
