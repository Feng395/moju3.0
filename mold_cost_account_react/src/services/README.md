# Services 服务层

## 📋 概述

Services 层负责处理所有与后端 API 的通信，包括 HTTP 请求、WebSocket 连接和数据转换。采用 Axios 和 Socket.IO 实现。

## 📁 文件结构

```
services/
├── api.ts                 # Axios 配置和拦截器
├── authService.ts         # 认证服务
├── chatService.ts         # 聊天服务
├── fileService.ts         # 文件服务
├── jobService.ts          # 任务服务
├── websocketService.ts    # WebSocket 服务
└── types.ts               # 类型定义
```

## 🔧 核心服务

### api.ts (API 配置)

**功能**: Axios 实例配置和请求/响应拦截器

**配置**:
```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // Token 过期，跳转登录
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

### authService.ts (认证服务)

**功能**: 用户认证相关操作

**接口**:
```typescript
interface LoginRequest {
  username: string;
  password: string;
}

interface LoginResponse {
  success: boolean;
  token: string;
  user_info: {
    user_id: string;
    username: string;
    role: string;
  };
}

class AuthService {
  // 登录
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await api.post('/api/login', credentials);
    if (response.success) {
      localStorage.setItem('token', response.token);
      localStorage.setItem('user', JSON.stringify(response.user_info));
    }
    return response;
  }

  // 登出
  async logout(): Promise<void> {
    await api.post('/api/logout');
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }

  // 验证 Token
  async verifyToken(): Promise<boolean> {
    try {
      await api.post('/api/verify-token');
      return true;
    } catch {
      return false;
    }
  }

  // 修改密码
  async changePassword(newPassword: string): Promise<void> {
    await api.post('/api/change-password', { new_password: newPassword });
  }

  // 获取当前用户
  getCurrentUser() {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  }

  // 检查是否登录
  isAuthenticated(): boolean {
    return !!localStorage.getItem('token');
  }
}

export default new AuthService();
```

**使用示例**:
```typescript
import authService from '@/services/authService';

// 登录
const handleLogin = async () => {
  try {
    const response = await authService.login({
      username: 'admin',
      password: 'admin123'
    });
    console.log('登录成功:', response);
  } catch (error) {
    console.error('登录失败:', error);
  }
};

// 登出
const handleLogout = async () => {
  await authService.logout();
  navigate('/login');
};
```

### chatService.ts (聊天服务)

**功能**: 聊天消息和会话管理

**接口**:
```typescript
interface SendMessageRequest {
  session_id: string;
  message: string;
  job_id?: string;
}

interface Message {
  id: string;
  type: 'user' | 'ai' | 'system';
  content: string;
  timestamp: Date;
}

class ChatService {
  // 发送消息
  async sendMessage(data: SendMessageRequest): Promise<Message> {
    return await api.post('/api/v1/chat/message', data);
  }

  // 获取会话列表
  async getSessions(userId: string): Promise<Session[]> {
    return await api.get(`/api/chat-sessions?user_id=${userId}`);
  }

  // 获取会话历史
  async getHistory(sessionId: string): Promise<Message[]> {
    return await api.get(`/api/chat-sessions/${sessionId}/history`);
  }

  // 创建会话
  async createSession(name: string): Promise<Session> {
    return await api.post('/api/chat-sessions', { session_name: name });
  }

  // 删除会话
  async deleteSession(sessionId: string): Promise<void> {
    await api.delete(`/api/chat-sessions/${sessionId}`);
  }

  // 更新会话名称
  async updateSessionName(sessionId: string, name: string): Promise<void> {
    await api.put(`/api/chat-sessions/${sessionId}/name`, {
      session_name: name
    });
  }
}

export default new ChatService();
```

**使用示例**:
```typescript
import chatService from '@/services/chatService';

// 发送消息
const sendMessage = async (message: string) => {
  const response = await chatService.sendMessage({
    session_id: sessionId,
    message: message
  });
  setMessages([...messages, response]);
};

// 获取会话列表
const loadSessions = async () => {
  const sessions = await chatService.getSessions(userId);
  setSessions(sessions);
};
```

### fileService.ts (文件服务)

**功能**: 文件上传和下载

**接口**:
```typescript
interface UploadOptions {
  file: File;
  jobId: string;
  onProgress?: (progress: number) => void;
}

class FileService {
  // 上传文件
  async uploadFile(options: UploadOptions): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', options.file);
    formData.append('job_id', options.jobId);

    return await api.post('/api/v1/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (options.onProgress && progressEvent.total) {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          options.onProgress(progress);
        }
      },
    });
  }

  // 获取预签名 URL
  async getPresignedUrl(filePath: string): Promise<string> {
    const response = await api.get('/api/v1/files/presigned-url', {
      params: { file_path: filePath }
    });
    return response.url;
  }

  // 下载文件
  async downloadFile(fileId: string, fileName: string): Promise<void> {
    const response = await api.get(`/api/v1/files/download/${fileId}`, {
      responseType: 'blob'
    });
    
    const url = window.URL.createObjectURL(new Blob([response]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  // 删除文件
  async deleteFile(fileId: string): Promise<void> {
    await api.delete(`/api/v1/files/${fileId}`);
  }
}

export default new FileService();
```

**使用示例**:
```typescript
import fileService from '@/services/fileService';

// 上传文件
const handleUpload = async (file: File) => {
  try {
    const response = await fileService.uploadFile({
      file: file,
      jobId: jobId,
      onProgress: (progress) => {
        setUploadProgress(progress);
      }
    });
    console.log('上传成功:', response);
  } catch (error) {
    console.error('上传失败:', error);
  }
};

// 下载文件
const handleDownload = async (fileId: string, fileName: string) => {
  await fileService.downloadFile(fileId, fileName);
};
```

### jobService.ts (任务服务)

**功能**: 任务管理

**接口**:
```typescript
interface CreateJobRequest {
  job_name: string;
  description?: string;
}

interface Job {
  job_id: string;
  job_name: string;
  status: string;
  progress: number;
  created_at: Date;
  updated_at: Date;
}

class JobService {
  // 创建任务
  async createJob(data: CreateJobRequest): Promise<Job> {
    return await api.post('/api/v1/jobs', data);
  }

  // 获取任务列表
  async getJobs(params?: {
    page?: number;
    page_size?: number;
    status?: string;
  }): Promise<{ jobs: Job[]; total: number }> {
    return await api.get('/api/v1/jobs', { params });
  }

  // 获取任务详情
  async getJob(jobId: string): Promise<Job> {
    return await api.get(`/api/v1/jobs/${jobId}`);
  }

  // 更新任务
  async updateJob(jobId: string, data: Partial<Job>): Promise<Job> {
    return await api.put(`/api/v1/jobs/${jobId}`, data);
  }

  // 删除任务
  async deleteJob(jobId: string): Promise<void> {
    await api.delete(`/api/v1/jobs/${jobId}`);
  }

  // 获取任务进度
  async getJobProgress(jobId: string): Promise<{
    progress: number;
    stage: string;
    message: string;
  }> {
    return await api.get(`/api/v1/jobs/${jobId}/progress`);
  }
}

export default new JobService();
```

**使用示例**:
```typescript
import jobService from '@/services/jobService';

// 创建任务
const createJob = async () => {
  const job = await jobService.createJob({
    job_name: '模具001',
    description: '测试任务'
  });
  setCurrentJob(job);
};

// 获取任务列表
const loadJobs = async () => {
  const { jobs, total } = await jobService.getJobs({
    page: 1,
    page_size: 10,
    status: 'processing'
  });
  setJobs(jobs);
};
```

### websocketService.ts (WebSocket 服务)

**功能**: 实时通信

**接口**:
```typescript
import io, { Socket } from 'socket.io-client';

class WebSocketService {
  private socket: Socket | null = null;

  // 连接
  connect(jobId: string, token: string): void {
    this.socket = io(`ws://localhost:8000/ws/${jobId}`, {
      query: { token },
      transports: ['websocket']
    });

    this.socket.on('connect', () => {
      console.log('WebSocket 连接成功');
    });

    this.socket.on('disconnect', () => {
      console.log('WebSocket 断开连接');
    });
  }

  // 监听消息
  on(event: string, callback: (data: any) => void): void {
    if (this.socket) {
      this.socket.on(event, callback);
    }
  }

  // 发送消息
  emit(event: string, data: any): void {
    if (this.socket) {
      this.socket.emit(event, data);
    }
  }

  // 断开连接
  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }
}

export default new WebSocketService();
```

**使用示例**:
```typescript
import websocketService from '@/services/websocketService';

// 连接 WebSocket
useEffect(() => {
  const token = localStorage.getItem('token');
  if (token && jobId) {
    websocketService.connect(jobId, token);

    // 监听进度更新
    websocketService.on('progress_update', (data) => {
      setProgress(data.progress);
      setStage(data.stage);
    });

    // 监听任务完成
    websocketService.on('job_completed', (data) => {
      message.success('任务完成！');
    });

    return () => {
      websocketService.disconnect();
    };
  }
}, [jobId]);
```

## 🔒 错误处理

### 统一错误处理

```typescript
// api.ts
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.message || '请求失败';
    
    // 显示错误提示
    notification.error({
      message: '错误',
      description: message
    });

    // 特殊状态码处理
    switch (error.response?.status) {
      case 401:
        // 未授权，跳转登录
        window.location.href = '/login';
        break;
      case 403:
        // 无权限
        notification.error({ message: '无权限访问' });
        break;
      case 404:
        // 资源不存在
        notification.error({ message: '资源不存在' });
        break;
      case 500:
        // 服务器错误
        notification.error({ message: '服务器错误' });
        break;
    }

    return Promise.reject(error);
  }
);
```

### 重试机制

```typescript
import axios from 'axios';
import axiosRetry from 'axios-retry';

axiosRetry(api, {
  retries: 3,
  retryDelay: axiosRetry.exponentialDelay,
  retryCondition: (error) => {
    return axiosRetry.isNetworkOrIdempotentRequestError(error) ||
           error.response?.status === 429;
  }
});
```

## 🧪 测试

### 服务测试

```typescript
import { describe, it, expect, vi } from 'vitest';
import authService from './authService';

describe('AuthService', () => {
  it('should login successfully', async () => {
    const response = await authService.login({
      username: 'admin',
      password: 'admin123'
    });
    
    expect(response.success).toBe(true);
    expect(response.token).toBeDefined();
  });

  it('should handle login failure', async () => {
    await expect(
      authService.login({
        username: 'invalid',
        password: 'invalid'
      })
    ).rejects.toThrow();
  });
});
```

## 📚 相关文档

- [Axios 文档](https://axios-http.com/)
- [Socket.IO 文档](https://socket.io/docs/)
- [主项目文档](../../README.md)

## 🤝 贡献指南

1. 遵循 RESTful API 规范
2. 添加完整的类型定义
3. 实现错误处理
4. 编写单元测试
5. 更新文档

## 📞 联系方式

如有问题，请联系前端团队或提交 Issue。
