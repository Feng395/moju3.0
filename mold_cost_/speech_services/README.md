# Speech Services - 语音识别服务

## 📋 概述

语音识别服务基于 CodeWhisper（OpenAI Whisper），为模具成本核算系统提供语音转文字功能。

## 🏗️ 架构

```
speech_services/
├── README.md                 # 本文件
├── main.py                   # 服务主入口
├── start_speech.bat          # Windows 启动脚本
├── start_speech.sh           # Linux/macOS 启动脚本
├── requirements.txt          # Python 依赖
├── config/                   # 配置文件
│   ├── base_config.json      # 基础配置
│   ├── base_dict.json        # 通用术语库
│   └── user_dict.json        # 用户学习词库（自动生成）
├── dictionaries/             # 术语字典
│   └── programmer_terms.json # 程序员术语
└── core/                     # 核心模块
    ├── __init__.py
    ├── transcriber.py        # 转录器
    ├── dict_manager.py       # 字典管理器
    ├── history_manager.py    # 历史管理器
    ├── prompt_engine.py      # 提示词引擎
    └── utils.py              # 工具函数
```

## 🚀 快速开始

### 前置要求

1. **Python 3.8+**
2. **FFmpeg**（音频处理）

```bash
# 检查 FFmpeg
ffmpeg -version

# Windows 安装
winget install ffmpeg

# macOS 安装
brew install ffmpeg

# Ubuntu 安装
sudo apt install ffmpeg
```

### 启动服务

#### Windows

```bash
cd mold_cost_/speech_services
start_speech.bat
```

#### Linux/macOS

```bash
cd mold_cost_/speech_services
chmod +x start_speech.sh
./start_speech.sh
```

#### 手动启动

```bash
cd mold_cost_/speech_services

# 安装依赖（首次）
pip install -r requirements.txt

# 启动服务
python main.py --host 0.0.0.0 --port 8888 --model small
```

### 验证服务

```bash
# 健康检查
curl http://localhost:8888/api/health

# 查看 API 文档
# 浏览器访问：http://localhost:8888/docs
```

## 📡 API 接口

### 1. 转录音频

**POST** `/api/transcribe`

**参数**：
- `file`: 音频文件（必需）
- `model`: 模型大小（可选，默认：small）
- `language`: 语言代码（可选，默认：zh）
- `fix_terms`: 是否修正术语（可选，默认：true）
- `learn`: 是否学习用户习惯（可选，默认：true）

**示例**：
```bash
curl -X POST http://localhost:8888/api/transcribe \
  -F "file=@audio.wav" \
  -F "model=small" \
  -F "language=zh"
```

**响应**：
```json
{
  "success": true,
  "text": "转录的文本内容",
  "language": "zh",
  "corrections": {
    "count": 3,
    "details": [...]
  }
}
```

### 2. 健康检查

**GET** `/api/health`

**响应**：
```json
{
  "status": "healthy",
  "loaded_models": ["small"]
}
```

### 3. 模型列表

**GET** `/api/models`

**响应**：
```json
{
  "models": ["tiny", "base", "small", "medium", "large"],
  "default": "small",
  "loaded": ["small"]
}
```

### 4. WebSocket 实时转录

**WebSocket** `/ws/transcribe`

支持实时流式转录（可选功能）。

## 🔧 配置说明

### 环境变量

在 `mold_cost_/.env` 中配置：

```bash
# 语音识别服务配置
SPEECH_SERVICE_HOST=0.0.0.0
SPEECH_SERVICE_PORT=8888
SPEECH_SERVICE_MODEL=small
```

### 模型选择

| 模型 | 大小 | 速度 | 准确率 | 显存占用 | 适用场景 |
|------|------|------|--------|----------|----------|
| tiny | ~39 MB | 最快 | 较低 | ~1 GB | 快速测试 |
| base | ~74 MB | 很快 | 一般 | ~1-2 GB | 实时应用 |
| small | ~244 MB | 较快 | 较高 | ~2-4 GB | 推荐使用 |
| medium | ~769 MB | 中等 | 高 | ~4-8 GB | 高准确率 |
| large | ~1550 MB | 较慢 | 最高 | ~8-16 GB | 专业场景 |

### 命令行参数

```bash
python main.py [OPTIONS]

选项：
  --host TEXT       服务器绑定地址（默认：0.0.0.0）
  --port INTEGER    服务器端口（默认：8888）
  --model TEXT      Whisper 模型（默认：small）
  --reload          开发模式，代码修改自动重载
  --help            显示帮助信息
```

## 🎯 特色功能

### 1. 术语修正

自动修正程序员术语，覆盖 13+ 大分类，400+ 条规则：

| 说的话 | 普通识别 | CodeWhisper |
|--------|----------|-------------|
| 提PR | "TPR" ❌ | 提PR ✅ |
| MySQL | "my circle" ❌ | MySQL ✅ |
| Redis | "瑞迪斯" ❌ | Redis ✅ |

### 2. 学习功能

系统会学习你的常用术语，持续优化识别准确率。

### 3. 中英文混合

支持中英文混合识别，适合技术对话场景。

## 🧪 测试

### 基础测试

```bash
# 使用 demo 音频测试
curl -X POST http://localhost:8888/api/transcribe \
  -F "file=@test_audio.wav" \
  -F "model=small" \
  -F "language=zh"
```

### 性能测试

```bash
# 测试识别速度
time curl -X POST http://localhost:8888/api/transcribe \
  -F "file=@test_audio.wav"
```

## 🐛 故障排除

### 问题 1：FFmpeg 未找到

**错误**：`FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'`

**解决**：安装 FFmpeg
```bash
# Windows
winget install ffmpeg

# macOS
brew install ffmpeg

# Ubuntu
sudo apt install ffmpeg
```

### 问题 2：端口被占用

**错误**：`OSError: [Errno 98] Address already in use`

**解决**：更换端口或停止占用进程
```bash
# 查看端口占用
# Windows:
netstat -ano | findstr :8888
# Linux/macOS:
lsof -i :8888

# 使用其他端口
python main.py --port 8889
```

### 问题 3：模型下载慢

**解决**：首次运行会下载模型，可能需要几分钟。可以手动下载模型文件放到缓存目录。

### 问题 4：识别准确率低

**解决**：
1. 使用更大的模型（medium 或 large）
2. 在安静环境下录音
3. 调整麦克风音量
4. 添加自定义术语到字典

## 📊 性能优化

### GPU 加速（NVIDIA 显卡）

```bash
# 检查 CUDA 版本
nvidia-smi

# 安装 GPU 版 PyTorch
pip uninstall -y torch torchaudio torchvision
pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cu121
```

### 减少内存占用

```bash
# 使用更小的模型
python main.py --model tiny
```

## 🔗 集成到 API Gateway

语音识别服务已集成到 API Gateway，通过以下路由访问：

- `/api/speech/transcribe` - 转录音频
- `/api/speech/health` - 健康检查
- `/api/speech/models` - 模型列表

API Gateway 会自动转发请求到语音识别服务。

## 📚 相关文档

- [CodeWhisper 原始文档](../../codewhisper/README.md)
- [集成方案](../../CODEWHISPER_INTEGRATION_PLAN.md)
- [快速开始](../../VOICE_INPUT_QUICKSTART.md)

## 📝 维护日志

- 2026-02-27: 初始版本，基于 CodeWhisper 创建
- 支持中文优化和术语修正
- 集成到模具成本核算系统

## 💡 提示

- 首次使用需要下载 Whisper 模型
- 建议在安静环境下使用
- 可以通过字典文件自定义术语
- 支持学习功能，使用越多越准确

## 📞 技术支持

如有问题，请联系技术团队或查看故障排除文档。
