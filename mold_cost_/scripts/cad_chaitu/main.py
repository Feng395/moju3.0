#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CAD 拆图主处理流程
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple
from loguru import logger
import sys
import ezdxf
from mold_cost.infrastructure.cad.cad_process_runtime import execute_cad_split_process

# 导入板料线集成器
try:
    # 中文说明：板料线算法本体已迁入 src，legacy 入口只保留兼容壳。
    from mold_cost.infrastructure.cad.material_line_integrator import MaterialLineIntegrator
    MATERIAL_LINE_AVAILABLE = True
except ImportError:
    try:
        from mold_cost.infrastructure.cad.material_line_integrator import MaterialLineIntegrator
        MATERIAL_LINE_AVAILABLE = True
    except ImportError:
        MATERIAL_LINE_AVAILABLE = False
        logger.warning("⚠️ 板料线集成模块未找到，板料线功能将被禁用")

try:
    from scripts.feature_recognition.dimension_extractor import extract_dimensions as extract_subgraph_dimensions
except ImportError:
    try:
        from ..feature_recognition.dimension_extractor import extract_dimensions as extract_subgraph_dimensions
    except ImportError:
        try:
            from feature_recognition.dimension_extractor import extract_dimensions as extract_subgraph_dimensions
        except ImportError:
            extract_subgraph_dimensions = None
            logger.warning("⚠️ 子图尺寸提取模块未找到，板料线将回退到估算尺寸")

# 禁用 ezdxf 的日志输出
logging.getLogger('ezdxf').setLevel(logging.WARNING)

# ========== 配置 loguru 日志输出 ==========
# 移除默认的 stderr 输出
logger.remove()

# 添加控制台输出（保留）
logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> - <level>{level:8}</level> - <cyan>{name}</cyan> - {message}")

# 添加文件输出到统一日志目录
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logger.add(
    str(log_dir / "cad_chaitu.log"),
    rotation="00:00",
    retention="30 days",
    compression="zip",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    encoding="utf-8"
)

logger.info("=" * 80)
logger.info("🔧 CAD 拆图模块启动")
logger.info(f"📁 日志文件: {log_dir / 'cad_chaitu.log'}")
logger.info(f"📦 模块路径: {__file__}")
logger.info("=" * 80)

# 使用统一的配置加载模块
from scripts.config_loader import load_config, get_db_config, get_oda_config

# 加载配置
load_config()
db_config = get_db_config()
oda_config = get_oda_config()

# 从配置中获取数据库配置
DB_HOST = db_config['host']
DB_PORT = db_config['port']
DB_NAME = db_config['database']
DB_USER = db_config['user']
DB_PASSWORD = db_config['password']

# 从配置中获取 ODA 配置
ODA_FILE_CONVERTER_PATH = oda_config['oda_file_converter_path']

# 验证必需的配置项
_required_configs = {
    'ODA_FILE_CONVERTER_PATH': ODA_FILE_CONVERTER_PATH,
    'DB_HOST': DB_HOST,
    'DB_PORT': DB_PORT,
    'DB_NAME': DB_NAME,
    'DB_USER': DB_USER,
    'DB_PASSWORD': DB_PASSWORD,
}

_missing_configs = [k for k, v in _required_configs.items() if v is None]
if _missing_configs:
    logger.error(f"❌ 缺少必需的配置项: {', '.join(_missing_configs)}")
    raise ValueError(f"缺少必需的配置项: {', '.join(_missing_configs)}")

logger.info(f"✅ 配置加载完成: ODA={ODA_FILE_CONVERTER_PATH}, DB={DB_HOST}:{DB_PORT}/{DB_NAME}")

# 支持相对导入和绝对导入
try:
    # 尝试相对导入（作为包使用时）
    from .converter import DWGConverter
    from .cad_system import CADAnalysisSystem
    from .database import DatabaseManager
    from .storage import FileStorageManager
    from .utils import extract_model_code_from_source
except ImportError:
    # 绝对导入（直接运行时）
    from converter import DWGConverter
    from cad_system import CADAnalysisSystem
    from database import DatabaseManager
    from storage import FileStorageManager
    from utils import extract_model_code_from_source

from mold_cost.infrastructure.cad.cad_xt_export_runtime import export_xt_from_prt_with_nxopen


# 全局实例
db_manager = None
storage_manager = None
_minio_client = None

def init_managers(minio_client=None):
    """初始化管理器"""
    global db_manager, storage_manager, _minio_client
    
    # 保存 minio_client 引用
    _minio_client = minio_client
    
    # 初始化数据库管理器
    if db_manager is None:
        db_manager = DatabaseManager(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    
    # 初始化存储管理器
    if storage_manager is None:
        storage_manager = FileStorageManager(minio_client=minio_client)
    
    logger.info("✅ 管理器初始化完成")


def _extract_subgraph_lwt_from_dxf(dxf_path: str) -> Optional[Dict[str, float]]:
    """优先从导出的子图DXF自身提取L/W/T"""
    if extract_subgraph_dimensions is None:
        return None

    try:
        doc = ezdxf.readfile(dxf_path)
        length, width, thickness = extract_subgraph_dimensions(doc)
        if length > 0 and width > 0 and thickness > 0:
            return {
                "L": float(length),
                "W": float(width),
                "T": float(thickness),
            }
    except Exception as e:
        logger.debug(f"子图尺寸提取失败: {dxf_path} - {e}")

    return None


def _estimate_subgraph_lwt_from_region(region: Optional[Dict]) -> Optional[Dict[str, float]]:
    """兼容兜底：无法从子图文本提取时，用拆图区域估算一个L/W/T"""
    if not region:
        return None

    bounds = region.get("bounds", {})
    if not bounds:
        return None

    span_x = float(bounds.get("max_x", 0) - bounds.get("min_x", 0))
    span_y = float(bounds.get("max_y", 0) - bounds.get("min_y", 0))
    if span_x <= 0 or span_y <= 0:
        return None

    return {
        "L": max(span_x, span_y),
        "W": min(span_x, span_y),
        "T": 10.0,
    }


def _resolve_subgraph_lwt(dxf_path: str, region: Optional[Dict]) -> Tuple[Optional[Dict[str, float]], str]:
    """解析单个子图用于板料线识别的L/W/T，并返回来源说明"""
    extracted_lwt = _extract_subgraph_lwt_from_dxf(dxf_path)
    if extracted_lwt:
        return extracted_lwt, "subgraph_dxf_text"

    estimated_lwt = _estimate_subgraph_lwt_from_region(region)
    if estimated_lwt:
        return estimated_lwt, "region_bounds_fallback"

    return None, "unavailable"


def _save_material_line_debug_files(job_id: str, export_files: list) -> Optional[str]:
    """临时保存加完板料线的子图，便于人工核查。"""
    if not export_files:
        return None

    debug_root = Path(__file__).parent.parent.parent / "temp" / "material_line_debug" / job_id
    debug_root.mkdir(parents=True, exist_ok=True)

    saved_count = 0
    for file_info in export_files:
        local_path = file_info.get("local_path")
        sub_code = file_info.get("sub_code")
        if not local_path or not os.path.exists(local_path) or not sub_code:
            continue

        target_path = debug_root / f"{sub_code}.dxf"
        shutil.copy2(local_path, target_path)
        saved_count += 1

    if saved_count == 0:
        return None

    logger.info(f"📁 已临时保存 {saved_count} 个板料线子图: {debug_root}")
    return str(debug_root)


async def chaitu_process(dwg_url: Optional[str], job_id: str, minio_client=None) -> Dict:
    """
    拆图处理函数
    
    Args:
        dwg_url: DWG 文件的 URL 或本地路径（可选，如果不提供则从数据库查询）
        job_id: 任务ID（用于关联数据库和查询 dwg_file_path）
        minio_client: MinIO 客户端实例（可选）
    
    Returns:
        Dict: {
            "status": "ok" | "error",
            "message": str,
            "data": {...} (可选)
        }
    """
    global _minio_client
    
    # 如果传入了 minio_client，使用传入的
    if minio_client is not None:
        _minio_client = minio_client
    
    # 如果还没有 minio_client，尝试从上层导入
    if _minio_client is None:
        try:
            import sys
            # 添加 scripts 目录到路径
            scripts_dir = Path(__file__).parent.parent
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))
            from minio_client import minio_client as imported_client
            _minio_client = imported_client
            logger.info("✅ 成功导入 MinIO 客户端")
        except ImportError as e:
            logger.warning(f"⚠️ 无法导入 MinIO 客户端: {e}")
            _minio_client = None
        except Exception as e:
            logger.warning(f"⚠️ 导入 MinIO 客户端时出错: {e}")
            _minio_client = None
    
    # 初始化管理器
    if db_manager is None or storage_manager is None:
        init_managers(_minio_client)
    
    try:
        # 中文说明：DWG 来源解析、输入准备、分析编排、板料线、上传、`.x_t` 与落库流程均已收口到 src runtime。
        result = await execute_cad_split_process(
            dwg_url=dwg_url,
            job_id=job_id,
            db_manager=db_manager,
            storage_manager=storage_manager,
            minio_client=_minio_client,
            extract_model_code_from_source=extract_model_code_from_source,
            converter_factory=DWGConverter,
            oda_converter_path=ODA_FILE_CONVERTER_PATH,
            analysis_system_factory=CADAnalysisSystem,
            material_line_available=MATERIAL_LINE_AVAILABLE,
            integrator_factory=MaterialLineIntegrator,
            resolve_subgraph_lwt=_resolve_subgraph_lwt,
            save_debug_files=_save_material_line_debug_files,
            export_xt_from_prt=export_xt_from_prt_with_nxopen,
        )
        return result

    except Exception as e:
        logger.error(f"拆图异常: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
