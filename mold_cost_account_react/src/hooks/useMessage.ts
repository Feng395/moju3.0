/**
 * 使用 Ant Design App 组件提供的 message 实例
 * 这样可以消费动态主题上下文
 * 
 * 使用方法：
 * ```tsx
 * import { useMessage } from '@/hooks/useMessage'
 * 
 * function MyComponent() {
 *   const message = useMessage()
 *   
 *   const handleClick = () => {
 *     message.success('操作成功')
 *   }
 * }
 * ```
 */
import { App } from 'antd'

export const useMessage = () => {
  const { message } = App.useApp()
  return message
}

export const useModal = () => {
  const { modal } = App.useApp()
  return modal
}

export const useNotification = () => {
  const { notification } = App.useApp()
  return notification
}
