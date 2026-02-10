import api from './api'

export interface HistoryMessage {
  message_id: number
  role: 'system' | 'user' | 'assistant'
  content: string
  timestamp: string
  metadata?: Record<string, any>
}

export interface SessionInfo {
  session_id: string
  job_id: string
  user_id: string
  created_at: string
  updated_at: string
  status: 'active' | 'completed' | 'archived'
  metadata?: Record<string, any>
}

export interface ChatHistoryResponse {
  session_id: string
  session_info: SessionInfo
  messages: HistoryMessage[]
  total_count: number
  returned_count: number
  offset: number
  limit: number
  has_more: boolean
}

export interface GetHistoryParams {
  limit?: number
  offset?: number
}

class HistoryService {
  /**
   * 获取聊天历史消息（从数据库）
   * 根据API文档：GET /api/v1/chat/history/{session_id}?limit=100&offset=0
   */
  async getChatHistory(sessionId: string, params: GetHistoryParams = {}): Promise<ChatHistoryResponse> {
    const { limit = 100, offset = 0 } = params
    
    try {
      const response = await api.get(`/chat/history/${sessionId}`, {
        params: {
          limit,
          offset
        },
      })
      
      return response.data
    } catch (error: any) {
      // 处理特定的错误响应
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail
        if (detail === '无效的Token') {
          throw new Error('Token已失效，请重新登录')
        } else if (detail === 'Not authenticated') {
          throw new Error('未认证，请先登录')
        } else if (detail.error === 'SESSION_NOT_FOUND') {
          throw new Error('会话不存在')
        }
      }
      
      console.error('获取聊天历史失败:', error)
      throw error
    }
  }

  /**
   * 获取所有聊天历史消息（分页查询直到获取全部）
   */
  async getAllChatHistory(sessionId: string): Promise<ChatHistoryResponse> {
    const limit = 100
    let offset = 0
    let allMessages: HistoryMessage[] = []
    let sessionInfo: SessionInfo | null = null
    let totalCount = 0
    
    try {
      // 第一次请求
      const firstResponse = await this.getChatHistory(sessionId, { limit, offset })
      allMessages = firstResponse.messages
      sessionInfo = firstResponse.session_info
      totalCount = firstResponse.total_count
      
      // console.log(`📥 加载历史消息 - 第1批: ${firstResponse.returned_count}/${totalCount}`)
      
      // 如果还有更多消息，继续请求
      while (firstResponse.has_more || allMessages.length < totalCount) {
        offset += limit
        
        const response = await this.getChatHistory(sessionId, { limit, offset })
        allMessages = [...allMessages, ...response.messages]
        
        // console.log(`📥 加载历史消息 - 第${Math.floor(offset / limit) + 1}批: ${response.returned_count}/${totalCount}, 累计: ${allMessages.length}`)
        
        // 如果没有更多消息或已获取全部，退出循环
        if (!response.has_more || allMessages.length >= totalCount) {
          break
        }
      }
      
      return {
        session_id: sessionId,
        session_info: sessionInfo!,
        messages: allMessages,
        total_count: totalCount,
        returned_count: allMessages.length,
        offset: 0,
        limit: allMessages.length,
        has_more: false
      }
    } catch (error) {
      console.error('获取所有聊天历史失败:', error)
      throw error
    }
  }

  /**
   * 将API返回的历史消息转换为应用内的消息格式
   */
  convertToAppMessages(historyMessages: HistoryMessage[]): import('../store/useAppStore').Message[] {
    return historyMessages.map((msg, index) => {
      // 检查当前消息是否需要确认，以及下一条消息来判断确认状态
      let confirmationStatus: 'confirmed' | 'cancelled' | undefined = undefined
      
      if (msg.metadata?.requires_confirmation === true) {
        // 获取当前消息的意图类型
        const intent = msg.metadata?.intent
        
        // 查看下一条消息
        const nextMsg = historyMessages[index + 1]
        
        if (nextMsg) {
          // 如果下一条是进度消息（如 feature_recognition_started, pricing_started），说明已确认
          if (nextMsg.role === 'system' && 
              nextMsg.metadata?.message_type === 'progress' &&
              (nextMsg.metadata?.stage?.includes('_started') || 
               nextMsg.metadata?.stage === 'continuing')) {
            confirmationStatus = 'confirmed'
          }
          // 如果下一条是 review_display_view（数据修改确认后的刷新），说明已确认
          else if (nextMsg.role === 'system' && 
                   nextMsg.metadata?.message_type === 'review_display_view') {
            confirmationStatus = 'confirmed'
          }
          // 如果下一条是用户消息，根据意图类型决定是否标记为已取消
          else if (nextMsg.role === 'user') {
            // 重新识别特征和重新计算：标记为已取消
            if (intent === 'FEATURE_RECOGNITION' || intent === 'PRICE_CALCULATION') {
              confirmationStatus = 'cancelled'
            }
            // 确认修改：不标记为已取消（后端会缓存这些修改）
            // DATA_MODIFICATION 不设置 confirmationStatus
          }
        }
        // 如果没有下一条消息，根据意图类型决定是否标记为已取消
        else {
          // 重新识别特征和重新计算：标记为已取消
          if (intent === 'FEATURE_RECOGNITION' || intent === 'PRICE_CALCULATION') {
            confirmationStatus = 'cancelled'
          }
          // 确认修改：不标记为已取消（后端会缓存这些修改）
          // DATA_MODIFICATION 不设置 confirmationStatus
        }
      }
      const baseMessage = {
        id: `history-${msg.message_id || index}`,
        type: this.convertRoleToType(msg.role),
        content: msg.content,
        timestamp: new Date(msg.timestamp),
        jobId: undefined, // 将在调用时设置
        // 添加意图和确认相关字段
        intent: msg.metadata?.intent as any,
        requiresConfirmation: msg.metadata?.requires_confirmation === true ? false : undefined, // 历史消息不显示确认按钮
        intentData: msg.metadata?.data,
        confirmationStatus, // 添加确认状态
      }

      // 检查是否有原始 WebSocket 消息
      const originalWsMessage = msg.metadata?.original_ws_message

      // 处理不同类型的消息
      if (originalWsMessage) {
        // 处理进度消息
        if (originalWsMessage.type === 'progress' && originalWsMessage.data) {
          const progressData = originalWsMessage.data
          
          // 检查是否是审核数据展示消息
          if (progressData.type === 'review_display_view' && progressData.data) {
            return {
              ...baseMessage,
              type: 'system' as const,
              reviewData: progressData.data, // 保存审核数据
            }
          }
          
          // 普通进度消息
          if (progressData.stage) {
            return {
              ...baseMessage,
              type: 'progress' as const,
              progressData: {
                stage: progressData.stage,
                progress: progressData.progress || 0,
                message: progressData.message || msg.content,
                details: progressData.details,
              },
            }
          }
        }
        
        // 处理 review_display_view 类型的 WebSocket 消息
        if (originalWsMessage.type === 'review_display_view' && originalWsMessage.data) {
          return {
            ...baseMessage,
            type: 'system' as const,
            reviewData: originalWsMessage.data, // 保存审核数据
          }
        }
        
        // 处理 completion_request 类型的 WebSocket 消息（缺失字段）
        if (originalWsMessage.type === 'completion_request' && originalWsMessage.data) {
          return {
            ...baseMessage,
            type: 'assistant' as const,
            missingFieldsData: {
              message: originalWsMessage.data.message || '数据不完整，需要补全必填字段',
              summary: `发现 ${originalWsMessage.data.missing_fields?.length || 0} 条记录缺少必填字段`,
              missing_fields: originalWsMessage.data.missing_fields || [],
              suggestion: originalWsMessage.data.suggestion,
            },
          }
        }
        
        // 处理修改确认消息
        if (originalWsMessage.type === 'modification_confirmation') {
          return {
            ...baseMessage,
            type: 'system' as const,
            // 移除 modificationData，因为历史消息不需要显示修改卡片
          }
        }
        
        // 处理操作完成消息
        if (originalWsMessage.type === 'operation_completed') {
          return {
            ...baseMessage,
            type: 'system' as const,
            operationCompleted: {
              action_type: originalWsMessage.action_type,
              result: originalWsMessage.result,
            },
          }
        }
      }
      
      // 处理特殊的 metadata 标记（当没有 original_ws_message 时）
      if (msg.metadata) {
        // 处理 message_type 为 review_display_view 的情况
        if (msg.metadata.message_type === 'review_display_view' && msg.metadata.original_ws_message?.data) {
          return {
            ...baseMessage,
            type: 'system' as const,
            reviewData: msg.metadata.original_ws_message.data, // 保存审核数据
          }
        }
        
        // 处理 message_type 为 completion_request 的情况（缺失字段）
        if (msg.metadata.message_type === 'completion_request' && msg.metadata.original_ws_message?.data) {
          return {
            ...baseMessage,
            type: 'assistant' as const,
            missingFieldsData: {
              message: msg.metadata.original_ws_message.data.message || '数据不完整，需要补全必填字段',
              summary: `发现 ${msg.metadata.original_ws_message.data.missing_fields?.length || 0} 条记录缺少必填字段`,
              missing_fields: msg.metadata.original_ws_message.data.missing_fields || [],
              suggestion: msg.metadata.original_ws_message.data.suggestion,
            },
          }
        }
        
        // 审核启动消息
        if (msg.metadata.action === 'start_review') {
          return {
            ...baseMessage,
            type: 'system' as const,
            reviewStartData: msg.metadata.data_summary,
          }
        }
        
        // 修改确认消息
        if (msg.metadata.message_type === 'modification_confirmation') {
          return {
            ...baseMessage,
            type: 'system' as const,
            modificationConfirmation: true,
          }
        }
        
        // 操作完成消息
        if (msg.metadata.message_type === 'operation_completed') {
          return {
            ...baseMessage,
            type: 'system' as const,
            operationCompleted: {
              action_type: msg.metadata.action_type,
            },
          }
        }
        
        // 进度消息
        if (msg.metadata.message_type === 'progress' && msg.metadata.stage) {
          return {
            ...baseMessage,
            type: 'progress' as const,
            progressData: {
              stage: msg.metadata.stage,
              progress: msg.metadata.progress || 0,
              message: msg.content,
              details: msg.metadata.original_ws_message?.data?.details,
            },
          }
        }
      }
      
      // 默认处理：尝试从内容推断进度信息
      const progressData = this.extractProgressData(msg)
      if (progressData) {
        return {
          ...baseMessage,
          type: 'progress' as const,
          progressData,
        }
      }
      
      return baseMessage
    })
  }

  /**
   * 转换角色类型
   */
  private convertRoleToType(role: string): 'user' | 'assistant' | 'system' | 'progress' {
    switch (role) {
      case 'user':
        return 'user'
      case 'assistant':
        return 'assistant'
      case 'system':
        return 'system'
      default:
        return 'system'
    }
  }

  /**
   * 从消息metadata中提取进度数据
   */
  private extractProgressData(msg: HistoryMessage): import('../store/useAppStore').ProgressMessageData | undefined {
    // 检查是否是进度消息
    if (msg.metadata?.action === 'start_review' || 
        msg.metadata?.modification_id ||
        msg.content.includes('进度') ||
        msg.content.includes('完成') ||
        msg.content.includes('失败')) {
      
      // 尝试从metadata中提取进度信息
      if (msg.metadata?.progress !== undefined) {
        return {
          stage: msg.metadata.stage || 'processing',
          progress: msg.metadata.progress || 0,
          message: msg.content,
          details: msg.metadata.details,
        }
      }
      
      // 根据消息内容推断进度信息
      if (msg.content.includes('任务初始化')) {
        return {
          stage: 'initialization',
          progress: msg.content.includes('完成') ? 100 : 0,
          message: msg.content,
        }
      } else if (msg.content.includes('拆图')) {
        return {
          stage: 'file_processing',
          progress: msg.content.includes('完成') ? 100 : 50,
          message: msg.content,
        }
      } else if (msg.content.includes('识别特征')) {
        return {
          stage: 'feature_recognition',
          progress: msg.content.includes('完成') ? 100 : 50,
          message: msg.content,
        }
      } else if (msg.content.includes('计算价格')) {
        return {
          stage: 'cost_calculation',
          progress: msg.content.includes('完成') ? 100 : 50,
          message: msg.content,
        }
      }
    }
    
    return undefined
  }

  /**
   * 归档会话
   * 根据API文档：POST /api/v1/chat/sessions/{session_id}/archive
   */
  async archiveSession(sessionId: string): Promise<void> {
    try {
      await api.post(`/chat/sessions/${sessionId}/archive`)
    } catch (error) {
      console.error('归档会话失败:', error)
      throw error
    }
  }
}

export const historyService = new HistoryService()