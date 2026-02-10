# 历史消息加载错误处理

## 问题描述
当从历史会话进入聊天历史时，如果 `/chat/history/{job_id}` 接口请求失败，需要：
1. 不显示 AI 头像和旋转等待图标
2. 显示请求失败的提示
3. 提供重新请求的按钮

## 解决方案

### 1. 状态管理（useAppStore.ts）

#### 新增状态
```typescript
interface AppState {
  // ...
  historyLoadError: string | null  // 历史消息加载错误信息
  // ...
}
```

#### 新增 Action
```typescript
setHistoryLoadError: (error: string | null) => void  // 设置历史消息加载错误
```

#### 修改 loadHistoryMessages
```typescript
loadHistoryMessages: async (sessionId) => {
  try {
    // 设置加载状态，同时清除打字状态和错误信息
    set({ isLoadingHistory: true, isTyping: false, historyLoadError: null })
    
    // ... 加载逻辑
    
  } catch (error) {
    console.error('❌ 加载历史消息失败:', error)
    
    // 保存错误信息
    const errorMessage = error instanceof Error ? error.message : '加载历史消息失败，请重试'
    set({ historyLoadError: errorMessage })
    
    // 加载失败时，清空消息列表
    set({ messages: [] })
  } finally {
    // 清除加载状态
    set({ isLoadingHistory: false })
  }
}
```

### 2. UI 显示（ChatInterface.tsx）

#### 错误提示界面
在消息区域添加错误提示的条件渲染：

```typescript
{isLoadingHistory ? (
  // 显示骨架屏
  <Skeleton />
) : historyLoadError ? (
  // 显示错误提示和重试按钮
  <div style={{ textAlign: 'center' }}>
    <ExclamationCircleOutlined style={{ fontSize: 48, color: token.colorError }} />
    <Typography.Title level={4}>加载历史消息失败</Typography.Title>
    <Text>{historyLoadError}</Text>
    <Button 
      type="primary" 
      icon={<SyncOutlined />}
      onClick={() => {
        if (currentJobId) {
          setHistoryLoadError(null)
          loadHistoryMessages(currentJobId)
        }
      }}
    >
      重新加载
    </Button>
  </div>
) : (
  // 显示正常消息列表
  <MessageList />
)}
```

## 用户体验流程

### 正常流程
1. 用户点击历史会话
2. 显示骨架屏（3条消息的加载动画）
3. 加载成功，显示历史消息

### 错误流程
1. 用户点击历史会话
2. 显示骨架屏（3条消息的加载动画）
3. 加载失败，显示错误提示：
   - 红色错误图标
   - "加载历史消息失败" 标题
   - 具体错误信息
   - "重新加载" 按钮
4. 用户点击"重新加载"按钮
5. 清除错误状态，重新加载历史消息

## 关键改进

### 1. 不显示 AI 头像和旋转图标
- 错误状态下只显示错误提示界面
- 不显示 `<AIAvatar isTyping={true} />` 和 `<LoadingOutlined />`

### 2. 清晰的错误信息
- 显示具体的错误原因（从 Error 对象获取）
- 提供友好的默认错误信息："加载历史消息失败，请重试"

### 3. 便捷的重试机制
- 一键重试按钮
- 点击后自动清除错误状态并重新加载
- 使用 `SyncOutlined` 图标表示刷新操作

## 测试场景

### 场景 1：网络错误
- 断开网络连接
- 点击历史会话
- 应显示："加载历史消息失败，请重试"
- 点击重新加载按钮
- 恢复网络后应成功加载

### 场景 2：服务器错误
- 服务器返回 500 错误
- 应显示具体的错误信息
- 点击重新加载按钮可重试

### 场景 3：权限错误
- Token 过期或无效
- 应显示权限相关的错误信息
- 可能需要重新登录

## 代码位置

### 修改的文件
1. `src/store/useAppStore.ts`
   - 新增 `historyLoadError` 状态
   - 新增 `setHistoryLoadError` action
   - 修改 `loadHistoryMessages` 错误处理

2. `src/components/ChatInterface.tsx`
   - 新增错误提示 UI
   - 添加重试按钮
   - 导入 `ExclamationCircleOutlined` 和 `SyncOutlined`

## 注意事项

1. **错误状态清理**：在重新加载前清除错误状态，避免闪烁
2. **加载状态管理**：确保 `isLoadingHistory` 和 `historyLoadError` 互斥
3. **用户体验**：错误提示应简洁明了，按钮操作应直观
4. **错误日志**：保留 `console.error` 用于调试
