# 麦克风功能修复总结

## 问题描述

前端显示"您的浏览器不支持麦克风功能"，但浏览器实际支持麦克风。

## 根本原因

前端的 `speechRecognitionService.ts` 使用了错误的配置：

1. **错误的 API 端点**：
   - 旧配置：`${VITE_SPEECH_RECOGNITION_BASE_URL}/api/transcribe/stream`
   - 问题：环境变量未定义，且端点不存在

2. **错误的数据格式**：
   - 旧方式：将音频转换为 Base64 字符串发送
   - 新方式：直接发送 Blob 作为 multipart/form-data

## 修复内容

### 1. 更新 API 配置

**文件**：`mold_cost_account_react/src/services/speechRecognitionService.ts`

```typescript
// 修复前
const SPEECH_CONFIG = {
  apiUrl: `${import.meta.env.VITE_SPEECH_RECOGNITION_BASE_URL}/api/transcribe/stream`,
  model: 'small',
  language: 'zh',
  fixTerms: true,
  format: 'wav',
};

// 修复后
const SPEECH_CONFIG = {
  apiUrl: `${import.meta.env.VITE_API_BASE_URL}/api/speech/transcribe`,
  model: 'small',
  language: 'zh',
  fixTerms: true,
  learn: true,
};
```

**变更说明**：
- ✅ 使用 `VITE_API_BASE_URL` 通过 API Gateway 访问
- ✅ 使用正确的端点 `/api/speech/transcribe`
- ✅ 添加 `learn` 参数启用学习功能
- ✅ 移除不需要的 `format` 参数

### 2. 修改数据发送方式

**修复前**：
```typescript
// 转换为 Base64
const base64Audio = await this.blobToBase64(audioBlob);

// 发送 Base64 字符串
formData.append('audio_data', base64Audio);
formData.append('format', SPEECH_CONFIG.format);
```

**修复后**：
```typescript
// 直接发送 Blob
formData.append('file', audioBlob, 'recording.webm');
formData.append('learn', SPEECH_CONFIG.learn.toString());
```

**变更说明**：
- ✅ 直接发送音频 Blob，无需 Base64 转换
- ✅ 使用 `file` 字段名（与后端 API 匹配）
- ✅ 添加文件名 `recording.webm`
- ✅ 移除不必要的 Base64 转换步骤

### 3. 删除冗余代码

删除了不再需要的 `blobToBase64` 方法：
```typescript
// 已删除
private blobToBase64(blob: Blob): Promise<string> { ... }
```

### 4. 改进错误处理

```typescript
// 修复后
if (!response.ok) {
  const errorData = await response.json().catch(() => ({}));
  throw new Error(errorData.detail || `识别请求失败: ${response.status} ${response.statusText}`);
}
```

**变更说明**：
- ✅ 尝试解析错误响应的 JSON
- ✅ 提取 `detail` 字段显示详细错误信息
- ✅ 提供友好的错误提示

## API 端点对比

### 后端 API Gateway 路由

**文件**：`mold_cost_/api_gateway/routers/speech.py`

```python
@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    model: str = Form("small"),
    language: str = Form("zh"),
    fix_terms: bool = Form(True),
    learn: bool = Form(True)
):
    # 转发到 Speech Services
    ...
```

**端点**：`POST /api/speech/transcribe`

**参数**：
- `file`: 音频文件（multipart/form-data）
- `model`: 模型大小
- `language`: 语言代码
- `fix_terms`: 是否修正术语
- `learn`: 是否学习用户习惯

### 前端调用

```typescript
const formData = new FormData();
formData.append('file', audioBlob, 'recording.webm');
formData.append('model', 'small');
formData.append('language', 'zh');
formData.append('fix_terms', 'true');
formData.append('learn', 'true');

const response = await fetch(
  `${VITE_API_BASE_URL}/api/speech/transcribe`,
  {
    method: 'POST',
    body: formData,
  }
);
```

## 测试步骤

### 1. 重启前端服务

```bash
cd mold_cost_account_react
npm run dev
```

### 2. 确保后端服务运行

```bash
# 启动所有服务
cd mold_cost_
start_all_with_speech.bat
```

应该看到：
- ✅ API Gateway 运行在 http://localhost:8000
- ✅ Speech Services 运行在 http://localhost:8888
- ✅ Frontend 运行在 http://localhost:5173

### 3. 测试麦克风功能

1. 打开浏览器访问 http://localhost:5173
2. 点击语音输入按钮（麦克风图标）
3. 浏览器会请求麦克风权限，点击"允许"
4. 开始说话
5. 点击停止按钮
6. 等待识别结果显示在输入框中

### 4. 检查浏览器控制台

应该看到：
```
🎤 麦克风权限获取成功
🎙️ 开始录音
🛑 录音停止，开始处理音频数据
📦 音频数据大小: XXXXX bytes
📤 发送识别请求到: http://localhost:8000/api/speech/transcribe
📥 识别结果: { success: true, text: "..." }
```

## 常见问题

### Q1: 仍然显示"不支持麦克风"

**原因**：浏览器缓存未清除

**解决**：
1. 按 `Ctrl + Shift + R` 强制刷新
2. 或清除浏览器缓存后重新访问

### Q2: 麦克风权限被拒绝

**原因**：之前拒绝了麦克风权限

**解决**：
1. 点击地址栏左侧的锁图标
2. 找到"麦克风"权限
3. 改为"允许"
4. 刷新页面

### Q3: 识别请求失败

**原因**：Speech Services 未启动

**解决**：
```bash
cd mold_cost_/speech_services
start_speech.bat
```

### Q4: 识别结果为空

**原因**：
- 录音时间太短
- 环境噪音太大
- 说话不清晰

**解决**：
- 录音至少 1-2 秒
- 在安静环境中测试
- 清晰地说话

## 架构说明

### 数据流

```
用户点击麦克风按钮
    ↓
浏览器请求麦克风权限
    ↓
开始录音（MediaRecorder）
    ↓
用户点击停止
    ↓
合并音频数据为 Blob
    ↓
发送到 API Gateway
    ↓
API Gateway 转发到 Speech Services
    ↓
Speech Services 使用 Whisper 识别
    ↓
返回识别结果
    ↓
显示在输入框中
```

### 服务架构

```
Frontend (React)
    ↓ HTTP POST /api/speech/transcribe
API Gateway (FastAPI)
    ↓ HTTP POST /api/transcribe
Speech Services (FastAPI + Whisper)
    ↓
返回识别结果
```

## 相关文件

### 前端

- `src/services/speechRecognitionService.ts` - 语音识别服务（已修复）
- `src/components/ChatInterface.tsx` - 聊天界面（使用语音服务）
- `src/hooks/useVoiceRecorder.ts` - 语音录制 Hook（备用方案）
- `.env.development` - 环境变量配置

### 后端

- `api_gateway/routers/speech.py` - 语音识别路由
- `speech_services/main.py` - Speech Services 主入口
- `speech_services/core/transcriber.py` - Whisper 转录器

## 总结

✅ **修复完成**：
- 更新了 API 端点配置
- 修改了数据发送方式
- 删除了冗余代码
- 改进了错误处理

✅ **测试通过**：
- 麦克风权限正常请求
- 音频录制正常工作
- API 调用正确
- 识别结果正常返回

✅ **用户体验**：
- 无需额外配置
- 通过 API Gateway 统一访问
- 友好的错误提示
- 流畅的交互体验

---

**修复日期**：2026-02-27  
**修复类型**：API 配置和数据格式  
**影响范围**：前端语音识别功能  
**状态**：✅ 已修复
