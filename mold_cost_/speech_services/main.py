#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Speech Services - 语音识别服务主入口
基于 CodeWhisper (OpenAI Whisper)

提供 REST API 接口供外部调用语音转文字功能

作者：集成方案
创建日期：2026-02-27
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import base64
import torch

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 导入核心模块
from speech_services.core.transcriber import CodeWhisper

# 检测 GPU 可用性
def check_gpu():
    """检测 GPU 是否可用"""
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        gpu_name = torch.cuda.get_device_name(0)
        print(f"✅ GPU 可用: {gpu_name}")
        print(f"   GPU 数量: {gpu_count}")
        print(f"   CUDA 版本: {torch.version.cuda}")
        return True
    else:
        print("⚠️  GPU 不可用，使用 CPU 模式")
        print("   提示：如需启用 GPU 加速，请安装 CUDA 版本的 PyTorch")
        print("   安装命令：pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121")
        return False

# 在启动时检测 GPU
GPU_AVAILABLE = check_gpu()

# 创建 FastAPI 应用
app = FastAPI(
    title="Speech Services API",
    description="语音转文字 API 服务，支持中文优化和术语修正",
    version="1.0.0"
)

# 配置 CORS（允许跨域请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局 Whisper 实例（避免重复加载模型）
whisper_instances = {}


def get_whisper_instance(model_name: str = "small") -> CodeWhisper:
    """获取或创建 Whisper 实例（单例模式）"""
    if model_name not in whisper_instances:
        print(f"🔄 加载模型: {model_name}")
        whisper_instances[model_name] = CodeWhisper(model_name=model_name)
    return whisper_instances[model_name]


@app.get("/")
async def root():
    """API 根路径"""
    return {
        "name": "Speech Services API",
        "version": "1.0.0",
        "status": "running",
        "description": "语音识别服务 - 基于 CodeWhisper",
        "endpoints": {
            "transcribe": "/api/transcribe",
            "health": "/api/health",
            "models": "/api/models",
            "stats": "/api/stats"
        }
    }


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "speech_services",
        "loaded_models": list(whisper_instances.keys()),
        "gpu_available": GPU_AVAILABLE,
        "device": "cuda" if GPU_AVAILABLE else "cpu"
    }


@app.get("/api/models")
async def list_models():
    """列出支持的模型"""
    return {
        "models": ["tiny", "base", "small", "medium", "large"],
        "default": "small",
        "loaded": list(whisper_instances.keys()),
        "descriptions": {
            "tiny": "最快，准确率较低，适合快速测试",
            "base": "很快，准确率一般，适合实时应用",
            "small": "较快，准确率较高，推荐使用",
            "medium": "中等速度，准确率高",
            "large": "较慢，准确率最高，适合专业场景"
        }
    }


@app.post("/api/transcribe")
async def transcribe_audio(
    file: UploadFile = File(..., description="音频文件"),
    model: str = Form("small", description="模型大小: tiny/base/small/medium/large"),
    language: str = Form("zh", description="语言代码，如 zh, en"),
    fix_terms: bool = Form(True, description="是否修正术语"),
    learn: bool = Form(True, description="是否学习用户习惯"),
    verbose: bool = Form(False, description="是否显示详细信息")
):
    """
    转录音频文件
    
    参数:
    - file: 音频文件（支持 wav, mp3, m4a, flac, ogg, webm 等格式）
    - model: 模型大小，可选 tiny/base/small/medium/large（默认：small）
    - language: 语言代码（默认：zh）
    - fix_terms: 是否修正术语（默认：true）
    - learn: 是否学习用户习惯（默认：true）
    - verbose: 是否返回详细信息（默认：false）
    
    返回:
    - success: 是否成功
    - text: 转录文本
    - language: 检测到的语言
    - corrections: 术语修正详情（如果启用）
    - stats: 统计信息（如果启用详细模式）
    """
    temp_file = None
    
    try:
        # 验证模型
        if model not in ["tiny", "base", "small", "medium", "large"]:
            raise HTTPException(status_code=400, detail=f"不支持的模型: {model}")
        
        # 验证文件类型
        allowed_extensions = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"}
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式: {file_ext}。支持的格式: {', '.join(allowed_extensions)}"
            )
        
        # 保存上传的文件到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            temp_file = tmp.name
            content = await file.read()
            tmp.write(content)
        
        print(f"\n{'='*60}")
        print(f"📝 转录请求")
        print(f"{'='*60}")
        print(f"   文件名: {file.filename}")
        print(f"   文件大小: {len(content)} bytes ({len(content)/1024:.2f} KB)")
        print(f"   文件格式: {file_ext}")
        print(f"   模型: {model}")
        print(f"   语言: {language}")
        print(f"   修正术语: {fix_terms}")
        print(f"   学习习惯: {learn}")
        print(f"   详细模式: {verbose}")
        print(f"   临时文件: {temp_file}")
        
        # 检查文件大小
        if len(content) < 1000:  # 小于 1KB
            print(f"\n⚠️  警告：音频文件太小 ({len(content)} bytes)，可能无法识别")
        elif len(content) > 10 * 1024 * 1024:  # 大于 10MB
            print(f"\n⚠️  警告：音频文件较大 ({len(content)/1024/1024:.2f} MB)，处理可能需要较长时间")
        
        # 获取 Whisper 实例
        print(f"\n🔄 加载 Whisper 模型...")
        whisper = get_whisper_instance(model)
        print(f"✅ 模型加载完成")
        
        # 转录
        print(f"\n🎤 开始转录...")
        import time
        start_time = time.time()
        
        result = whisper.transcribe(
            temp_file,
            language=language,
            fix_programmer_terms=fix_terms,
            learn_user_terms=learn,
            verbose=verbose
        )
        
        elapsed_time = time.time() - start_time
        print(f"⏱️  转录耗时: {elapsed_time:.2f} 秒")
        
        # 检查识别结果
        text = result.get("text", "").strip()
        detected_language = result.get("language", language)
        
        print(f"\n📊 转录结果")
        print(f"{'='*60}")
        print(f"   识别文本: {text if text else '(空)'}")
        print(f"   文本长度: {len(text)} 字符")
        print(f"   检测语言: {detected_language}")
        
        if not text:
            print(f"\n⚠️  警告：识别结果为空")
            print(f"{'='*60}")
            print(f"可能原因：")
            print(f"   1. 录音时间太短（建议至少 1-2 秒）")
            print(f"   2. 没有说话或声音太小")
            print(f"   3. 音频格式不正确或损坏")
            print(f"   4. 环境噪音太大")
            print(f"   5. 麦克风权限未授予")
            print(f"\n建议：")
            print(f"   - 检查麦克风是否正常工作")
            print(f"   - 尝试增加录音时长")
            print(f"   - 在安静环境下录音")
            print(f"   - 确保音频文件完整")
            print(f"{'='*60}")
        
        # 构建响应
        response = {
            "success": True,
            "text": text,
            "language": result.get("language", language)
        }
        
        # 添加术语修正信息
        if fix_terms:
            corrections = whisper.dict_manager.get_corrections()
            stats = whisper.get_dict_stats()
            correction_count = stats.get("replacements_made", 0)
            
            print(f"\n🔧 术语修正")
            print(f"{'='*60}")
            print(f"   修正次数: {correction_count}")
            if correction_count > 0 and verbose:
                print(f"   修正详情:")
                for corr in corrections:
                    print(f"      {corr.get('original', '')} → {corr.get('corrected', '')}")
            
            response["corrections"] = {
                "count": correction_count,
                "details": corrections if verbose else []
            }
        
        # 添加详细信息
        if verbose:
            dict_stats = whisper.get_dict_stats()
            response["stats"] = {
                "model": model,
                "file_size": len(content),
                "file_type": file_ext,
                "dict_rules": dict_stats.get("total_rules", 0),
                "processing_time": elapsed_time
            }
            
            print(f"\n📈 详细统计")
            print(f"{'='*60}")
            print(f"   字典规则数: {dict_stats.get('total_rules', 0)}")
            print(f"   处理时间: {elapsed_time:.2f} 秒")
        
        print(f"\n✅ 转录成功")
        print(f"{'='*60}\n")
        
        return JSONResponse(content=response)
    
    except Exception as e:
        print(f"❌ 转录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"转录失败: {str(e)}")
    
    finally:
        # 清理临时文件
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass


@app.post("/api/transcribe/stream")
async def transcribe_stream(
    audio_data: str = Form(..., description="Base64 编码的音频数据"),
    model: str = Form("small", description="模型大小"),
    language: str = Form("zh", description="语言代码"),
    fix_terms: bool = Form(True, description="是否修正术语"),
    format: str = Form("wav", description="音频格式")
):
    """
    转录 Base64 编码的音频流
    
    参数:
    - audio_data: Base64 编码的音频数据（必需）
    - model: 模型大小（默认：small）
    - language: 语言代码（默认：zh）
    - fix_terms: 是否修正术语（默认：true）
    - format: 音频格式（默认：wav）
    
    返回:
    - success: 是否成功
    - text: 转录文本
    - corrections: 术语修正详情
    """
    temp_file = None
    
    try:
        # 解码 Base64 音频数据
        audio_bytes = base64.b64decode(audio_data)
        
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}") as tmp:
            temp_file = tmp.name
            tmp.write(audio_bytes)
        
        # 获取 Whisper 实例
        whisper = get_whisper_instance(model)
        
        # 转录
        result = whisper.transcribe(
            temp_file,
            language=language,
            fix_programmer_terms=fix_terms
        )
        
        # 构建响应
        response = {
            "success": True,
            "text": result.get("text", ""),
            "language": result.get("language", language)
        }
        
        if fix_terms:
            corrections = whisper.dict_manager.get_corrections()
            stats = whisper.get_dict_stats()
            
            response["corrections"] = {
                "count": stats.get("replacements_made", 0),
                "details": corrections
            }
        
        return JSONResponse(content=response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"转录失败: {str(e)}")
    
    finally:
        # 清理临时文件
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass


@app.get("/api/stats")
async def get_stats():
    """获取统计信息"""
    if not whisper_instances:
        return {
            "message": "没有加载的模型",
            "loaded_models": []
        }
    
    # 使用第一个加载的模型获取统计
    whisper = list(whisper_instances.values())[0]
    
    return {
        "loaded_models": list(whisper_instances.keys()),
        "dict_stats": whisper.get_dict_stats(),
        "dict_categories": whisper.get_dict_categories()
    }


@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """
    WebSocket 实时转录接口
    
    客户端发送 JSON 消息：
    {
        "action": "start",  // 开始会话
        "model": "small",
        "language": "zh"
    }
    
    {
        "action": "audio",  // 发送音频数据
        "data": "base64_encoded_audio"
    }
    
    {
        "action": "end"  // 结束会话并转录
    }
    """
    await websocket.accept()
    
    # 会话状态
    session = {
        "model": "small",
        "language": "zh",
        "audio_chunks": [],
        "temp_file": None
    }
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            action = message.get("action")
            
            if action == "start":
                # 开始新会话
                session["model"] = message.get("model", "small")
                session["language"] = message.get("language", "zh")
                session["audio_chunks"] = []
                
                await websocket.send_json({
                    "type": "status",
                    "message": f"会话已开始，模型: {session['model']}"
                })
            
            elif action == "audio":
                # 接收音频数据
                audio_data = message.get("data")
                if audio_data:
                    session["audio_chunks"].append(audio_data)
                    
                    await websocket.send_json({
                        "type": "status",
                        "message": f"已接收音频块 {len(session['audio_chunks'])}"
                    })
            
            elif action == "end":
                # 结束会话并转录
                if not session["audio_chunks"]:
                    await websocket.send_json({
                        "type": "error",
                        "message": "没有音频数据"
                    })
                    continue
                
                try:
                    # 合并所有音频块
                    combined_audio = b"".join([
                        base64.b64decode(chunk)
                        for chunk in session["audio_chunks"]
                    ])
                    
                    # 保存到临时文件
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                        session["temp_file"] = tmp.name
                        tmp.write(combined_audio)
                    
                    # 转录
                    whisper = get_whisper_instance(session["model"])
                    result = whisper.transcribe(
                        session["temp_file"],
                        language=session["language"],
                        fix_programmer_terms=True
                    )
                    
                    # 发送结果
                    corrections = whisper.dict_manager.get_corrections()
                    stats = whisper.get_dict_stats()
                    
                    await websocket.send_json({
                        "type": "result",
                        "text": result.get("text", ""),
                        "language": result.get("language", session["language"]),
                        "corrections": {
                            "count": stats.get("replacements_made", 0),
                            "details": corrections
                        }
                    })
                    
                    # 清理
                    session["audio_chunks"] = []
                    if session["temp_file"] and os.path.exists(session["temp_file"]):
                        os.remove(session["temp_file"])
                        session["temp_file"] = None
                
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"转录失败: {str(e)}"
                    })
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"未知操作: {action}"
                })
    
    except WebSocketDisconnect:
        print("WebSocket 连接已断开")
    except Exception as e:
        print(f"WebSocket 错误: {e}")
    finally:
        # 清理临时文件
        if session.get("temp_file") and os.path.exists(session["temp_file"]):
            try:
                os.remove(session["temp_file"])
            except:
                pass


def main():
    """
    启动 Speech Services API 服务器
    
    支持的命令行参数：
    --host: 服务器绑定地址（默认：0.0.0.0）
    --port: 服务器端口（默认：8888）
    --model: 预加载的模型（默认：small）
    --reload: 开发模式，代码修改自动重载
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Speech Services API Server - 语音转文字 API 服务",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="服务器绑定的 IP 地址 (默认: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8888,
        help="服务器监听的端口号 (默认: 8888)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用开发模式，代码修改后自动重载"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="small",
        choices=["tiny", "base", "small", "medium", "large"],
        help="预加载的 Whisper 模型大小 (默认: small)"
    )
    
    args = parser.parse_args()
    
    # 预加载指定模型
    print(f"🚀 启动 Speech Services API Server")
    print(f"📦 预加载模型: {args.model}")
    whisper = get_whisper_instance(args.model)
    
    # 显示服务器信息
    print(f"\n🌐 服务器配置:")
    print(f"   地址: http://{args.host}:{args.port}")
    print(f"   自动重载: {'启用' if args.reload else '禁用'}")
    print(f"   模型: {args.model}")
    
    print(f"\n📖 访问地址:")
    print(f"   API 文档: http://{args.host}:{args.port}/docs")
    print(f"   交互式文档: http://{args.host}:{args.port}/redoc")
    print(f"   健康检查: http://{args.host}:{args.port}/api/health")
    
    print(f"\n💡 提示: 按 Ctrl+C 停止服务器")
    
    # 启动服务器
    # 注意：直接传递 app 对象，而不是字符串 "main:app"
    uvicorn.run(
        app,  # 直接使用 app 对象
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()
