/**
 * 语音录制 Hook
 * 
 * 功能：
 * - 录制音频
 * - 调用后端 API 进行语音转文字
 * - 处理录制状态和错误
 * 
 * 作者：集成方案
 * 创建日期：2026-02-27
 */

import { useState, useRef, useCallback } from 'react';
import axios from 'axios';

interface UseVoiceRecorderOptions {
    /** 转录完成回调 */
    onTranscriptionComplete?: (text: string) => void;
    /** 错误回调 */
    onError?: (error: Error) => void;
    /** 录音开始回调 */
    onRecordingStart?: () => void;
    /** 录音停止回调 */
    onRecordingStop?: () => void;
}

interface UseVoiceRecorderReturn {
    /** 是否正在录音 */
    isRecording: boolean;
    /** 是否正在转录 */
    isTranscribing: boolean;
    /** 开始录音 */
    startRecording: () => Promise<void>;
    /** 停止录音 */
    stopRecording: () => void;
    /** 录音时长（秒） */
    recordingDuration: number;
}

export const useVoiceRecorder = (
    options: UseVoiceRecorderOptions = {}
): UseVoiceRecorderReturn => {
    const [isRecording, setIsRecording] = useState(false);
    const [isTranscribing, setIsTranscribing] = useState(false);
    const [recordingDuration, setRecordingDuration] = useState(0);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const durationIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const startTimeRef = useRef<number>(0);

    /**
     * 开始录音
     */
    const startRecording = useCallback(async () => {
        try {
            // 请求麦克风权限
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                }
            });

            // 创建 MediaRecorder
            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus'
            });

            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];
            startTimeRef.current = Date.now();

            // 监听数据可用事件
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            // 监听停止事件
            mediaRecorder.onstop = async () => {
                // 合并音频数据
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });

                // 停止所有音频轨道
                stream.getTracks().forEach(track => track.stop());

                // 清除计时器
                if (durationIntervalRef.current) {
                    clearInterval(durationIntervalRef.current);
                    durationIntervalRef.current = null;
                }

                // 转录音频
                await transcribeAudio(audioBlob);

                // 重置录音时长
                setRecordingDuration(0);
            };

            // 开始录音
            mediaRecorder.start();
            setIsRecording(true);

            // 开始计时
            durationIntervalRef.current = setInterval(() => {
                const duration = Math.floor((Date.now() - startTimeRef.current) / 1000);
                setRecordingDuration(duration);
            }, 1000);

            // 触发回调
            options.onRecordingStart?.();

        } catch (error) {
            console.error('启动录音失败:', error);

            // 处理常见错误
            let errorMessage = '启动录音失败';
            if (error instanceof Error) {
                if (error.name === 'NotAllowedError') {
                    errorMessage = '麦克风权限被拒绝，请在浏览器设置中允许麦克风访问';
                } else if (error.name === 'NotFoundError') {
                    errorMessage = '未找到麦克风设备';
                } else if (error.name === 'NotReadableError') {
                    errorMessage = '麦克风被其他应用占用';
                } else {
                    errorMessage = error.message;
                }
            }

            options.onError?.(new Error(errorMessage));
        }
    }, [options]);

    /**
     * 停止录音
     */
    const stopRecording = useCallback(() => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);

            // 触发回调
            options.onRecordingStop?.();
        }
    }, [isRecording, options]);

    /**
     * 转录音频
     */
    const transcribeAudio = async (audioBlob: Blob) => {
        setIsTranscribing(true);

        try {
            // 构建表单数据
            const formData = new FormData();
            formData.append('file', audioBlob, 'recording.webm');
            formData.append('model', 'small');  // 使用 small 模型平衡速度和准确率
            formData.append('language', 'zh');  // 中文
            formData.append('fix_terms', 'true');  // 启用术语修正
            formData.append('learn', 'true');  // 启用学习功能

            // 发送请求
            const response = await axios.post(
                `${import.meta.env.VITE_API_BASE_URL}/api/speech/transcribe`,
                formData,
                {
                    headers: {
                        'Content-Type': 'multipart/form-data',
                    },
                    timeout: 60000, // 60秒超时
                }
            );

            // 处理响应
            if (response.data.success && response.data.text) {
                options.onTranscriptionComplete?.(response.data.text);
            } else {
                throw new Error('转录结果为空');
            }

        } catch (error) {
            console.error('转录失败:', error);

            // 处理错误
            let errorMessage = '语音识别失败';
            if (axios.isAxiosError(error)) {
                if (error.code === 'ECONNABORTED') {
                    errorMessage = '语音识别超时，请重试';
                } else if (error.response) {
                    errorMessage = error.response.data?.detail || error.response.data?.message || errorMessage;
                } else if (error.request) {
                    errorMessage = '无法连接到语音识别服务';
                }
            } else if (error instanceof Error) {
                errorMessage = error.message;
            }

            options.onError?.(new Error(errorMessage));

        } finally {
            setIsTranscribing(false);
        }
    };

    return {
        isRecording,
        isTranscribing,
        startRecording,
        stopRecording,
        recordingDuration,
    };
};
