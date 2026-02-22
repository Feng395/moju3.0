# Components 组件库

## 📋 概述

本目录包含模具成本核算系统前端的所有 React 组件，采用 TypeScript 和 Ant Design 构建。

## 📁 组件分类

### 🎨 布局组件

- `Layout.tsx` - 主布局组件
- `Sidebar.tsx` - 侧边栏导航
- `Header.tsx` - 顶部导航栏
- `Footer.tsx` - 页脚组件

### 💬 聊天相关

- `ChatInterface.tsx` - 聊天界面主组件
- `MessageList.tsx` - 消息列表
- `MessageItem.tsx` - 单条消息
- `InputBox.tsx` - 输入框组件
- `TypingIndicator.tsx` - 打字指示器

### 📤 文件处理

- `FileUpload.tsx` - 文件上传组件
- `FileList.tsx` - 文件列表
- `FilePreview.tsx` - 文件预览
- `DragDropZone.tsx` - 拖拽上传区域

### 📊 任务管理

- `JobList.tsx` - 任务列表
- `JobCard.tsx` - 任务卡片
- `JobDetail.tsx` - 任务详情
- `JobStatus.tsx` - 任务状态

### 📈 进度显示

- `ProgressIndicator.tsx` - 进度指示器
- `ProgressBar.tsx` - 进度条
- `StageIndicator.tsx` - 阶段指示器
- `LoadingSpinner.tsx` - 加载动画

### 🎯 交互组件

- `InteractionCards.tsx` - 交互卡片容器
- `ConfirmCard.tsx` - 确认卡片
- `FormCard.tsx` - 表单卡片
- `SelectionCard.tsx` - 选择卡片

### ⚙️ 设置相关

- `Settings.tsx` - 设置页面
- `SettingsPanel.tsx` - 设置面板
- `ThemeSelector.tsx` - 主题选择器
- `LanguageSelector.tsx` - 语言选择器

### 🔔 通知组件

- `NotificationCenter.tsx` - 通知中心
- `Toast.tsx` - 提示消息
- `Alert.tsx` - 警告提示

## 🎨 核心组件详解

### ChatInterface (聊天界面)

**功能**: ChatGPT 风格的对话界面

**Props**:
```typescript
interface ChatInterfaceProps {
  sessionId?: string;
  onSendMessage?: (message: string) => void;
  onFileUpload?: (file: File) => void;
}
```

**使用示例**:
```tsx
import ChatInterface from '@/components/ChatInterface';

function App() {
  return (
    <ChatInterface
      sessionId="session-123"
      onSendMessage={(msg) => console.log(msg)}
      onFileUpload={(file) => console.log(file)}
    />
  );
}
```

**特性**:
- 实时消息显示
- Markdown 渲染
- 代码高亮
- 打字效果
- 滚动到底部

### MessageList (消息列表)

**功能**: 显示聊天消息列表

**Props**:
```typescript
interface MessageListProps {
  messages: Message[];
  loading?: boolean;
  onRetry?: (messageId: string) => void;
}

interface Message {
  id: string;
  type: 'user' | 'ai' | 'system';
  content: string;
  timestamp: Date;
  status?: 'sending' | 'sent' | 'failed';
}
```

**使用示例**:
```tsx
import MessageList from '@/components/MessageList';

const messages = [
  {
    id: '1',
    type: 'user',
    content: '你好',
    timestamp: new Date()
  },
  {
    id: '2',
    type: 'ai',
    content: '你好！有什么可以帮助你的吗？',
    timestamp: new Date()
  }
];

<MessageList messages={messages} />
```

### FileUpload (文件上传)

**功能**: 支持拖拽的文件上传组件

**Props**:
```typescript
interface FileUploadProps {
  accept?: string;
  maxSize?: number;
  multiple?: boolean;
  onUpload: (files: File[]) => void;
  onError?: (error: Error) => void;
}
```

**使用示例**:
```tsx
import FileUpload from '@/components/FileUpload';

<FileUpload
  accept=".dwg,.prt"
  maxSize={100 * 1024 * 1024} // 100MB
  multiple={false}
  onUpload={(files) => handleUpload(files)}
  onError={(error) => console.error(error)}
/>
```

**特性**:
- 拖拽上传
- 文件类型验证
- 文件大小限制
- 上传进度显示
- 错误处理

### ProgressIndicator (进度指示器)

**功能**: 显示任务处理进度

**Props**:
```typescript
interface ProgressIndicatorProps {
  progress: number;
  stage: string;
  message?: string;
  status?: 'processing' | 'completed' | 'failed';
}
```

**使用示例**:
```tsx
import ProgressIndicator from '@/components/ProgressIndicator';

<ProgressIndicator
  progress={50}
  stage="cad_parsing"
  message="正在解析CAD文件..."
  status="processing"
/>
```

**特性**:
- 百分比进度条
- 阶段显示
- 状态图标
- 动画效果

### InteractionCards (交互卡片)

**功能**: 显示需要用户交互的卡片

**Props**:
```typescript
interface InteractionCardsProps {
  interactions: Interaction[];
  onSubmit: (interactionId: string, data: any) => void;
  onCancel?: (interactionId: string) => void;
}

interface Interaction {
  id: string;
  type: 'confirm' | 'form' | 'selection';
  title: string;
  description?: string;
  fields?: FormField[];
  options?: Option[];
}
```

**使用示例**:
```tsx
import InteractionCards from '@/components/InteractionCards';

const interactions = [
  {
    id: '1',
    type: 'confirm',
    title: '确认材料',
    description: '检测到材料为 45#钢，是否正确？'
  },
  {
    id: '2',
    type: 'form',
    title: '补充信息',
    fields: [
      { name: 'quantity', label: '数量', type: 'number' },
      { name: 'material', label: '材料', type: 'select' }
    ]
  }
];

<InteractionCards
  interactions={interactions}
  onSubmit={(id, data) => handleSubmit(id, data)}
/>
```

### JobList (任务列表)

**功能**: 显示任务列表

**Props**:
```typescript
interface JobListProps {
  jobs: Job[];
  loading?: boolean;
  onJobClick?: (jobId: string) => void;
  onRefresh?: () => void;
}

interface Job {
  job_id: string;
  job_name: string;
  status: string;
  progress: number;
  created_at: Date;
  updated_at: Date;
}
```

**使用示例**:
```tsx
import JobList from '@/components/JobList';

<JobList
  jobs={jobs}
  loading={loading}
  onJobClick={(id) => navigate(`/jobs/${id}`)}
  onRefresh={() => fetchJobs()}
/>
```

### Settings (设置页面)

**功能**: 系统设置界面

**Props**:
```typescript
interface SettingsProps {
  settings: SystemSettings;
  onSave: (settings: SystemSettings) => void;
}

interface SystemSettings {
  theme: 'light' | 'dark';
  language: 'zh-CN' | 'en-US';
  uploadLimit: number;
  autoSave: boolean;
}
```

**使用示例**:
```tsx
import Settings from '@/components/Settings';

<Settings
  settings={settings}
  onSave={(newSettings) => updateSettings(newSettings)}
/>
```

## 🎨 样式规范

### CSS Modules

```tsx
import styles from './Component.module.css';

<div className={styles.container}>
  <h1 className={styles.title}>标题</h1>
</div>
```

### Ant Design 主题

```tsx
import { ConfigProvider } from 'antd';

<ConfigProvider
  theme={{
    token: {
      colorPrimary: '#00b96b',
      borderRadius: 8,
    },
  }}
>
  <App />
</ConfigProvider>
```

### 响应式设计

```css
/* 移动端 */
@media (max-width: 768px) {
  .container {
    padding: 10px;
  }
}

/* 平板 */
@media (min-width: 769px) and (max-width: 1024px) {
  .container {
    padding: 20px;
  }
}

/* 桌面 */
@media (min-width: 1025px) {
  .container {
    padding: 30px;
  }
}
```

## 🔧 开发指南

### 创建新组件

```bash
# 创建组件文件
touch src/components/MyComponent.tsx
touch src/components/MyComponent.module.css
```

```tsx
// MyComponent.tsx
import React from 'react';
import styles from './MyComponent.module.css';

interface MyComponentProps {
  title: string;
  onAction?: () => void;
}

const MyComponent: React.FC<MyComponentProps> = ({ title, onAction }) => {
  return (
    <div className={styles.container}>
      <h2>{title}</h2>
      <button onClick={onAction}>操作</button>
    </div>
  );
};

export default MyComponent;
```

### 组件测试

```tsx
// MyComponent.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import MyComponent from './MyComponent';

describe('MyComponent', () => {
  it('renders title', () => {
    render(<MyComponent title="测试标题" />);
    expect(screen.getByText('测试标题')).toBeInTheDocument();
  });

  it('calls onAction when button clicked', () => {
    const handleAction = jest.fn();
    render(<MyComponent title="测试" onAction={handleAction} />);
    
    fireEvent.click(screen.getByText('操作'));
    expect(handleAction).toHaveBeenCalled();
  });
});
```

### 性能优化

```tsx
import React, { memo, useMemo, useCallback } from 'react';

// 使用 memo 避免不必要的重渲染
const MyComponent = memo(({ data }) => {
  // 使用 useMemo 缓存计算结果
  const processedData = useMemo(() => {
    return data.map(item => processItem(item));
  }, [data]);

  // 使用 useCallback 缓存回调函数
  const handleClick = useCallback(() => {
    console.log('clicked');
  }, []);

  return <div onClick={handleClick}>{processedData}</div>;
});
```

## 📚 相关文档

- [React 文档](https://react.dev/)
- [TypeScript 文档](https://www.typescriptlang.org/)
- [Ant Design 文档](https://ant.design/)
- [主项目文档](../../README.md)

## 🤝 贡献指南

1. 遵循组件命名规范
2. 添加 TypeScript 类型定义
3. 编写组件文档
4. 添加单元测试
5. 保持代码简洁

## 📞 联系方式

如有问题，请联系前端团队或提交 Issue。
