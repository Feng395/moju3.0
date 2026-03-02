"""聊天会话服务"""
from shared.unified_logging import get_logger
import logging
import time
from datetime import datetime
from typing import Tuple, Optional, List, Dict, Any
import asyncpg
from api_gateway.config import settings

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


class ChatSessionService:
    """聊天会话服务类"""
    
    def _format_datetime(self, dt):
        """格式化datetime为ISO格式字符串"""
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%dT%H:%M:%S')
        return dt
    
    def _format_session_data(self, session):
        """格式化会话数据"""
        if not session:
            return None
        
        formatted = dict(session)
        if 'created_at' in formatted:
            formatted['created_at'] = self._format_datetime(formatted['created_at'])
        if 'updated_at' in formatted:
            formatted['updated_at'] = self._format_datetime(formatted['updated_at'])
        
        return formatted
    
    async def get_session_by_id(self, session_id: str) -> Optional[dict]:
        """根据会话ID获取会话信息"""
        try:
            query = """
            SELECT session_id, job_id, user_id, name, status, metadata,
                   created_at, updated_at
            FROM chat_sessions
            WHERE session_id = $1
            """
            
            conn = await DatabaseConnection.get_connection()
            try:
                result = await conn.fetchrow(query, session_id)
                return self._format_session_data(result) if result else None
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"获取会话信息失败: {e}")
            return None
    
    async def get_session_by_job_id(self, job_id: str, user_id: Optional[str] = None) -> Optional[dict]:
        """根据任务ID获取会话信息"""
        try:
            conn = await DatabaseConnection.get_connection()
            try:
                if user_id:
                    query = """
                    SELECT session_id, job_id, user_id, name, status, metadata,
                           created_at, updated_at
                    FROM chat_sessions
                    WHERE job_id = $1 AND user_id = $2
                    """
                    result = await conn.fetchrow(query, job_id, user_id)
                else:
                    query = """
                    SELECT session_id, job_id, user_id, name, status, metadata,
                           created_at, updated_at
                    FROM chat_sessions
                    WHERE job_id = $1
                    """
                    result = await conn.fetchrow(query, job_id)
                
                return self._format_session_data(result) if result else None
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"根据job_id获取会话信息失败: {e}")
            return None
    
    async def update_session_name_by_job_id(
        self,
        job_id: str,
        name: str,
        user_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[dict]]:
        """根据任务ID更新会话名称"""
        try:
            # 验证输入
            if not job_id or not job_id.strip():
                return False, "任务ID不能为空", None
            
            if not name or not name.strip():
                return False, "会话名称不能为空", None
            
            name = name.strip()
            
            # 检查名称长度
            if len(name) > 255:
                return False, "会话名称不能超过255个字符", None
            
            # 检查会话是否存在
            session = await self.get_session_by_job_id(job_id, user_id)
            if not session:
                return False, "会话不存在或无权访问", None
            
            # 更新会话名称
            conn = await DatabaseConnection.get_connection()
            try:
                if user_id:
                    query = """
                    UPDATE chat_sessions
                    SET name = $1, updated_at = $2
                    WHERE job_id = $3 AND user_id = $4
                    RETURNING session_id, job_id, user_id, name, status, metadata,
                              created_at, updated_at
                    """
                    result = await conn.fetchrow(query, name, datetime.now(), job_id, user_id)
                else:
                    query = """
                    UPDATE chat_sessions
                    SET name = $1, updated_at = $2
                    WHERE job_id = $3
                    RETURNING session_id, job_id, user_id, name, status, metadata,
                              created_at, updated_at
                    """
                    result = await conn.fetchrow(query, name, datetime.now(), job_id)
                
                if result:
                    logger.info(f"任务 {job_id} 的会话名称已更新为: {name}")
                    return True, "会话名称更新成功", self._format_session_data(result)
                else:
                    return False, "更新失败", None
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"更新会话名称失败: {e}")
            return False, f"系统错误: {str(e)}", None
    
    async def update_session_name(
        self,
        session_id: str,
        name: str,
        user_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[dict]]:
        """更新会话名称（根据session_id）"""
        try:
            # 验证输入
            if not session_id or not session_id.strip():
                return False, "会话ID不能为空", None
            
            if not name or not name.strip():
                return False, "会话名称不能为空", None
            
            name = name.strip()
            
            # 检查名称长度
            if len(name) > 255:
                return False, "会话名称不能超过255个字符", None
            
            # 检查会话是否存在
            session = await self.get_session_by_id(session_id)
            if not session:
                return False, "会话不存在", None
            
            # 如果提供了user_id，验证权限
            if user_id and session['user_id'] != user_id:
                return False, "无权修改此会话", None
            
            # 更新会话名称
            query = """
            UPDATE chat_sessions
            SET name = $1, updated_at = $2
            WHERE session_id = $3
            RETURNING session_id, job_id, user_id, name, status, metadata,
                      created_at, updated_at
            """
            
            conn = await DatabaseConnection.get_connection()
            try:
                result = await conn.fetchrow(query, name, datetime.now(), session_id)
                
                if result:
                    logger.info(f"会话 {session_id} 名称已更新为: {name}")
                    return True, "会话名称更新成功", self._format_session_data(result)
                else:
                    return False, "更新失败", None
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"更新会话名称失败: {e}")
            return False, f"系统错误: {str(e)}", None
    
    async def delete_session_by_job_id(
        self,
        job_id: str,
        user_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """根据任务ID删除会话及相关数据（级联删除）"""
        start_time = time.time()
        
        try:
            # 验证输入
            if not job_id or not job_id.strip():
                return False, "任务ID不能为空"
            
            # 检查会话是否存在
            session = await self.get_session_by_job_id(job_id, user_id)
            if not session:
                return False, "会话不存在或无权访问"
            
            conn = await DatabaseConnection.get_connection()
            try:
                # 开始事务
                async with conn.transaction():
                    deleted_counts = {}
                    
                    # 按正确的依赖顺序删除（先删除子表，再删除父表）
                    
                    # 1. 删除聊天消息
                    result = await conn.execute(
                        "DELETE FROM chat_messages WHERE session_id IN (SELECT session_id FROM chat_sessions WHERE job_id = $1)",
                        job_id
                    )
                    deleted_counts['chat_messages'] = int(result.split()[-1])
                    
                    # 2. 删除引用subgraphs的子表
                    result = await conn.execute(
                        "DELETE FROM features WHERE subgraph_id IN (SELECT subgraph_id FROM subgraphs WHERE job_id = $1)",
                        job_id
                    )
                    deleted_counts['features'] = int(result.split()[-1])
                    
                    result = await conn.execute(
                        "DELETE FROM processing_cost_calculation_details WHERE subgraph_id IN (SELECT subgraph_id FROM subgraphs WHERE job_id = $1)",
                        job_id
                    )
                    deleted_counts['processing_cost_calculation_details'] = int(result.split()[-1])
                    
                    # 3. 删除子图数据
                    result = await conn.execute("DELETE FROM subgraphs WHERE job_id = $1", job_id)
                    deleted_counts['subgraphs'] = int(result.split()[-1])
                    
                    # 4-16. 删除其他表
                    tables = [
                        'job_price_snapshots', 'job_process_snapshots', 'operation_logs',
                        'price_histories', 'recalculations', 'batch_recalculations',
                        'process_changes', 'nc_calculations', 'user_interactions',
                        'report_summary', 'reports', 'archives'
                    ]
                    
                    for table in tables:
                        result = await conn.execute(f"DELETE FROM {table} WHERE job_id = $1", job_id)
                        deleted_counts[table] = int(result.split()[-1])
                    
                    # 删除audit_logs
                    result = await conn.execute(
                        "DELETE FROM audit_logs WHERE resource_type = 'job' AND resource_id = $1",
                        job_id
                    )
                    deleted_counts['audit_logs'] = int(result.split()[-1])
                    
                    # 17. 删除任务主表
                    result = await conn.execute("DELETE FROM jobs WHERE job_id = $1", job_id)
                    deleted_counts['jobs'] = int(result.split()[-1])
                    
                    # 18. 最后删除聊天会话
                    result = await conn.execute("DELETE FROM chat_sessions WHERE job_id = $1", job_id)
                    deleted_counts['chat_sessions'] = int(result.split()[-1])
                
                # 构建统计信息
                total_deleted = sum(deleted_counts.values())
                elapsed = time.time() - start_time
                
                logger.info(f"删除任务 {job_id} 完成，耗时: {elapsed:.3f}秒")
                logger.info(f"删除统计: {deleted_counts}")
                
                if elapsed > 1.0:
                    logger.warning(f"删除操作较慢: {elapsed:.3f}秒, job_id={job_id}")
                
                if deleted_counts.get('chat_sessions', 0) > 0:
                    # 构建删除摘要消息
                    summary_parts = []
                    for table, count in deleted_counts.items():
                        if count > 0:
                            summary_parts.append(f"{table}({count}条)")
                    
                    summary = f"会话删除成功，共删除 {total_deleted} 条记录: " + ", ".join(summary_parts)
                    return True, summary
                else:
                    return False, "删除失败，未找到匹配的记录"
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"删除会话失败: {e}")
            return False, f"系统错误: {str(e)}"
    
    async def delete_session_by_id(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """根据会话ID删除会话及相关数据"""
        start_time = time.time()
        
        try:
            # 验证输入
            if not session_id or not session_id.strip():
                return False, "会话ID不能为空"
            
            # 检查会话是否存在
            session = await self.get_session_by_id(session_id)
            if not session:
                return False, "会话不存在"
            
            # 验证权限
            if user_id and session['user_id'] != user_id:
                return False, "无权删除此会话"
            
            job_id = session['job_id']
            
            conn = await DatabaseConnection.get_connection()
            try:
                # 开始事务
                async with conn.transaction():
                    deleted_counts = {}
                    
                    # 1. 删除聊天消息
                    result = await conn.execute("DELETE FROM chat_messages WHERE session_id = $1", session_id)
                    deleted_counts['chat_messages'] = int(result.split()[-1])
                    
                    # 2. 删除引用subgraphs的子表
                    result = await conn.execute(
                        "DELETE FROM features WHERE subgraph_id IN (SELECT subgraph_id FROM subgraphs WHERE job_id = $1)",
                        job_id
                    )
                    deleted_counts['features'] = int(result.split()[-1])
                    
                    result = await conn.execute(
                        "DELETE FROM processing_cost_calculation_details WHERE subgraph_id IN (SELECT subgraph_id FROM subgraphs WHERE job_id = $1)",
                        job_id
                    )
                    deleted_counts['processing_cost_calculation_details'] = int(result.split()[-1])
                    
                    # 3. 删除子图数据
                    result = await conn.execute("DELETE FROM subgraphs WHERE job_id = $1", job_id)
                    deleted_counts['subgraphs'] = int(result.split()[-1])
                    
                    # 4-16. 删除其他表
                    tables = [
                        'job_price_snapshots', 'job_process_snapshots', 'operation_logs',
                        'price_histories', 'recalculations', 'batch_recalculations',
                        'process_changes', 'nc_calculations', 'user_interactions',
                        'report_summary', 'reports', 'archives'
                    ]
                    
                    for table in tables:
                        result = await conn.execute(f"DELETE FROM {table} WHERE job_id = $1", job_id)
                        deleted_counts[table] = int(result.split()[-1])
                    
                    # 删除audit_logs
                    result = await conn.execute(
                        "DELETE FROM audit_logs WHERE resource_type = 'job' AND resource_id = $1",
                        job_id
                    )
                    deleted_counts['audit_logs'] = int(result.split()[-1])
                    
                    # 17. 删除任务主表
                    result = await conn.execute("DELETE FROM jobs WHERE job_id = $1", job_id)
                    deleted_counts['jobs'] = int(result.split()[-1])
                    
                    # 18. 最后删除聊天会话
                    result = await conn.execute("DELETE FROM chat_sessions WHERE session_id = $1", session_id)
                    deleted_counts['chat_sessions'] = int(result.split()[-1])
                
                # 构建统计信息
                total_deleted = sum(deleted_counts.values())
                elapsed = time.time() - start_time
                
                logger.info(f"删除会话 {session_id} (任务 {job_id}) 完成，耗时: {elapsed:.3f}秒")
                logger.info(f"删除统计: {deleted_counts}")
                
                if elapsed > 1.0:
                    logger.warning(f"删除操作较慢: {elapsed:.3f}秒, session_id={session_id}")
                
                if deleted_counts.get('chat_sessions', 0) > 0:
                    # 构建删除摘要消息
                    summary_parts = []
                    for table, count in deleted_counts.items():
                        if count > 0:
                            summary_parts.append(f"{table}({count}条)")
                    
                    summary = f"会话删除成功，共删除 {total_deleted} 条记录: " + ", ".join(summary_parts)
                    return True, summary
                else:
                    return False, "删除失败，未找到匹配的记录"
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"删除会话失败: {e}")
            return False, f"系统错误: {str(e)}"
    
    async def delete_sessions_by_job_ids_batch(
        self,
        job_ids: List[str],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """批量删除多个任务的会话及相关数据"""
        start_time = time.time()
        
        try:
            # 验证输入
            if not job_ids:
                return {
                    'total': 0,
                    'success_count': 0,
                    'failed_count': 0,
                    'total_deleted': 0,
                    'elapsed_seconds': 0,
                    'results': []
                }
            
            conn = await DatabaseConnection.get_connection()
            try:
                # 如果提供了user_id，先验证权限
                if user_id:
                    placeholders = ','.join([f'${i+1}' for i in range(len(job_ids))])
                    check_query = f"""
                    SELECT job_id, session_id
                    FROM chat_sessions
                    WHERE job_id IN ({placeholders}) AND user_id = ${len(job_ids)+1}
                    """
                    valid_sessions = await conn.fetch(check_query, *job_ids, user_id)
                    
                    if not valid_sessions:
                        return {
                            'total': len(job_ids),
                            'success_count': 0,
                            'failed_count': len(job_ids),
                            'total_deleted': 0,
                            'elapsed_seconds': round(time.time() - start_time, 3),
                            'results': [
                                {
                                    'job_id': jid,
                                    'success': False,
                                    'message': '会话不存在或无权访问',
                                    'deleted_count': 0
                                }
                                for jid in job_ids
                            ]
                        }
                    
                    valid_job_ids = [row['job_id'] for row in valid_sessions]
                    invalid_job_ids = set(job_ids) - set(valid_job_ids)
                else:
                    valid_job_ids = job_ids
                    invalid_job_ids = set()
                
                # 批量删除
                async with conn.transaction():
                    placeholders = ','.join([f'${i+1}' for i in range(len(valid_job_ids))])
                    deleted_counts = {}
                    
                    # 1. 删除聊天消息
                    result = await conn.execute(
                        f"DELETE FROM chat_messages WHERE session_id IN (SELECT session_id FROM chat_sessions WHERE job_id IN ({placeholders}))",
                        *valid_job_ids
                    )
                    deleted_counts['chat_messages'] = int(result.split()[-1])
                    
                    # 2. 删除引用subgraphs的子表
                    result = await conn.execute(
                        f"DELETE FROM features WHERE subgraph_id IN (SELECT subgraph_id FROM subgraphs WHERE job_id IN ({placeholders}))",
                        *valid_job_ids
                    )
                    deleted_counts['features'] = int(result.split()[-1])
                    
                    result = await conn.execute(
                        f"DELETE FROM processing_cost_calculation_details WHERE subgraph_id IN (SELECT subgraph_id FROM subgraphs WHERE job_id IN ({placeholders}))",
                        *valid_job_ids
                    )
                    deleted_counts['processing_cost_calculation_details'] = int(result.split()[-1])
                    
                    # 3. 删除子图数据
                    result = await conn.execute(f"DELETE FROM subgraphs WHERE job_id IN ({placeholders})", *valid_job_ids)
                    deleted_counts['subgraphs'] = int(result.split()[-1])
                    
                    # 4-16. 删除其他表
                    tables = [
                        'job_price_snapshots', 'job_process_snapshots', 'operation_logs',
                        'price_histories', 'recalculations', 'batch_recalculations',
                        'process_changes', 'nc_calculations', 'user_interactions',
                        'report_summary', 'reports', 'archives'
                    ]
                    
                    for table in tables:
                        result = await conn.execute(f"DELETE FROM {table} WHERE job_id IN ({placeholders})", *valid_job_ids)
                        deleted_counts[table] = int(result.split()[-1])
                    
                    # 删除audit_logs
                    result = await conn.execute(
                        f"DELETE FROM audit_logs WHERE resource_type = 'job' AND resource_id IN ({placeholders})",
                        *valid_job_ids
                    )
                    deleted_counts['audit_logs'] = int(result.split()[-1])
                    
                    # 17. 删除任务主表
                    result = await conn.execute(f"DELETE FROM jobs WHERE job_id IN ({placeholders})", *valid_job_ids)
                    deleted_counts['jobs'] = int(result.split()[-1])
                    
                    # 18. 最后删除聊天会话
                    result = await conn.execute(f"DELETE FROM chat_sessions WHERE job_id IN ({placeholders})", *valid_job_ids)
                    deleted_counts['chat_sessions'] = int(result.split()[-1])
                
                total_deleted = sum(deleted_counts.values())
                elapsed = time.time() - start_time
                
                logger.info(f"批量删除 {len(valid_job_ids)} 个任务完成，耗时: {elapsed:.3f}秒")
                logger.info(f"删除统计: {deleted_counts}")
                
                # 构建结果
                results = []
                for job_id in valid_job_ids:
                    results.append({
                        'job_id': job_id,
                        'success': True,
                        'message': '删除成功',
                        'deleted_count': total_deleted // len(valid_job_ids)
                    })
                
                for job_id in invalid_job_ids:
                    results.append({
                        'job_id': job_id,
                        'success': False,
                        'message': '会话不存在或无权访问',
                        'deleted_count': 0
                    })
                
                return {
                    'total': len(job_ids),
                    'success_count': len(valid_job_ids),
                    'failed_count': len(invalid_job_ids),
                    'total_deleted': total_deleted,
                    'elapsed_seconds': round(elapsed, 3),
                    'results': results
                }
            finally:
                await conn.close()
                
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"批量删除失败: {e}")
            return {
                'total': len(job_ids),
                'success_count': 0,
                'failed_count': len(job_ids),
                'total_deleted': 0,
                'elapsed_seconds': round(elapsed, 3),
                'results': [
                    {
                        'job_id': jid,
                        'success': False,
                        'message': f'系统错误: {str(e)}',
                        'deleted_count': 0
                    }
                    for jid in job_ids
                ]
            }
    
    async def get_user_sessions(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[dict], int]:
        """获取用户的会话列表"""
        try:
            # 构建查询条件
            conditions = ["user_id = $1"]
            params = [user_id]
            param_index = 2
            
            if status:
                conditions.append(f"status = ${param_index}")
                params.append(status)
                param_index += 1
            
            where_clause = " AND ".join(conditions)
            
            conn = await DatabaseConnection.get_connection()
            try:
                # 查询总数
                count_query = f"""
                SELECT COUNT(*) as total
                FROM chat_sessions
                WHERE {where_clause}
                """
                count_result = await conn.fetchrow(count_query, *params)
                total = count_result['total'] if count_result else 0
                
                # 查询列表
                query = f"""
                SELECT session_id, job_id, user_id, name, status, metadata,
                       created_at, updated_at
                FROM chat_sessions
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_index} OFFSET ${param_index + 1}
                """
                params.extend([limit, offset])
                
                results = await conn.fetch(query, *params)
                sessions = [self._format_session_data(row) for row in results] if results else []
                
                return sessions, total
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"获取用户会话列表失败: {e}")
            raise


# 创建服务实例
chat_session_service = ChatSessionService()
