"""工艺规则服务"""
import logging
from datetime import datetime
from typing import Tuple, Optional, List, Dict
import asyncpg
from api_gateway.config import settings

logger = logging.getLogger(__name__)


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


class ProcessRuleService:
    """工艺规则服务类"""
    
    # 规则条件映射表
    RULE_MAPPING = {
        '慢丝割一修一': 'slow_and_one',
        '慢丝割一刀': 'slow_cut',
        '快丝割一刀': 'fast_cut',
        '中丝割一修一': 'middle_and_one'
    }
    
    def _format_datetime(self, dt):
        """格式化datetime为ISO格式字符串"""
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%dT%H:%M:%S')
        return dt
    
    def _format_rule_data(self, rule):
        """格式化规则数据，将datetime转换为字符串"""
        if not rule:
            return None
        
        formatted_rule = dict(rule)
        if 'created_at' in formatted_rule:
            formatted_rule['created_at'] = self._format_datetime(formatted_rule['created_at'])
        
        return formatted_rule
    
    def _format_rules_list(self, rules):
        """格式化规则列表"""
        if not rules:
            return []
        return [self._format_rule_data(rule) for rule in rules]
    
    def _parse_description_to_conditions(self, description: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        根据description解析规则条件
        
        Args:
            description: 描述文本
        
        Returns:
            (conditions, output_params, error_message)
        """
        if not description:
            return None, None, "description不能为空"
        
        # 查找匹配的规则
        matched_rule = None
        for rule_text, rule_code in self.RULE_MAPPING.items():
            if rule_text in description:
                matched_rule = rule_code
                break
        
        if not matched_rule:
            # 列出所有支持的规则
            supported_rules = ', '.join(self.RULE_MAPPING.keys())
            return None, None, f"description中的规则条件无法识别。支持的规则: {supported_rules}"
        
        # 生成conditions和output_params
        conditions = matched_rule
        output_params = matched_rule
        
        return conditions, output_params, None
    
    async def create_rule(self, rule_data: dict) -> Tuple[bool, str, Optional[dict]]:
        """创建工艺规则"""
        try:
            # 如果没有提供conditions和output_params，从description解析
            if 'conditions' not in rule_data or 'output_params' not in rule_data:
                if 'description' not in rule_data:
                    return False, "缺少description字段或conditions/output_params字段", None
                
                conditions, output_params, error_msg = self._parse_description_to_conditions(
                    rule_data['description']
                )
                
                if error_msg:
                    return False, error_msg, None
                
                rule_data['conditions'] = conditions
                rule_data['output_params'] = output_params
            
            # 如果没有提供version_id，使用默认值 v1.0
            if 'version_id' not in rule_data:
                rule_data['version_id'] = 'v1.0'
            
            query = """
            INSERT INTO process_rules 
            (id, version_id, feature_type, name, description, priority, 
             is_active, conditions, output_params, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id, version_id, feature_type, name, description,
                      priority, is_active, conditions, output_params, created_at
            """
            
            params = (
                rule_data['id'],
                rule_data['version_id'],
                rule_data['feature_type'],
                rule_data['name'],
                rule_data.get('description'),
                rule_data.get('priority', 1),
                rule_data.get('is_active', True),
                rule_data['conditions'],
                rule_data['output_params'],
                datetime.now()
            )
            
            conn = await DatabaseConnection.get_connection()
            try:
                result = await conn.fetchrow(query, *params)
                return True, "规则创建成功", self._format_rule_data(result)
            finally:
                await conn.close()
            
        except Exception as e:
            logger.error(f"创建规则失败: {e}")
            return False, f"创建规则失败: {str(e)}", None
    
    async def get_rule_by_id(self, rule_id: str) -> Tuple[bool, str, Optional[dict]]:
        """根据ID获取规则"""
        try:
            query = """
            SELECT id, version_id, feature_type, name, description,
                   priority, is_active, conditions, output_params, created_at
            FROM process_rules
            WHERE id = $1
            """
            
            conn = await DatabaseConnection.get_connection()
            try:
                result = await conn.fetchrow(query, rule_id)
                
                if result:
                    return True, "获取成功", self._format_rule_data(result)
                else:
                    return False, "规则不存在", None
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"获取规则失败: {e}")
            return False, f"获取规则失败: {str(e)}", None
    
    async def get_rules(self, filters: Optional[dict] = None, page: int = 1, page_size: int = 20) -> Tuple[bool, str, Optional[dict]]:
        """获取规则列表（支持分页和筛选）"""
        try:
            # 构建查询条件
            conditions = []
            params = []
            param_index = 1
            
            # 默认只查询激活的规则
            is_active_filter = True
            
            if filters:
                if filters.get('version_id'):
                    conditions.append(f"version_id = ${param_index}")
                    params.append(filters['version_id'])
                    param_index += 1
                
                if filters.get('feature_type'):
                    conditions.append(f"feature_type = ${param_index}")
                    params.append(filters['feature_type'])
                    param_index += 1
                
                if filters.get('is_active') is not None:
                    is_active_filter = filters['is_active']
                
                if filters.get('name'):
                    conditions.append(f"name ILIKE ${param_index}")
                    params.append(f"%{filters['name']}%")
                    param_index += 1
            
            # 添加is_active条件
            conditions.append(f"is_active = ${param_index}")
            params.append(is_active_filter)
            param_index += 1
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            conn = await DatabaseConnection.get_connection()
            try:
                # 查询总数
                count_query = f"SELECT COUNT(*) as total FROM process_rules WHERE {where_clause}"
                count_result = await conn.fetchrow(count_query, *params)
                total = count_result['total'] if count_result else 0
                
                # 查询数据
                offset = (page - 1) * page_size
                query = f"""
                SELECT id, version_id, feature_type, name, description,
                       priority, is_active, conditions, output_params, created_at
                FROM process_rules
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_index} OFFSET ${param_index + 1}
                """
                
                params.extend([page_size, offset])
                results = await conn.fetch(query, *params)
                
                return True, "获取成功", {
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (total + page_size - 1) // page_size,
                    'data': self._format_rules_list(results)
                }
            finally:
                await conn.close()
            
        except Exception as e:
            logger.error(f"获取规则列表失败: {e}")
            return False, f"获取规则列表失败: {str(e)}", None
    
    async def update_rule(self, rule_id: str, update_data: dict) -> Tuple[bool, str, Optional[dict]]:
        """更新规则"""
        try:
            # 构建更新字段
            update_fields = []
            params = []
            param_index = 1
            
            allowed_fields = ['version_id', 'feature_type', 'name', 'description',
                            'priority', 'is_active', 'conditions', 'output_params']
            
            for field in allowed_fields:
                if field in update_data:
                    update_fields.append(f"{field} = ${param_index}")
                    params.append(update_data[field])
                    param_index += 1
            
            if not update_fields:
                return False, "没有需要更新的字段", None
            
            params.append(rule_id)
            
            query = f"""
            UPDATE process_rules
            SET {', '.join(update_fields)}
            WHERE id = ${param_index}
            RETURNING id, version_id, feature_type, name, description,
                      priority, is_active, conditions, output_params, created_at
            """
            
            conn = await DatabaseConnection.get_connection()
            try:
                result = await conn.fetchrow(query, *params)
                
                if result:
                    return True, "规则更新成功", self._format_rule_data(result)
                else:
                    return False, "规则不存在", None
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"更新规则失败: {e}")
            return False, f"更新规则失败: {str(e)}", None
    
    async def delete_rule(self, rule_id: str) -> Tuple[bool, str, None]:
        """删除规则（硬删除）"""
        try:
            query = "DELETE FROM process_rules WHERE id = $1 RETURNING id"
            
            conn = await DatabaseConnection.get_connection()
            try:
                result = await conn.fetchrow(query, rule_id)
                
                if result:
                    return True, "规则删除成功", None
                else:
                    return False, "规则不存在", None
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"删除规则失败: {e}")
            return False, f"删除规则失败: {str(e)}", None
    
    async def soft_delete_rule(self, rule_id: str) -> Tuple[bool, str, Optional[dict]]:
        """软删除规则（将is_active设为false）"""
        try:
            query = """
            UPDATE process_rules
            SET is_active = false
            WHERE id = $1
            RETURNING id, version_id, feature_type, name, description,
                      priority, is_active, conditions, output_params, created_at
            """
            
            conn = await DatabaseConnection.get_connection()
            try:
                result = await conn.fetchrow(query, rule_id)
                
                if result:
                    return True, "规则已停用", self._format_rule_data(result)
                else:
                    return False, "规则不存在", None
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"软删除规则失败: {e}")
            return False, f"软删除规则失败: {str(e)}", None
    
    async def batch_delete_rules(self, rule_ids: List[str]) -> Tuple[bool, str, Optional[dict]]:
        """批量删除规则（硬删除）"""
        try:
            placeholders = ','.join([f'${i+1}' for i in range(len(rule_ids))])
            query = f"DELETE FROM process_rules WHERE id IN ({placeholders}) RETURNING id"
            
            conn = await DatabaseConnection.get_connection()
            try:
                results = await conn.fetch(query, *rule_ids)
                
                deleted_count = len(results) if results else 0
                return True, f"成功删除 {deleted_count} 条规则", {'deleted_count': deleted_count}
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"批量删除规则失败: {e}")
            return False, f"批量删除规则失败: {str(e)}", None
    
    async def batch_soft_delete_rules(self, rule_ids: List[str]) -> Tuple[bool, str, Optional[dict]]:
        """批量软删除规则（将is_active设为false）"""
        try:
            placeholders = ','.join([f'${i+1}' for i in range(len(rule_ids))])
            query = f"""
            UPDATE process_rules
            SET is_active = false
            WHERE id IN ({placeholders})
            RETURNING id
            """
            
            conn = await DatabaseConnection.get_connection()
            try:
                results = await conn.fetch(query, *rule_ids)
                
                updated_count = len(results) if results else 0
                return True, f"成功停用 {updated_count} 条规则", {'updated_count': updated_count}
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"批量软删除规则失败: {e}")
            return False, f"批量软删除规则失败: {str(e)}", None
    
    async def get_rules_by_version_and_type(
        self, version_id: str, feature_type: str, active_only: bool = True
    ) -> Tuple[bool, str, Optional[List[dict]]]:
        """根据版本和特征类型获取规则"""
        try:
            query = """
            SELECT id, version_id, feature_type, name, description,
                   priority, is_active, conditions, output_params, created_at
            FROM process_rules
            WHERE version_id = $1 AND feature_type = $2
            """
            params = [version_id, feature_type]
            
            if active_only:
                query += " AND is_active = true"
            
            query += " ORDER BY created_at DESC"
            
            conn = await DatabaseConnection.get_connection()
            try:
                results = await conn.fetch(query, *params)
                return True, "获取成功", self._format_rules_list(results)
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"获取规则失败: {e}")
            return False, f"获取规则失败: {str(e)}", None


# 创建服务实例
process_rule_service = ProcessRuleService()
