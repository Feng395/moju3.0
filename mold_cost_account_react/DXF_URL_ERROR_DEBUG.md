# DXF Viewer URL 参数错误调试指南

## 🐛 错误信息
```
DXF文件加载失败: Error: `url` parameter is not specified
at _DxfViewer.Load (dxf-viewer.js?v=deaff638:34978:13)
```

## 🔍 问题分析

这个错误表明传递给 `viewer.Load()` 方法的URL参数为空、未定义或无效。

## 🛠️ 调试步骤

### 1. 检查预签名URL获取
```typescript
// 在浏览器控制台中测试
const testFilePath = 'dxf/2026/01/9ba97078-a7bf-4472-a977-564dca64cee7/LP-01.dxf'
const result = await fileService.getPresignedUrl(testFilePath, 3600)
console.log('API结果:', result)
```

### 2. 检查状态管理
确保 `presignedUrl` 状态正确设置：
```typescript
console.log('presignedUrl状态:', presignedUrl)
console.log('URL类型:', typeof presignedUrl)
console.log('URL长度:', presignedUrl?.length)
```

### 3. 检查useEffect触发时机
```typescript
useEffect(() => {
  console.log('useEffect触发:', {
    presignedUrl: presignedUrl,
    hasContainer: !!containerRef.current,
    visible: visible
  })
}, [presignedUrl, visible])
```

## 🔧 已实施的修复

### 1. 增强错误检查
```typescript
// 验证URL格式
if (!presignedUrl || typeof presignedUrl !== 'string' || presignedUrl.trim() === '') {
  throw new Error('预签名URL无效或为空')
}

// 加载前再次验证
await viewer.Load(presignedUrl.trim())
```

### 2. 添加详细日志
```typescript
console.log('开始加载DXF文件，URL长度:', presignedUrl.length)
console.log('URL前100字符:', presignedUrl.substring(0, 100))
```

### 3. 改进状态管理
- 添加了更多的状态验证
- 改进了错误处理逻辑
- 增加了重试机制

### 4. 调试工具
- 创建了 `DebugDxfViewer` 组件
- 添加了API测试按钮
- 增加了详细的控制台日志

## 🧪 测试方法

### 方法1：使用调试组件
```tsx
import DebugDxfViewer from './src/test/debug-dxf-viewer'

// 在应用中渲染调试组件
<DebugDxfViewer />
```

### 方法2：浏览器控制台测试
1. 打开浏览器开发者工具
2. 在控制台中运行：
```javascript
// 测试API调用
const testAPI = async () => {
  try {
    const result = await fileService.getPresignedUrl(
      'dxf/2026/01/9ba97078-a7bf-4472-a977-564dca64cee7/LP-01.dxf', 
      3600
    )
    console.log('✅ API成功:', result)
    return result
  } catch (error) {
    console.error('❌ API失败:', error)
  }
}
testAPI()
```

### 方法3：网络请求检查
1. 打开开发者工具的Network标签
2. 点击"查看图纸"按钮
3. 检查是否有对 `/api/v1/files/presigned-url` 的请求
4. 查看请求和响应的详细信息

## 🎯 可能的原因

### 1. API调用失败
- 网络连接问题
- 认证token无效
- 服务器错误

### 2. 状态竞争
- useEffect在错误的时机触发
- presignedUrl状态未正确设置

### 3. 参数问题
- filePath为空或格式错误
- API响应格式不正确

### 4. 时序问题
- 组件卸载后仍在执行异步操作
- 状态更新时机不正确

## ✅ 验证清单

- [ ] API调用是否成功返回预签名URL
- [ ] presignedUrl状态是否正确设置
- [ ] URL格式是否有效（以http开头）
- [ ] 网络请求是否成功（200状态码）
- [ ] 认证token是否有效
- [ ] 文件路径格式是否正确

## 🚀 下一步

如果问题仍然存在：

1. **检查网络请求**：确认API调用是否成功
2. **验证认证**：确保登录状态和token有效
3. **测试文件路径**：使用已知存在的DXF文件路径
4. **简化测试**：使用调试组件逐步排查问题

---

## 📝 调试日志模板

```
🔍 DXF查看器调试信息:
- 文件路径: [filePath]
- API调用状态: [成功/失败]
- 预签名URL: [有/无]
- URL长度: [length]
- 错误信息: [error]
- 浏览器: [browser]
- 网络状态: [online/offline]
```