# 前端集成指南 - 语音识别服务

## 📋 概述

本文档说明如何在前端（React/Vue）中集成语音识别服务，实现语音输入功能。

## 🎯 集成目标

1. 支持点击按钮录音
2. 实时显示录音状态
3. 自动发送音频到服务器
4. 显示识别结果
5. 支持术语修正

## 🔧 技术方案

### 方案 1: 使用 MediaRecorder API（推荐）

适用于现代浏览器，支持直接录制音频。

### 方案 2: 使用 RecordRTC 库

适用于需要兼容旧浏览器的场景。

## 📝 实现步骤

### 1. React 实现

#### 安装依赖

```bash
npm install recordrtc
```

#### 创建语音输入组件

```jsx
// components/VoiceInput.jsx
import React, { useState, useRef } from 'react';
import RecordRTC from 'recordrtc';

const VoiceInput = ({ onTranscript }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const recorderRef = useRef(null);
  const streamRef = useRef(null);

  // 开始录音
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const recorder = new RecordRTC(stream, {
        type: 'audio',
        mimeType: 'audio/wav',
        recorderType: RecordRTC.StereoAudioRecorder,
        numberOfAudioChannels: 1,
        desiredSampRate: 16000
      });

      recorder.startRecording();
      recorderRef.current = recorder;
      setIsRecording(true);
    } catch (error) {
      console.error('录音失败:', error);
      alert('无法访问麦克风，请检查权限设置');
    }
  };

  // 停止录音并发送
  const stopRecording = () => {
    if (!recorderRef.current) return;

    recorderRef.current.stopRecording(async () => {
      const blob = recorderRef.current.getBlob();
      
      // 停止麦克风
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }

      setIsRecording(false);
      setIsProcessing(true);

      // 发送到服务器
      await sendAudioToServer(blob);
      
      setIsProcessing(false);
    });
  };

  // 发送音频到服务器
  const sendAudioToServer = async (audioBlob) => {
    const formData = new FormData();
    formData.append('file', audioBlob, 'audio.wav');
    formData.append('model', 'small');
    formData.append('language', 'zh');
    formData.append('fix_terms', 'true');
    formData.append('learn', 'true');

    try {
      const response = await fetch('http://localhost:8888/api/transcribe', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();
      
      if (result.success) {
        // 回调返回识别结果
        onTranscript(result.text, result.corrections);
      } else {
        console.error('识别失败:', result);
        alert('语音识别失败，请重试');
      }
    } catch (error) {
      console.error('请求失败:', error);
      alert('网络错误，请检查服务是否启动');
    }
  };

  return (
    <div className="voice-input">
      <button
        onClick={isRecording ? stopRecording : startRecording}
        disabled={isProcessing}
        className={`voice-button ${isRecording ? 'recording' : ''}`}
      >
        {isProcessing ? (
          <span>🔄 识别中...</span>
        ) : isRecording ? (
          <span>🔴 停止录音</span>
        ) : (
          <span>🎤 开始录音</span>
        )}
      </button>
      
      {isRecording && (
        <div className="recording-indicator">
          <span className="pulse">●</span> 正在录音...
        </div>
      )}
    </div>
  );
};

export default VoiceInput;
```

#### 使用组件

```jsx
// pages/ModificationPage.jsx
import React, { useState } from 'react';
import VoiceInput from '../components/VoiceInput';

const ModificationPage = () => {
  const [inputText, setInputText] = useState('');
  const [corrections, setCorrections] = useState([]);

  const handleTranscript = (text, corrections) => {
    setInputText(text);
    setCorrections(corrections?.details || []);
    
    // 显示修正详情
    if (corrections && corrections.count > 0) {
      console.log(`术语修正: ${corrections.count} 处`);
      corrections.details?.forEach(c => {
        console.log(`  ${c.wrong} → ${c.correct}`);
      });
    }
  };

  return (
    <div className="modification-page">
      <h2>语音修改指令</h2>
      
      {/* 语音输入 */}
      <VoiceInput onTranscript={handleTranscript} />
      
      {/* 文本输入框 */}
      <textarea
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        placeholder="请说出修改指令，例如：将UP01的材质改为Cr12MoV"
        rows={4}
      />
      
      {/* 术语修正提示 */}
      {corrections.length > 0 && (
        <div className="corrections-info">
          <p>✅ 已修正 {corrections.length} 个术语：</p>
          <ul>
            {corrections.map((c, i) => (
              <li key={i}>
                <code>{c.wrong}</code> → <code>{c.correct}</code>
                <span className="category">({c.category})</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {/* 提交按钮 */}
      <button onClick={() => handleSubmit(inputText)}>
        执行修改
      </button>
    </div>
  );
};

export default ModificationPage;
```

#### 样式

```css
/* styles/VoiceInput.css */
.voice-input {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  margin: 20px 0;
}

.voice-button {
  padding: 12px 24px;
  font-size: 16px;
  border: none;
  border-radius: 8px;
  background: #4CAF50;
  color: white;
  cursor: pointer;
  transition: all 0.3s;
}

.voice-button:hover {
  background: #45a049;
}

.voice-button.recording {
  background: #f44336;
  animation: pulse 1.5s infinite;
}

.voice-button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.recording-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #f44336;
  font-weight: bold;
}

.pulse {
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.corrections-info {
  margin: 15px 0;
  padding: 15px;
  background: #e8f5e9;
  border-left: 4px solid #4CAF50;
  border-radius: 4px;
}

.corrections-info ul {
  list-style: none;
  padding: 0;
  margin: 10px 0 0 0;
}

.corrections-info li {
  padding: 5px 0;
  font-family: monospace;
}

.corrections-info code {
  background: #fff;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 14px;
}

.corrections-info .category {
  color: #666;
  font-size: 12px;
  margin-left: 8px;
}
```

### 2. Vue 实现

#### 创建语音输入组件

```vue
<!-- components/VoiceInput.vue -->
<template>
  <div class="voice-input">
    <button
      @click="toggleRecording"
      :disabled="isProcessing"
      :class="['voice-button', { recording: isRecording }]"
    >
      <span v-if="isProcessing">🔄 识别中...</span>
      <span v-else-if="isRecording">🔴 停止录音</span>
      <span v-else>🎤 开始录音</span>
    </button>
    
    <div v-if="isRecording" class="recording-indicator">
      <span class="pulse">●</span> 正在录音...
    </div>
  </div>
</template>

<script>
import RecordRTC from 'recordrtc';

export default {
  name: 'VoiceInput',
  emits: ['transcript'],
  data() {
    return {
      isRecording: false,
      isProcessing: false,
      recorder: null,
      stream: null
    };
  },
  methods: {
    async toggleRecording() {
      if (this.isRecording) {
        this.stopRecording();
      } else {
        await this.startRecording();
      }
    },
    
    async startRecording() {
      try {
        this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        this.recorder = new RecordRTC(this.stream, {
          type: 'audio',
          mimeType: 'audio/wav',
          recorderType: RecordRTC.StereoAudioRecorder,
          numberOfAudioChannels: 1,
          desiredSampRate: 16000
        });
        
        this.recorder.startRecording();
        this.isRecording = true;
      } catch (error) {
        console.error('录音失败:', error);
        alert('无法访问麦克风，请检查权限设置');
      }
    },
    
    stopRecording() {
      if (!this.recorder) return;
      
      this.recorder.stopRecording(async () => {
        const blob = this.recorder.getBlob();
        
        // 停止麦克风
        if (this.stream) {
          this.stream.getTracks().forEach(track => track.stop());
        }
        
        this.isRecording = false;
        this.isProcessing = true;
        
        await this.sendAudioToServer(blob);
        
        this.isProcessing = false;
      });
    },
    
    async sendAudioToServer(audioBlob) {
      const formData = new FormData();
      formData.append('file', audioBlob, 'audio.wav');
      formData.append('model', 'small');
      formData.append('language', 'zh');
      formData.append('fix_terms', 'true');
      formData.append('learn', 'true');
      
      try {
        const response = await fetch('http://localhost:8888/api/transcribe', {
          method: 'POST',
          body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
          this.$emit('transcript', result.text, result.corrections);
        } else {
          console.error('识别失败:', result);
          alert('语音识别失败，请重试');
        }
      } catch (error) {
        console.error('请求失败:', error);
        alert('网络错误，请检查服务是否启动');
      }
    }
  }
};
</script>

<style scoped>
/* 与 React 版本相同的样式 */
</style>
```

#### 使用组件

```vue
<!-- pages/ModificationPage.vue -->
<template>
  <div class="modification-page">
    <h2>语音修改指令</h2>
    
    <!-- 语音输入 -->
    <VoiceInput @transcript="handleTranscript" />
    
    <!-- 文本输入框 -->
    <textarea
      v-model="inputText"
      placeholder="请说出修改指令，例如：将UP01的材质改为Cr12MoV"
      rows="4"
    />
    
    <!-- 术语修正提示 -->
    <div v-if="corrections.length > 0" class="corrections-info">
      <p>✅ 已修正 {{ corrections.length }} 个术语：</p>
      <ul>
        <li v-for="(c, i) in corrections" :key="i">
          <code>{{ c.wrong }}</code> → <code>{{ c.correct }}</code>
          <span class="category">({{ c.category }})</span>
        </li>
      </ul>
    </div>
    
    <!-- 提交按钮 -->
    <button @click="handleSubmit">执行修改</button>
  </div>
</template>

<script>
import VoiceInput from '@/components/VoiceInput.vue';

export default {
  name: 'ModificationPage',
  components: {
    VoiceInput
  },
  data() {
    return {
      inputText: '',
      corrections: []
    };
  },
  methods: {
    handleTranscript(text, corrections) {
      this.inputText = text;
      this.corrections = corrections?.details || [];
      
      if (corrections && corrections.count > 0) {
        console.log(`术语修正: ${corrections.count} 处`);
        corrections.details?.forEach(c => {
          console.log(`  ${c.wrong} → ${c.correct}`);
        });
      }
    },
    
    handleSubmit() {
      // 处理提交逻辑
      console.log('提交修改:', this.inputText);
    }
  }
};
</script>
```

## 🔒 安全考虑

### 1. HTTPS 要求

浏览器要求在 HTTPS 环境下才能访问麦克风（localhost 除外）。

**开发环境**:
```bash
# 使用 localhost
http://localhost:3000
```

**生产环境**:
```bash
# 必须使用 HTTPS
https://your-domain.com
```

### 2. CORS 配置

确保语音服务允许跨域请求：

```python
# main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. 权限请求

在用户首次使用时请求麦克风权限：

```javascript
const requestMicrophonePermission = async () => {
  try {
    await navigator.mediaDevices.getUserMedia({ audio: true });
    return true;
  } catch (error) {
    console.error('麦克风权限被拒绝:', error);
    return false;
  }
};
```

## 📊 性能优化

### 1. 音频压缩

```javascript
const recorder = new RecordRTC(stream, {
  type: 'audio',
  mimeType: 'audio/wav',
  recorderType: RecordRTC.StereoAudioRecorder,
  numberOfAudioChannels: 1,  // 单声道
  desiredSampRate: 16000,     // 16kHz 采样率
  timeSlice: 1000,            // 每秒一个切片
  ondataavailable: (blob) => {
    // 实时处理音频数据
  }
});
```

### 2. 请求优化

```javascript
// 添加超时控制
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 30000);

try {
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
    signal: controller.signal
  });
  clearTimeout(timeoutId);
} catch (error) {
  if (error.name === 'AbortError') {
    alert('请求超时，请重试');
  }
}
```

### 3. 缓存策略

```javascript
// 缓存用户的常用术语
const cachedTerms = localStorage.getItem('user_terms');
if (cachedTerms) {
  // 使用缓存的术语优化提示词
}
```

## 🐛 错误处理

### 常见错误及解决方案

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| NotAllowedError | 用户拒绝麦克风权限 | 提示用户授权 |
| NotFoundError | 未找到麦克风设备 | 检查设备连接 |
| NotReadableError | 麦克风被其他应用占用 | 关闭其他应用 |
| NetworkError | 网络请求失败 | 检查服务状态 |
| TimeoutError | 请求超时 | 增加超时时间 |

### 错误处理示例

```javascript
const handleError = (error) => {
  switch (error.name) {
    case 'NotAllowedError':
      alert('请允许访问麦克风');
      break;
    case 'NotFoundError':
      alert('未检测到麦克风设备');
      break;
    case 'NotReadableError':
      alert('麦克风被占用，请关闭其他应用');
      break;
    default:
      alert(`录音失败: ${error.message}`);
  }
};
```

## 📱 移动端适配

### 1. 触摸事件

```javascript
// 支持长按录音
<button
  onTouchStart={startRecording}
  onTouchEnd={stopRecording}
  onMouseDown={startRecording}
  onMouseUp={stopRecording}
>
  按住说话
</button>
```

### 2. 响应式设计

```css
@media (max-width: 768px) {
  .voice-button {
    width: 100%;
    padding: 16px;
    font-size: 18px;
  }
}
```

## 🎨 UI/UX 建议

### 1. 视觉反馈

- 录音时显示动画效果
- 处理时显示加载状态
- 成功后显示修正详情

### 2. 用户引导

- 首次使用显示教程
- 提供示例指令
- 显示识别结果和修正

### 3. 错误提示

- 清晰的错误信息
- 提供解决建议
- 支持重试操作

## 📞 技术支持

如有问题，请查看：
- [优化指南](MOLD_INDUSTRY_OPTIMIZATION.md)
- [快速参考](QUICK_REFERENCE.md)
- [服务文档](README.md)

---

**版本**: 1.0.0 | **更新**: 2026-02-28
