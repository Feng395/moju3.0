// 语音识别配置 - 使用环境变量
const SPEECH_CONFIG = {
  apiUrl: `${import.meta.env.VITE_API_BASE_URL}/api/speech/transcribe`,
  model: 'small',
  language: 'zh',
  fixTerms: true,
  learn: true,
};

interface SpeechRecognitionCallbacks {
  onStart?: () => void;
  onResult?: (text: string, isFinal: boolean) => void;
  onEnd?: () => void;
  onError?: (error: string) => void;
}

export class SpeechRecognitionService {
  private audioContext: AudioContext | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private mediaStream: MediaStream | null = null;
  private audioChunks: Blob[] = [];
  private isRecording = false;
  private callbacks: SpeechRecognitionCallbacks = {};

  /**
   * 开始录音和识别
   */
  async startRecognition(callbacks: SpeechRecognitionCallbacks): Promise<void> {
    if (this.isRecording) {
      console.warn('已经在录音中');
      return;
    }

    this.callbacks = callbacks;
    this.audioChunks = [];

    try {
      // 1. 获取麦克风权限
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
        }
      });
      console.log('🎤 麦克风权限获取成功');

      // 2. 创建 MediaRecorder
      const options = { mimeType: 'audio/webm' };
      this.mediaRecorder = new MediaRecorder(this.mediaStream, options);

      // 3. 收集音频数据
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      // 4. 录音停止时发送数据
      this.mediaRecorder.onstop = async () => {
        console.log('🛑 录音停止，开始处理音频数据');

        try {
          // 合并音频数据
          const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
          console.log('📦 音频数据大小:', audioBlob.size, 'bytes');

          // 发送到语音识别接口
          await this.sendToRecognitionAPI(audioBlob);

        } catch (error: any) {
          console.error('❌ 处理音频数据失败:', error);
          this.callbacks.onError?.(error.message || '处理音频数据失败');
        }
      };

      // 5. 开始录音
      this.mediaRecorder.start();
      this.isRecording = true;
      console.log('🎙️ 开始录音');
      this.callbacks.onStart?.();

    } catch (error: any) {
      console.error('❌ 启动录音失败:', error);
      this.callbacks.onError?.(error.message || '启动录音失败');
      throw error;
    }
  }

  /**
   * 发送音频数据到识别接口
   */
  private async sendToRecognitionAPI(audioBlob: Blob): Promise<void> {
    try {
      console.log('📤 发送识别请求到:', SPEECH_CONFIG.apiUrl);
      console.log('📦 音频数据大小:', audioBlob.size, 'bytes');
      console.log('📦 音频类型:', audioBlob.type);

      // 构建 FormData
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.webm');
      formData.append('model', SPEECH_CONFIG.model);
      formData.append('language', SPEECH_CONFIG.language);
      formData.append('fix_terms', SPEECH_CONFIG.fixTerms.toString());
      formData.append('learn', SPEECH_CONFIG.learn.toString());

      console.log('📋 请求参数:', {
        model: SPEECH_CONFIG.model,
        language: SPEECH_CONFIG.language,
        fix_terms: SPEECH_CONFIG.fixTerms,
        learn: SPEECH_CONFIG.learn,
      });

      // 发送请求
      const response = await fetch(SPEECH_CONFIG.apiUrl, {
        method: 'POST',
        body: formData,
      });

      console.log('📡 响应状态:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('❌ 服务器返回错误:', errorData);
        throw new Error(errorData.detail || `识别请求失败: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      console.log('📥 识别结果:', result);

      if (result.success && result.text) {
        // 返回最终识别结果
        this.callbacks.onResult?.(result.text, true);
        this.callbacks.onEnd?.();
      } else if (result.success && !result.text) {
        // 识别成功但结果为空
        console.warn('⚠️  识别结果为空');
        const errorMsg = '未识别到语音内容，请确保：\n1. 录音时间至少 1-2 秒\n2. 清晰地说话\n3. 环境安静';
        this.callbacks.onError?.(errorMsg);
      } else {
        // 显示详细的错误信息
        console.error('❌ 识别失败，完整响应:', result);
        const errorMsg = result.message || result.detail || result.error || '识别失败，未返回文本';
        throw new Error(errorMsg);
      }

    } catch (error: any) {
      console.error('❌ 识别请求失败:', error);
      // 显示更详细的错误信息
      let errorMessage = error.message || '识别请求失败';
      if (error.response) {
        errorMessage = `服务器错误: ${error.response.status} - ${error.response.statusText}`;
      }
      this.callbacks.onError?.(errorMessage);
    }
  }

  /**
   * 停止录音和识别
   */
  stopRecognition(): void {
    if (!this.isRecording) {
      return;
    }

    console.log('🛑 停止录音');
    this.isRecording = false;

    // 停止 MediaRecorder
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }

    // 停止媒体流
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }
  }

  /**
   * 检查是否正在录音
   */
  isActive(): boolean {
    return this.isRecording;
  }

  /**
   * 清理资源
   */
  dispose(): void {
    this.stopRecognition();

    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }

    this.mediaRecorder = null;
    this.audioChunks = [];
  }
}

// 导出单例
export const speechRecognitionService = new SpeechRecognitionService();
