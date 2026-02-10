# 环境变量快速参考

## 🚀 快速启动

```bash
# 开发模式（使用 .env.development）
npm run dev

# 生产构建（使用 .env.production）
npm run build

# 预览生产构建
npm run preview
```

---

## 📁 环境文件

| 文件 | 命令 | 说明 |
|------|------|------|
| `.env` | 所有命令 | 基础配置（最低优先级） |
| `.env.development` | `npm run dev` | 开发环境配置 |
| `.env.production` | `npm run build` | 生产环境配置 |

**优先级**: `.env` < `.env.development` / `.env.production`

---

## 🔧 当前配置

### 开发环境 (npm run dev)
```bash
VITE_API_BASE_URL=http://192.168.0.41:8211
VITE_AUTH_BASE_URL=http://192.168.0.14:8000
VITE_WS_BASE_URL=http://192.168.0.41:8211
VITE_CONTINUE_API_BASE_URL=http://192.168.1.51:8300
```

### 生产环境 (npm run build)
```bash
VITE_API_BASE_URL=https://your-production-domain.com
VITE_AUTH_BASE_URL=https://your-auth-domain.com
VITE_WS_BASE_URL=https://your-production-domain.com
VITE_CONTINUE_API_BASE_URL=https://your-continue-api-domain.com
```

---

## 💻 代码中使用

```typescript
// 推荐方式：使用统一配置
import { config } from '@/config/env'

const apiUrl = config.API_URL        // 完整API地址
const wsUrl = config.WS_URL          // WebSocket地址
const authUrl = config.AUTH_URL      // 认证服务地址

// 环境判断
if (config.isDev) {
  console.log('开发环境')
}
```

---

## ⚠️ 重要提示

1. **修改环境变量后必须重启服务**
   ```bash
   # Ctrl+C 停止
   npm run dev  # 重新启动
   ```

2. **变量名必须以 `VITE_` 开头**
   - ✅ `VITE_API_URL`
   - ❌ `API_URL`

3. **不要提交敏感信息到 Git**
   - 使用 `.env.local` 存储本地配置
   - 添加到 `.gitignore`

---

## 🔍 调试

```typescript
// 查看所有环境变量
console.log(import.meta.env)

// 查看当前模式
console.log(import.meta.env.MODE)  // development / production

// 查看配置
import { config } from '@/config/env'
console.log(config)
```

---

详细文档请查看: [ENV_GUIDE.md](./ENV_GUIDE.md)
