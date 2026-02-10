# HistorySessions 组件修复实施方案

## 修复步骤

### 步骤1: 更新 useAppStore 添加会话切换状态

**文件**: `src/store/useAppStore.ts`

**修改内容**:

```typescript
interface AppState {
  // ... 现有状态 ...
  
  // 新增：会话切换状态
  isSwitchingSession: boolean
  switchingSessionId: string | null
  
  // ... 现有 actions ...
  
  // 新增：设置会话切换状态
  setIsSwitchingSession: (switching: boolean, sessionId?: string) => void
}

// 在 create 函数中添加初始状态
{
  // ... 现有初始状态 ...
  isSwitchingSession: false,
  switchingSessionId: null,
  
  // ... 现有 actions ...
  
  setIsSwitchingSession: (switching, sessionId) => set({
    isSwitchingSession: switching,
    switchingSessionId: switching ? sessionId || null : null,
  }),
}
```

### 步骤2: 改进 WebSocket 断开连接逻辑

**文件**: `src/services/websocketService.ts`

**修改 disconnect 方法**:

```typescript
disconnect(): void {
  console.log('🔌 主动断开WebSocket连接')
  this.stopHeartbeat()
  this.stopQualityCheck()
  
  if (this.ws) {
    // 清理所有事件监听器
    this.ws.onopen = null
    this.ws.onmessage = null
    this.ws.onclose = null
    this.ws.onerror = null
    
    // 关闭连接
    try {
      this.ws.close(1000, '主动断开连接')
    } catch (error) {
      console.warn('⚠️ 关闭WebSocket时出错:', error)
    }
    
    this.ws = null
  }
  
  this.setStatus('disconnected')
  this.jobId = null
  this.callbacks = {}
  this.reconnectAttempts = 0
  this.resetStats()
  
  console.log('✅ WebSocket连接已完全断开')
}
```

### 步骤3: 优化 HistorySessions 中的 handleSessionClick

**文件**: `src/components/HistorySessions.tsx`

**完整的改进版本**:

```typescript
// 处理会话点击
const handleSessionClick = async (session: SessionItem) => {
  // 如果处于选择模式，切换选择状态
  if (selectionMode) {
    handleToggleSelection(session.session_id)
    return
  }
  
  // 如果正在切换会话，忽略此次点击
  if (isSwitchingSession) {
    console.warn('⚠️ 正在切换会话，请稍候...')
    return
  }
  
  // 如果点击的是当前会话，只切换视图，不重新连接 WebSocket
  if (currentJobId === session.job_id) {
    console.log('📋 点击当前会话，切换到聊天视图')
    setCurrentView('chat')
    if (isMobile) {
      setMobileDrawerVisible(false)
    }
    return
  }
  
  // 标记正在切换会话
  setIsSwitchingSession(true, session.session_id)
  
  try {
    console.log('🔄 开始切换会话:', {
      from: currentJobId,
      to: session.job_id,
      timestamp: new Date().toISOString(),
    })
    
    // 断开当前 WebSocket 连接
    if (websocketService.isConnected()) {
      console.log('🔌 切换会话，断开当前 WebSocket 连接')
      websocketService.disconnect()
      
      // 等待连接完全关闭
      await new Promise(resolve => setTimeout(resolve, 150))
    }
    
    // 切换到新会话
    setCurrentJobId(session.job_id)
    setCurrentView('chat')
    
    // 连接新会话的 WebSocket，标记为从历史会话切换
    try {
      console.log('🔗 连接新会话的 WebSocket:', session.job_id)
      
      // 导入必要的模块
      const { addMessage, setIsTyping } = useAppStore.getState()
      
      await websocketService.connect(session.job_id, {
        onConnected: () => {
          console.log('✅ 新会话 WebSocket 连接成功')
        },
        onCompletionRequest: (jobId, data) => {
          // 处理缺失字段补全请求
          console.log('⚠️ 收到缺失字段补全请求:', data)
          
          // 停止打字状态
          setIsTyping(false)
          
          // 添加缺失字段卡片消息
          addMessage({
            type: 'assistant',
            content: data.message || '数据不完整，需要补全必填字段',
            jobId: jobId,
            missingFieldsData: {
              message: data.message || '数据不完整，需要补全必填字段',
              summary: `发现 ${data.missing_fields?.length || 0} 条记录缺少必填字段`,
              missing_fields: data.missing_fields || [],
              suggestion: data.suggestion,
            },
          })
        },
        onProgress: (jobId, data) => {
          console.log('📊 收到进度消息:', data)
          
          // 检查是否是 review_display_view 类型（显示表格）
          const isReviewDisplayView = (data as any).type === 'review_display_view'
          
          // 检查是否是 completion_request 类型（缺失字段请求）
          const isCompletionRequest = (data as any).type === 'completion_request'
          
          // 检查是否是任务完成
          const isTaskCompleted = data.stage === 'completed' || data.progress === 100
          
          // 如果任务完成，停止打字状态
          if (isTaskCompleted) {
            setIsTyping(false)
          }
          // 如果是显示表格或缺失字段请求，立即停止打字状态
          else if (isReviewDisplayView || isCompletionRequest) {
            setIsTyping(false)
          } else {
            // 其他进度消息才设置打字状态
            setIsTyping(true)
          }
          
          // 添加所有进度消息到聊天区域
          if (isCompletionRequest) {
            // 缺失字段请求类型的特殊处理
            const completionData = (data as any).data
            
            addMessage({
              type: 'assistant',
              content: completionData.message || '数据不完整，需要补全必填字段',
              jobId: jobId,
              missingFieldsData: {
                message: completionData.message || '数据不完整，需要补全必填字段',
                summary: `发现 ${completionData.missing_fields?.length || 0} 条记录缺少必填字段`,
                missing_fields: completionData.missing_fields || [],
                suggestion: completionData.suggestion,
              },
            })
          } else if (isReviewDisplayView) {
            // 显示表格类型的特殊处理
            const messageData = {
              type: 'progress' as const,
              content: '特征识别完成，请检查结果并确认',
              jobId: jobId,
              progressData: {
                stage: 'awaiting_confirm',
                progress: 50,
                message: '特征识别完成，请检查结果并确认',
                type: (data as any).type,
                data: (data as any).data,
              },
            }
            
            addMessage(messageData)
          } else {
            // 普通进度消息
            const messageData = {
              type: 'progress' as const,
              content: data.message || '处理中...',
              jobId: jobId,
              progressData: {
                stage: data.stage,
                progress: data.progress || 0,
                message: data.message || '处理中...',
                details: data.details,
              },
            }
            
            addMessage(messageData)
          }
          
          // ❌ 删除以下代码：不在 onProgress 中调用接口
          // 这些逻辑应该在 ChatInterface 中处理
          /*
          if (data.stage === 'awaiting_confirm') {
            setTimeout(async () => {
              try {
                setIsRefreshing(true)
                await chatService.startReview(jobId)
              } catch (error) {
                console.error('❌ 审核启动失败:', error)
              } finally {
                setIsRefreshing(false)
              }
            }, 500)
          }
          */
        },
        onReviewData: (jobId, data) => {
          console.log('📊 收到审核数据:', data)
          setIsTyping(false)
        },
        onModificationConfirmation: (jobId, data) => {
          console.log('📝 收到修改确认请求:', data)
          addMessage({
            type: 'system',
            content: '请确认以下修改：',
            jobId: jobId,
            modificationData: data,
          } as any)
          setIsTyping(false)
        },
        onReviewCompleted: (jobId, data) => {
          console.log('✅ 审核已完成:', data)
          addMessage({
            type: 'system',
            content: `审核已完成，共应用了 ${data.modifications_count || 0} 项修改`,
            jobId: jobId,
          })
          setIsTyping(false)
        },
        onError: (_, error) => {
          console.error('❌ 新会话 WebSocket 连接失败:', error)
          setIsTyping(false)
        }
      }, undefined, true) // 传入 fromHistorySwitch = true
    } catch (error) {
      console.error('❌ 连接新会话 WebSocket 失败:', error)
    }
    
    if (isMobile) {
      setMobileDrawerVisible(false)
    }
    
    console.log('✅ 会话切换完成:', session.job_id)
  } catch (error) {
    console.error('❌ 切换会话失败:', error)
  } finally {
    // 标记切换完成
    setIsSwitchingSession(false)
  }
}
```

### 步骤4: 创建请求去重工具

**文件**: `src/utils/requestDeduplication.ts`

**新建文件内容**:

```typescript
/**
 * 请求去重工具
 * 防止同一个请求在短时间内被多次调用
 */
class RequestDeduplicator {
  private pendingRequests: Map<string, Promise<any>> = new Map()
  
  /**
   * 执行请求，如果已有相同的请求在进行中，返回该请求的结果
   * @param key 请求的唯一标识
   * @param fn 请求函数
   * @returns 请求结果
   */
  async execute<T>(
    key: string,
    fn: () => Promise<T>
  ): Promise<T> {
    // 如果已有相同的请求在进行中，返回该请求的结果
    if (this.pendingRequests.has(key)) {
      console.log(`⏳ 请求已在进行中，复用结果: ${key}`)
      return this.pendingRequests.get(key)!
    }
    
    // 创建新请求
    const promise = fn()
      .finally(() => {
        // 请求完成后，移除缓存
        this.pendingRequests.delete(key)
        console.log(`✅ 请求完成，清除缓存: ${key}`)
      })
    
    // 缓存请求
    this.pendingRequests.set(key, promise)
    console.log(`📡 开始新请求: ${key}`)
    
    return promise
  }
  
  /**
   * 清除所有缓存的请求
   */
  clear(): void {
    this.pendingRequests.clear()
    console.log('🧹 已清除所有缓存的请求')
  }
  
  /**
   * 获取当前缓存的请求数
   */
  getPendingCount(): number {
    return this.pendingRequests.size
  }
}

export const requestDeduplicator = new RequestDeduplicator()
```

### 步骤5: 更新 chatService 使用请求去重

**文件**: `src/services/chatService.ts`

**修改 startReview 方法**:

```typescript
import { requestDeduplicator } from '../utils/requestDeduplication'

export const chatService = {
  // ... 其他方法 ...
  
  /**
   * 启动审核流程（CAD文件上传后调用）
   * 使用请求去重机制防止重复调用
   */
  async startReview(jobId: string): Promise<any> {
    try {
      console.log('🚀 启动审核流程:', jobId)
      
      // 使用去重机制，防止重复调用
      return await requestDeduplicator.execute(
        `startReview:${jobId}`,
        () => reviewService.startReview(jobId)
      )
    } catch (error: any) {
      console.error('❌ 启动审核失败:', error)
      // 如果是 REVIEW_LOCKED 错误，说明已经在审核中
      if (error.message?.includes('REVIEW_LOCKED') || error.message?.includes('审核中')) {
        console.log('ℹ️ 审核已在进行中，继续等待 WebSocket 推送')
        return // 不抛出错误，让流程继续
      }
      throw error
    }
  },
  
  /**
   * 刷新审核数据
   * 使用请求去重机制防止重复调用
   */
  async refreshReview(jobId: string) {
    try {
      console.log('🔄 刷新审核数据:', jobId)
      
      // 使用去重机制，防止重复调用
      return await requestDeduplicator.execute(
        `refreshReview:${jobId}`,
        () => reviewService.refreshReview(jobId)
      )
    } catch (error: any) {
      console.error('❌ 刷新审核数据失败:', error)
      throw error
    }
  },
  
  // ... 其他方法 ...
}
```

### 步骤6: 在 HistorySessions 中使用新的状态

**文件**: `src/components/HistorySessions.tsx`

**在组件顶部添加**:

```typescript
const { 
  isMobile, 
  setMobileDrawerVisible, 
  currentJobId,
  setCurrentJobId, 
  setCurrentView, 
  setSidebarCollapsed,
  sessions,
  sessionsLoading,
  sessionsTotal,
  hasMoreSessions,
  setSessions,
  addSessions,
  setSessionsLoading,
  deleteSession: deleteSessionFromStore,
  updateSession,
  setIsRefreshing,
  setIsReprocessing,
  isSwitchingSession,  // ✅ 新增
  setIsSwitchingSession,  // ✅ 新增
} = useAppStore()
```

---

## 验证清单

### 代码修改验证

- [ ] 在 `useAppStore.ts` 中添加了 `isSwitchingSession` 和 `switchingSessionId` 状态
- [ ] 在 `useAppStore.ts` 中添加了 `setIsSwitchingSession` action
- [ ] 改进了 `websocketService.ts` 中的 `disconnect()` 方法
- [ ] 优化了 `HistorySessions.tsx` 中的 `handleSessionClick` 方法
- [ ] 创建了 `requestDeduplication.ts` 工具文件
- [ ] 更新了 `chatService.ts` 中的 `startReview` 和 `refreshReview` 方法
- [ ] 在 `HistorySessions.tsx` 中导入了新的状态

### 功能测试

- [ ] 快速连续点击多个会话，只有最后一个会话的 WebSocket 连接成功
- [ ] 切换会话时，前一个会话的 WebSocket 完全断开
- [ ] 没有重复的 `/review/start` 接口调用
- [ ] 没有重复的 `/review/refresh` 接口调用
- [ ] 消息显示正确，没有混乱
- [ ] 在网络延迟情况下，仍然能正确切换会话

### 性能测试

- [ ] 使用浏览器开发者工具监控 WebSocket 连接数
- [ ] 使用浏览器开发者工具监控接口调用次数
- [ ] 使用浏览器开发者工具监控内存使用情况
- [ ] 在 3G 网络下测试，确保没有多个连接同时存在

### 日志验证

- [ ] 查看控制台日志，确认会话切换流程正确
- [ ] 查看控制台日志，确认 WebSocket 连接/断开正确
- [ ] 查看控制台日志，确认接口调用去重正确

---

## 回滚方案

如果修改后出现问题，可以按以下步骤回滚：

1. **恢复 useAppStore.ts** - 移除新增的状态和 action
2. **恢复 websocketService.ts** - 恢复原始的 `disconnect()` 方法
3. **恢复 HistorySessions.tsx** - 恢复原始的 `handleSessionClick` 方法
4. **删除 requestDeduplication.ts** - 删除新建的工具文件
5. **恢复 chatService.ts** - 恢复原始的 `startReview` 和 `refreshReview` 方法

---

## 后续优化

### 短期优化（1-2周）

1. 添加更详细的日志和监控
2. 添加用户提示（例如：加载状态指示器）
3. 添加错误恢复机制

### 中期优化（1个月）

1. 重构 WebSocket 连接管理
2. 优化历史消息加载性能
3. 添加连接质量监控

### 长期优化（3个月）

1. 实现会话预加载
2. 实现会话缓存
3. 实现离线支持

---

## 相关文档

- [HistorySessions 组件连续切换会话接口请求问题分析](./HISTORY_SESSIONS_ANALYSIS.md)
- [WebSocket 服务文档](./docs/WEBSOCKET_INTEGRATION_SUMMARY.md)
- [历史会话集成文档](./docs/WEBSOCKET_HISTORY_MESSAGES.md)
