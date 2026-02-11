"""价格项服务"""
import logging
from datetime import datetime
from typing import Tuple, Optional, List, Dict
from decimal import Decimal
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


class PriceItemService:
    """价格项服务类"""
    
    def _format_datetime(self, dt):
        """格式化datetime为ISO格式字符串"""
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%dT%H:%M:%S')
        return dt
    
    def _format_item_data(self, item):
        """格式化价格项数据，将datetime转换为字符串"""
        if not item:
            return None
        
        formatted_item = dict(item)
        if 'created_at' in formatted_item:
            formatted_item['created_at'] = self._format_datetime(formatted_item['created_at'])
        if 'updated_at' in formatted_item:
            formatted_item['updated_at'] = self._format_datetime(formatted_item['updated_at'])
        
        # 转换Decimal为字符串（保持精度）
        for key in ['price', 'work_hours', 'min_num', 'add_price', 'weight_num']:
            if key in formatted_item and formatted_item[key] is not None:
                formatted_item[key] = str(formatted_item[key]).strip()
        
        # trim 所有字符串字段，清除数据库中可能存在的前导/尾随空白字符
        for key in formatted_item:
            if isinstance(formatted_item[key], str):
                formatted_item[key] = formatted_item[key].strip()
        
        return formatted_item
    
    def _format_items_list(self, items):
        """格式化价格项列表"""
        if not items:
            return []
        return [self._format_item_data(item) for item in items]
    
    async def create_item(self, item_data: dict) -> Tuple[bool, str, Optional[dict]]:
        """创建价格项"""
        try:
            query = """
            INSERT INTO price_items 
            (id, version_id, category, sub_category, price, unit, work_hours, 
             min_num, add_price, weight_num, note, instruction, is_active, 
             created_by, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            RETURNING id, version_id, category, sub_category, price, unit, work_hours, 
                      min_num, add_price, weight_num, note, instruction, is_active, 
                      created_by, created_at, updated_at
            """
            
            now = datetime.now()
            
            # Decimal 类型字段需要转为 str（数据库列为 text 类型）
            def _to_str(val):
                return str(val) if isinstance(val, Decimal) else val
            
            params = (
                item_data['id'],
                item_data.get('version_id'),
                item_data.get('category'),
                item_data.get('sub_category'),
                _to_str(item_data.get('price')),
                item_data.get('unit'),
                _to_str(item_data.get('work_hours')),
                _to_str(item_data.get('min_num')),
                _to_str(item_data.get('add_price')),
                _to_str(item_data.get('weight_num')),
                item_data.get('note'),
                item_data.get('instruction'),
                item_data.get('is_active', True),
                item_data.get('created_by'),
                now,
                now
            )
            
            conn = await DatabaseConnection.get_connection()
            try:
                result = await conn.fetchrow(query, *params)
                return True, "价格项创建成功", self._format_item_data(result)
            finally:
                await conn.close()
            
        except Exception as e:
            logger.error(f"创建价格项失败: {e}")
            return False, f"创建价格项失败: {str(e)}", None
    
    async def get_item_by_id(self, item_id: str) -> Tuple[bool, str, Optional[dict]]:
        """根据ID获取价格项"""
        try:
            query = """
            SELECT id, version_id, category, sub_category, price, unit, work_hours, 
                   min_num, add_price, weight_num, note, instruction, is_active, 
                   created_by, created_at, updated_at
            FROM price_items
            WHERE id = $1
            """
            
            conn = await DatabaseConnection.get_connection()
            try:
                result = await conn.fetchrow(query, item_id)
                
                if result:
                    return True, "获取成功", self._format_item_data(result)
                else:
                    return False, "价格项不存在", None
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"获取价格项失败: {e}")
            return False, f"获取价格项失败: {str(e)}", None
    
    async def get_items(self, filters: Optional[dict] = None, page: int = 1, page_size: int = 20) -> Tuple[bool, str, Optional[dict]]:
        """获取价格项列表（支持分页和筛选）"""
        try:
            # 构建查询条件
            conditions = []
            params = []
            param_index = 1
            
            # 默认只查询激活的价格项
            is_active_filter = True
            
            if filters:
                if filters.get('version_id'):
                    conditions.append(f"version_id = ${param_index}")
                    params.append(filters['version_id'])
                    param_index += 1
                
                if filters.get('category'):
                    conditions.append(f"category = ${param_index}")
                    params.append(filters['category'])
                    param_index += 1
                
                if filters.get('sub_category'):
                    conditions.append(f"sub_category ILIKE ${param_index}")
                    params.append(f"%{filters['sub_category']}%")
                    param_index += 1
                
                if filters.get('is_active') is not None:
                    is_active_filter = filters['is_active']
            
            # 添加is_active条件
            conditions.append(f"is_active = ${param_index}")
            params.append(is_active_filter)
            param_index += 1
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            conn = await DatabaseConnection.get_connection()
            try:
                # 查询总数
                count_query = f"SELECT COUNT(*) as total FROM price_items WHERE {where_clause}"
                count_result = await conn.fetchrow(count_query, *params)
                total = count_result['total'] if count_result else 0
                
                # 查询数据
                offset = (page - 1) * page_size
                query = f"""
                SELECT id, version_id, category, sub_category, price, unit, work_hours, 
                       min_num, add_price, weight_num, note, instruction, is_active, 
                       created_by, created_at, updated_at
                FROM price_items
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
                    'data': self._format_items_list(results)
                }
            finally:
                await conn.close()
            
        except Exception as e:
            logger.error(f"获取价格项列表失败: {e}")
            return False, f"获取价格项列表失败: {str(e)}", None
    
    async def update_item(self, item_id: str, update_data: dict) -> Tuple[bool, str, Optional[dict]]:
        """更新价格项"""
        try:
            # 构建更新字段
            update_fields = []
            params = []
            param_index = 1
            
            allowed_fields = ['version_id', 'category', 'sub_category', 'price', 'unit', 
                            'work_hours', 'min_num', 'add_price', 'weight_num', 'note', 
                            'instruction', 'is_active', 'created_by']
            
            # Decimal 类型字段需要转为 str（数据库列为 text 类型）
            decimal_fields = {'price', 'work_hours', 'min_num', 'add_price', 'weight_num'}
            
            for field in allowed_fields:
                if field in update_data:
                    value = update_data[field]
                    # 将 Decimal 转为 str，asyncpg 期望 str 而非 Decimal
                    if field in decimal_fields and isinstance(value, Decimal):
                        value = str(value)
                    update_fields.append(f"{field} = ${param_index}")
                    params.append(value)
                    param_index += 1
            
            if not update_fields:
                return False, "没有需要更新的字段", None
            
            # 添加updated_at字段
            update_fields.append(f"updated_at = ${param_index}")
            params.append(datetime.now())
            param_index += 1
            
            params.append(item_id)
            
            query = f"""
            UPDATE price_items
            SET {', '.join(update_fields)}
            WHERE id = ${param_index}
            RETURNING id, version_id, category, sub_category, price, unit, work_hours, 
                      min_num, add_price, weight_num, note, instruction, is_active, 
                      created_by, created_at, updated_at
            """
            
            conn = await DatabaseConnection.get_connection()
            try:
                result = await conn.fetchrow(query, *params)
                
                if result:
                    return True, "价格项更新成功", self._format_item_data(result)
                else:
                    return False, "价格项不存在", None
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"更新价格项失败: {e}")
            return False, f"更新价格项失败: {str(e)}", None
    
    async def delete_item(self, item_id: str) -> Tuple[bool, str, None]:
        """删除价格项（硬删除）"""
        try:
            query = "DELETE FROM price_items WHERE id = $1 RETURNING id"
            
            conn = await DatabaseConnection.get_connection()
            try:
                result = await conn.fetchrow(query, item_id)
                
                if result:
                    return True, "价格项删除成功", None
                else:
                    return False, "价格项不存在", None
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"删除价格项失败: {e}")
            return False, f"删除价格项失败: {str(e)}", None
    
    async def soft_delete_item(self, item_id: str) -> Tuple[bool, str, Optional[dict]]:
        """软删除价格项（将is_active设为false）"""
        try:
            query = """
            UPDATE price_items
            SET is_active = false, updated_at = $1
            WHERE id = $2
            RETURNING id, version_id, category, sub_category, price, unit, work_hours, 
                      min_num, add_price, weight_num, note, instruction, is_active, 
                      created_by, created_at, updated_at
            """
            
            conn = await DatabaseConnection.get_connection()
            try:
                result = await conn.fetchrow(query, datetime.now(), item_id)
                
                if result:
                    return True, "价格项已停用", self._format_item_data(result)
                else:
                    return False, "价格项不存在", None
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"软删除价格项失败: {e}")
            return False, f"软删除价格项失败: {str(e)}", None
    
    async def batch_delete_items(self, item_ids: List[str]) -> Tuple[bool, str, Optional[dict]]:
        """批量删除价格项（硬删除）"""
        try:
            placeholders = ','.join([f'${i+1}' for i in range(len(item_ids))])
            query = f"DELETE FROM price_items WHERE id IN ({placeholders}) RETURNING id"
            
            conn = await DatabaseConnection.get_connection()
            try:
                results = await conn.fetch(query, *item_ids)
                
                deleted_count = len(results) if results else 0
                return True, f"成功删除 {deleted_count} 条价格项", {'deleted_count': deleted_count}
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"批量删除价格项失败: {e}")
            return False, f"批量删除价格项失败: {str(e)}", None
    
    async def batch_soft_delete_items(self, item_ids: List[str]) -> Tuple[bool, str, Optional[dict]]:
        """批量软删除价格项（将is_active设为false）"""
        try:
            placeholders = ','.join([f'${i+2}' for i in range(len(item_ids))])
            query = f"""
            UPDATE price_items
            SET is_active = false, updated_at = $1
            WHERE id IN ({placeholders})
            RETURNING id
            """
            
            params = [datetime.now()] + list(item_ids)
            
            conn = await DatabaseConnection.get_connection()
            try:
                results = await conn.fetch(query, *params)
                
                updated_count = len(results) if results else 0
                return True, f"成功停用 {updated_count} 条价格项", {'updated_count': updated_count}
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"批量软删除价格项失败: {e}")
            return False, f"批量软删除价格项失败: {str(e)}", None
    
    async def get_items_by_version_and_category(
        self, version_id: str, category: str, active_only: bool = True
    ) -> Tuple[bool, str, Optional[List[dict]]]:
        """根据版本和类别获取价格项"""
        try:
            query = """
            SELECT id, version_id, category, sub_category, price, unit, work_hours, 
                   min_num, add_price, weight_num, note, instruction, is_active, 
                   created_by, created_at, updated_at
            FROM price_items
            WHERE version_id = $1 AND category = $2
            """
            params = [version_id, category]
            
            if active_only:
                query += " AND is_active = true"
            
            query += " ORDER BY created_at DESC"
            
            conn = await DatabaseConnection.get_connection()
            try:
                results = await conn.fetch(query, *params)
                return True, "获取成功", self._format_items_list(results)
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"获取价格项失败: {e}")
            return False, f"获取价格项失败: {str(e)}", None


# 创建服务实例
price_item_service = PriceItemService()
