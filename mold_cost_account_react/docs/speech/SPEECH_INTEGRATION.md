# 前端语音识别集成说明

## 📋 概述

前端通过 API Gateway 访问语音识别服务，无需直接连接 Speech Services。

## 🔧 配置

### 环境变量

**`.env.development`** (开发环境)
```bash
# API Gateway 地址（语音识别通过此地址访问）
VITE_API_BASE_URL=http://localhost:8000
```

**注意**：不需要配置 `VITE_SPEECH_RECOGNITION_BASE_URL`，因为语音识别服务通过 API Gateway 的 `/api/speech/*` 路由访问。

## 🎨 使用语音识别 Hook

### 1. 导入 Hook

```typescript
import { useVoiceRecorder } from '../hooks/useVoiceRecorder';
```

### 2. 在组件中使用

```typescript
const MyComponent = () => {
  const { 
    isRecording,        // 是否正在录音
    isTranscribing,     // 是否正在识别
    startRecording,     // 开始录音
    stopRecording,      // 停止录音
    recordingDuration   // 录音时长（秒）
  } = useVoiceRecorder({
    onTranscriptionComplete: (text) => {
      // 识别完成回调
      console.log('识别结果:', text);
      // 将文本填充到输入框
      setInputText(prev => prev ? `${prev} ${text}` : text);
    },
    onError: (error) => {
      // 错误回调
      console.error('识别错误:', error);
      message.error(error.message);
    },
    onRecordingStart: () => {
      // 录音开始回调（可选）
      console.log('开始录音');
    },
    onRecordingStop: () => {
      // 录音停止回调（可选）
      console.log('停止录音');
    }
  });

  return (
    <button onClick={isRecording ? stopRecording : startRecording}>
      {isRecording ? '停止录音' : '开始录音'}
    </button>
  );
};
```

## 🔗 集成到现有语音按钮

如果你已经有语音输入按钮，只需添加转录逻辑：

```typescript
import { useVoiceRecorder } from '../hooks/useVoiceRecorder';
import { message } from 'antd';

const ChatInput = () => {
  const [inputText, setInputText] = useState('');
  
  // 使用语音识别 Hook
  const { 
    isRecording, 
    isTranscribing, 
    startRecording, 
    stopRecording 
  } = useVoiceRecorder({
    onTranscriptionComplete: (text) => {
      message.success('语音识别完成');
      // 将识别的文本追加到输入框
      setInputText(prev => prev ? `${prev} ${text}` : text);
    },
    onError: (error) => {
      message.error(error.message);
    }
  });

  // 在你现有的语音按钮点击事件中
  const handleVoiceClick = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <div>
      <Input.TextArea
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        placeholder="输入消息..."
      />
      
      {/* 你现有的语音按钮 */}
      <Button
        icon={<AudioOutlined />}
        onClick={handleVoiceClick}
        loading={isTranscribing}
        type={isRecording ? 'primary' : 'default'}
        danger={isRecording}
      >
        {isRecording ? '停止' : '语音'}
      </Button>
    </div>
  );
};
```

## 📡 API 接口

### 转录音频

**POST** `/api/speech/transcribe`

前端通过 API Gateway 访问，Hook 已封装好请求逻辑。

**请求**：
```typescript
const formData = new FormData();
formData.append('file', audioBlob, 'recording.webm');
formData.append('model', 'small');
formData.append('language', 'zh');

const response = await axios.post(
  `${import.meta.env.VITE_API_BASE_URL}/api/speech/transcribe`,
  formData
);
```

**响应**：
```json
{
  "success": true,
  "text": "识别的文本",
  "language": "zh",
  "corrections": {
    "count": 3,
    "details": [...]
  }
}
```

## 🎯 Hook 参数说明

### useVoiceRecorder(options)

**参数**：
```typescript
interface UseVoiceRecorderOptions {
  onTranscriptionComplete?: (text: string) => void;  // 识别完成回调
  onError?: (error: Error) => void;                  // 错误回调
  onRecordingStart?: () => void;                     // 录音开始回调
  onRecordingStop?: () => void;                      // 录音停止回调
}
```

**返回值**：
```typescript
interface UseVoiceRecorderReturn {
  isRecording: boolean;           // 是否正在录音
  isTranscribing: boolean;        // 是否正在识别
  startRecording: () => Promise<void>;  // 开始录音
  stopRecording: () => void;      // 停止录音
  recordingDuration: number;      // 录音时长（秒）
}
```

## 🐛 常见问题

### Q1: 麦克风权限被拒绝

**A**: 在浏览器设置中允许麦克风访问：
- Chrome/Edge：地址栏左侧 → 网站设置 → 麦克风 → 允许
- Firefox：地址栏左侧 → 权限 → 麦克风 → 允许

### Q2: 识别结果为空

**A**: 检查：
1. 录音时间是否太短（至少 1 秒）
2. 麦克风音量是否正常
3. 环境是否太嘈杂

### Q3: 识别速度慢

**A**: 这是正常的，语音识别需要时间处理。可以：
1. 控制录音时长在 30 秒以内
2. 后端可以切换到更小的模型（tiny/base）

### Q4: 无法连接到服务

**A**: 检查：
1. API Gateway 是否运行（http://localhost:8000）
2. Speech Services 是否运行（http://localhost:8888）
3. 网络连接是否正常

## 💡 最佳实践

### 1. 用户体验

```typescript
// 显示录音状态
{isRecording && (
  <div>
    正在录音... {recordingDuration}秒
  </div>
)}

// 显示识别状态
{isTranscribing && (
  <div>
    正在识别，请稍候...
  </div>
)}
```

### 2. 错误处理

```typescript
onError: (error) => {
  // 根据错误类型显示不同提示
  if (error.message.includes('权限')) {
    message.error('请允许麦克风权限');
  } else if (error.message.includes('超时')) {
    message.error('识别超时，请重试');
  } else {
    message.error(`识别失败: ${error.message}`);
  }
}
```

### 3. 禁用状态

```typescript
// 录音或识别时禁用发送按钮
<Button
  disabled={isRecording || isTranscribing}
  onClick={handleSend}
>
  发送
</Button>
```

## 🔗 相关文件

- Hook 实现: `src/hooks/useVoiceRecorder.ts`
- 后端路由: `mold_cost_/api_gateway/routers/speech.py`
- 服务文档: `mold_cost_/speech_services/README.md`

## 📚 技术栈

- React - UI 框架
- TypeScript - 类型安全
- MediaRecorder API - 浏览器录音
- Axios - HTTP 请求
- Ant Design - UI 组件

---

**创建日期**：2026-02-27
**版本**：1.0.0
