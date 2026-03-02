// 环境配置
export const config = {
  // API基础URL
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://192.168.1.143:8000',

  // API前缀
  API_PREFIX: import.meta.env.VITE_API_PREFIX || '/api/v1',

  // 认证服务基础URL
  AUTH_BASE_URL: import.meta.env.VITE_AUTH_BASE_URL || 'http://192.168.1.143:8000',

  // WebSocket基础URL
  WS_BASE_URL: import.meta.env.VITE_WS_BASE_URL || import.meta.env.VITE_API_BASE_URL || 'http://192.168.1.143:8000',

  // Continue接口专用URL（核算服务）
  CONTINUE_API_BASE_URL: import.meta.env.VITE_CONTINUE_API_BASE_URL || 'http://192.168.1.143:8000',

  // 完整的API地址
  get API_URL() {
    return `${this.API_BASE_URL}${this.API_PREFIX}`
  },

  // Continue接口完整地址
  get CONTINUE_API_URL() {
    return `${this.CONTINUE_API_BASE_URL}${this.API_PREFIX}`
  },

  // WebSocket地址
  get WS_URL() {
    const wsBaseUrl = this.WS_BASE_URL.replace(/^https?:\/\//, '')
    const protocol = this.WS_BASE_URL.startsWith('https') ? 'wss' : 'ws'
    return `${protocol}://${wsBaseUrl}/ws`
  },

  // 认证API地址
  get AUTH_URL() {
    return this.AUTH_BASE_URL
  },

  // 是否为开发环境
  isDev: import.meta.env.DEV,

  // 是否为生产环境
  isProd: import.meta.env.PROD,
}

export default config