"""
BaseActionHandler - 动作处理器基类
负责人：人员B2

定义动作处理器的接口和公共方法
"""
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from shared.timezone_utils import now_shanghai

from agents.intent_types import IntentResult, ActionResult, IntentType

logger = logging.getLogger(__name__)


class BaseActionHandler(ABC):
    """
    动作处理器基类
    
    所有具体的 Handler 都应继承此类并实现 handle() 方法
    """
    
    def __init__(self):
        """初始化 Handler"""
        self._redis_client = None
    
    @property
    def redis_client(self):
        """懒加载 Redis 客户端"""
        if self._redis_client is None:
            from api_gateway.utils.redis_client import redis_client
            self._redis_client = redis_client
        return self._redis_client
    
    @abstractmethod
    async def handle(
        self,
        intent_result: IntentResult,
        job_id: str,
        context: Dict[str, Any],
        db_session
    ) -> ActionResult:
        """
        处理意图
        
        Args:
            intent_result: 意图识别结果
            job_id: 任务ID
            context: 当前审核数据上下文
            db_session: 数据库会话
        
        Returns:
            ActionResult: 处理结果
        """
        pass
    
    # ========== Redis 状态管理辅助方法 ==========
    
    def _serialize_for_redis(self, data: Any) -> str:
        """
        序列化数据为 JSON（处理 datetime 对象）
        
        Args:
            data: 要序列化的数据
        
        Returns:
            JSON 字符串
        """
        def default_handler(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
        
        return json.dumps(data, ensure_ascii=False, default=default_handler)
    
    async def _save_pending_action(
        self,
        job_id: str,
        pending_action: Dict[str, Any]
    ):
        """
        保存待确认的操作到 Redis
        
        Args:
            job_id: 任务ID
            pending_action: 待确认的操作数据
        """
        key = f"review:pending_action:{job_id}"
        
        # 添加时间戳
        pending_action["created_at"] = now_shanghai().isoformat()
        
        await self.redis_client.set(
            key,
            self._serialize_for_redis(pending_action),
            ex=3600  # 1小时过期
        )
        
        logger.debug(f"💾 pending_action 已保存: {key}")
    
    async def _get_pending_action(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        从 Redis 获取待确认的操作
        
        Args:
            job_id: 任务ID
        
        Returns:
            待确认的操作数据，如果不存在返回 None
        """
        key = f"review:pending_action:{job_id}"
        data = await self.redis_client.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    async def _clear_pending_action(self, job_id: str):
        """
        清理 Redis 中的待确认操作
        
        Args:
            job_id: 任务ID
        """
        key = f"review:pending_action:{job_id}"
        await self.redis_client.delete(key)
        logger.debug(f"🗑️  pending_action 已清理: {key}")
    
    # ========== 辅助方法 ==========
    
    def _get_all_subgraph_ids(self, context: Dict[str, Any]) -> list[str]:
        """
        获取所有子图的 ID
        
        Args:
            context: 数据上下文（支持两种格式）
                - 格式1: {"subgraphs": [...]}  # 直接包含 subgraphs
                - 格式2: {"raw_data": {"subgraphs": [...]}}  # 嵌套在 raw_data 中
        
        Returns:
            subgraph_ids 列表
        """
        # 兼容两种数据结构
        if "raw_data" in context:
            # 格式2: 嵌套结构
            subgraphs = context.get("raw_data", {}).get("subgraphs", [])
            logger.debug(f"📊 从 raw_data 中获取子图: {len(subgraphs)} 个")
        else:
            # 格式1: 直接结构
            subgraphs = context.get("subgraphs", [])
            logger.debug(f"📊 从 context 中直接获取子图: {len(subgraphs)} 个")
        
        subgraph_ids = [sg.get("subgraph_id") for sg in subgraphs if sg.get("subgraph_id")]
        logger.debug(f"✅ 提取到 {len(subgraph_ids)} 个 subgraph_id")
        
        return subgraph_ids


class ActionHandlerFactory:
    """
    动作处理器工厂
    
    根据意图类型创建相应的 Handler
    """
    
    _handlers: Dict[str, BaseActionHandler] = {}
    
    @classmethod
    def register_handler(cls, intent_type: str, handler: BaseActionHandler):
        """
        注册 Handler
        
        Args:
            intent_type: 意图类型
            handler: Handler 实例
        """
        cls._handlers[intent_type] = handler
        logger.info(f"✅ 注册 Handler: {intent_type} -> {handler.__class__.__name__}")
    
    @classmethod
    def get_handler(cls, intent_type: str) -> Optional[BaseActionHandler]:
        """
        获取 Handler
        
        Args:
            intent_type: 意图类型
        
        Returns:
            Handler 实例，如果未注册返回 None
        """
        handler = cls._handlers.get(intent_type)
        
        if not handler:
            logger.warning(f"⚠️  未找到 Handler: {intent_type}")
        
        return handler
    
    @classmethod
    def initialize_handlers(cls):
        """
        初始化所有 Handler
        
        这个方法会在应用启动时调用，注册所有的 Handler
        """
        from .data_modification_handler import DataModificationHandler
        from .feature_recognition_handler import FeatureRecognitionHandler
        from .price_calculation_handler import PriceCalculationHandler
        from .query_details_handler import QueryDetailsHandler
        from .general_chat_handler import GeneralChatHandler
        
        # 注册所有 Handler
        cls.register_handler(IntentType.DATA_MODIFICATION, DataModificationHandler())
        cls.register_handler(IntentType.FEATURE_RECOGNITION, FeatureRecognitionHandler())
        cls.register_handler(IntentType.PRICE_CALCULATION, PriceCalculationHandler())
        cls.register_handler(IntentType.QUERY_DETAILS, QueryDetailsHandler())
        cls.register_handler(IntentType.GENERAL_CHAT, GeneralChatHandler())
        
        logger.info(f"✅ 所有 Handler 已注册，共 {len(cls._handlers)} 个")
