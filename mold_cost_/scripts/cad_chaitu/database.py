#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database helpers for CAD split flow.
"""

import uuid
from typing import Optional

import psycopg2
from psycopg2 import pool
from loguru import logger


class DatabaseManager:
    """Database access wrapper used by the CAD split flow."""

    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.db_pool = None
        self._subgraphs_has_xt_file_url = None
        self.config = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password,
        }
        self.init_pool()

    def init_pool(self) -> bool:
        """Initialize the PostgreSQL connection pool."""
        try:
            self.db_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                **self.config,
            )
            logger.info(
                f"✅ 数据库连接池初始化成功: "
                f"{self.config['host']}:{self.config['port']}/{self.config['database']}"
            )
            return True
        except Exception as e:
            logger.error(f"❌ 数据库连接池初始化失败: {e}")
            return False

    def _parse_job_uuid(self, job_id: str) -> Optional[uuid.UUID]:
        try:
            return uuid.UUID(job_id)
        except (ValueError, AttributeError):
            logger.error(f"❌ job_id 格式错误，不是有效的 UUID: {job_id}")
            return None

    def _check_subgraphs_has_xt_file_url(self, conn) -> bool:
        """Detect whether the current schema already contains subgraphs.xt_file_url."""
        if self._subgraphs_has_xt_file_url is not None:
            return self._subgraphs_has_xt_file_url

        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'subgraphs' AND column_name = 'xt_file_url'
                """
            )
            self._subgraphs_has_xt_file_url = cursor.fetchone() is not None
            if self._subgraphs_has_xt_file_url:
                logger.info("✅ 检测到 subgraphs.xt_file_url 列，启用 .x_t 路径写入")
            else:
                logger.warning("⚠️ 未检测到 subgraphs.xt_file_url 列，跳过 .x_t 路径写入")
            return self._subgraphs_has_xt_file_url
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass

    def get_dwg_file_path(self, job_id: str) -> Optional[str]:
        """Query dwg_file_path from jobs."""
        if not self.db_pool:
            logger.warning("数据库连接池未初始化")
            return None

        job_uuid = self._parse_job_uuid(job_id)
        if not job_uuid:
            return None

        conn = None
        cursor = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT dwg_file_path FROM jobs WHERE job_id = %s", (str(job_uuid),))
            result = cursor.fetchone()

            if result and result[0]:
                logger.info(f"✅ 从数据库查询到 dwg_file_path: {result[0]}")
                return result[0]

            logger.warning(f"⚠️ 未找到 job_id={job_id} 对应的 dwg_file_path")
            return None
        except Exception as e:
            logger.error(f"❌ 从数据库查询 dwg_file_path 失败: {e}")
            return None
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                self.db_pool.putconn(conn)

    def get_prt_file_path(self, job_id: str) -> Optional[str]:
        """Query prt_file_path from jobs."""
        if not self.db_pool:
            logger.warning("数据库连接池未初始化")
            return None

        job_uuid = self._parse_job_uuid(job_id)
        if not job_uuid:
            return None

        conn = None
        cursor = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT prt_file_path FROM jobs WHERE job_id = %s", (str(job_uuid),))
            result = cursor.fetchone()

            if result and result[0]:
                logger.info(f"✅ 从数据库查询到 prt_file_path: {result[0]}")
                return result[0]

            logger.warning(f"⚠️ 未找到 job_id={job_id} 对应的 prt_file_path")
            return None
        except Exception as e:
            logger.error(f"❌ 从数据库查询 prt_file_path 失败: {e}")
            return None
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                self.db_pool.putconn(conn)

    def save_subgraph(
        self,
        sub_code: str,
        file_url: str,
        source_file: str,
        job_id: str,
        part_name: str = None,
        part_code: str = None,
        xt_file_url: str = None,
    ) -> bool:
        """Persist one subgraph row."""
        if not self.db_pool:
            logger.warning("数据库连接池未初始化，跳过数据库保存")
            return False

        job_uuid = self._parse_job_uuid(job_id)
        if not job_uuid:
            logger.warning(f"⚠️ job_id 格式错误，跳过数据库保存: {job_id}")
            return False

        conn = None
        cursor = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            cursor.execute("SELECT job_id FROM jobs WHERE job_id = %s", (str(job_uuid),))
            if not cursor.fetchone():
                logger.warning(f"⚠️ job_id 在 jobs 表中不存在，跳过数据库保存: {job_uuid}")
                return False

            has_xt_file_url = self._check_subgraphs_has_xt_file_url(conn)

            subgraph_id = f"{source_file}_{sub_code}"
            if len(subgraph_id) > 50:
                logger.warning(f"⚠️ subgraph_id 长度超过 50 字符: {len(subgraph_id)} - {subgraph_id}")
                max_source_len = 50 - len(sub_code) - 1
                if max_source_len > 0:
                    subgraph_id = f"{source_file[:max_source_len]}_{sub_code}"
                    logger.info(f"   截断后: {subgraph_id}")
                else:
                    subgraph_id = subgraph_id[:50]
                    logger.warning(f"   强制截断为: {subgraph_id}")

            if not part_name:
                part_name = "未识别"
            if not part_code:
                part_code = sub_code

            if has_xt_file_url:
                insert_sql = """
                    INSERT INTO subgraphs (
                        subgraph_id,
                        job_id,
                        part_name,
                        part_code,
                        subgraph_file_url,
                        xt_file_url,
                        created_at,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (subgraph_id)
                    DO UPDATE SET
                        part_name = EXCLUDED.part_name,
                        part_code = EXCLUDED.part_code,
                        subgraph_file_url = EXCLUDED.subgraph_file_url,
                        xt_file_url = EXCLUDED.xt_file_url,
                        updated_at = NOW()
                """
                params = (subgraph_id, str(job_uuid), part_name, part_code, file_url, xt_file_url)
            else:
                insert_sql = """
                    INSERT INTO subgraphs (
                        subgraph_id,
                        job_id,
                        part_name,
                        part_code,
                        subgraph_file_url,
                        created_at,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (subgraph_id)
                    DO UPDATE SET
                        part_name = EXCLUDED.part_name,
                        part_code = EXCLUDED.part_code,
                        subgraph_file_url = EXCLUDED.subgraph_file_url,
                        updated_at = NOW()
                """
                params = (subgraph_id, str(job_uuid), part_name, part_code, file_url)

            cursor.execute(insert_sql, params)
            conn.commit()

            logger.debug(
                f"子图已保存到数据库: sub_code={sub_code}, 品名={part_name}, 编号={part_code}"
            )
            return True
        except Exception as e:
            logger.error(f"❌ 保存子图信息到数据库失败: {e}")
            logger.error(f"错误详情: {type(e).__name__}: {e}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return False
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                self.db_pool.putconn(conn)
