"""
语音识别路由
负责转发语音识别请求到 CodeWhisper 服务

作者：集成方案
创建日期：2026-02-27
"""
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
import httpx
import os
from shared.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/speech", tags=["语音识别"])

# 从环境变量获取 Speech Services 服务地址
SPEECH_SERVICE_URL = os.getenv(
    "SPEECH_SERVICE_URL", 
    "http://localhost:8888"
)


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(..., description="音频文件"),
    model: str = Form("small", description="模型大小: tiny/base/small/medium/large"),
    language: str = Form("zh", description="语言代码"),
    fix_terms: bool = Form(True, description="是否修正术语"),
    learn: bool = Form(True, description="是否学习用户习惯")
):
    """
    转录音频文件
    
    参数:
    - file: 音频文件（支持 wav, mp3, m4a, webm, flac, ogg 等格式）
    - model: 模型大小（默认：small）
    - language: 语言代码（默认：zh）
    - fix_terms: 是否修正术语（默认：true）
    - learn: 是否学习用户习惯（默认：true）
    
    返回:
    - success: 是否成功
    - text: 转录文本
    - language: 检测到的语言
    - corrections: 术语修正详情
    """
    logger.info(f"收到语音转录请求: file={file.filename}, model={model}, language={language}")
    
    try:
        # 读取上传的文件
        audio_data = await file.read()
        logger.info(f"音频文件大小: {len(audio_data)} bytes")
        
        # 转发到 CodeWhisper 服务
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {"file": (file.filename, audio_data, file.content_type or "audio/webm")}
            data = {
                "model": model,
                "language": language,
                "fix_terms": str(fix_terms).lower(),
                "learn": str(learn).lower()
            }
            
            logger.info(f"转发请求到 Speech Services: {SPEECH_SERVICE_URL}/api/transcribe")
            
            response = await client.post(
                f"{SPEECH_SERVICE_URL}/api/transcribe",
                files=files,
                data=data
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"转录成功: text_length={len(result.get('text', ''))}")
            
            return JSONResponse(content={
                "success": True,
                "text": result.get("text", ""),
                "language": result.get("language", language),
                "corrections": result.get("corrections", {})
            })
    
    except httpx.HTTPError as e:
        logger.error(f"Speech Services 服务错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"语音识别服务错误: {str(e)}"
        )
    except Exception as e:
        logger.error(f"转录失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"转录失败: {str(e)}"
        )


@router.get("/health")
async def check_speech_service():
    """
    检查 Speech Services 服务健康状态
    
    返回:
    - status: 服务状态
    - service_url: 服务地址
    - loaded_models: 已加载的模型
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{SPEECH_SERVICE_URL}/api/health"
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Speech Services 服务健康检查成功: {result}")
            
            return {
                "status": "healthy",
                "service_url": SPEECH_SERVICE_URL,
                "speech_service_status": result
            }
    except Exception as e:
        logger.error(f"Speech Services 服务不可用: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"语音识别服务不可用: {str(e)}"
        )


@router.get("/models")
async def list_available_models():
    """
    列出可用的语音识别模型
    
    返回:
    - models: 支持的模型列表
    - default: 默认模型
    - loaded: 已加载的模型
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{SPEECH_SERVICE_URL}/api/models"
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        # 返回默认值
        return {
            "models": ["tiny", "base", "small", "medium", "large"],
            "default": "small",
            "loaded": [],
            "error": str(e)
        }
