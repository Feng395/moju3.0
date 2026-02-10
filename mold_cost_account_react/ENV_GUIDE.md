# React 前端环境变量使用指南

## 📋 目录

- [环境文件说明](#环境文件说明)
- [环境变量加载机制](#环境变量加载机制)
- [npm命令与环境对应关系](#npm命令与环境对应关系)
- [环境变量列表](#环境变量列表)
- [使用方法](#使用方法)
- [常见问题](#常见问题)

---

## 🗂️ 环境文件说明

项目中有3个环境配置文件：

| 文件名 | 用途 | 优先级 | 何时使用 |
|--------|------|--------|----------|
| `.env` | **默认配置** | 最低 | 所有环境的基础配置 |
| `.env.development` | **开发环境** | 中 | `npm run dev` 时使用 |
| `.env.production` | **生产环境** | 高 | `npm run build` 时使用 |

### 文件优先级规则

Vite 会按照以下优先级加载环境变量（**后者覆盖前者**）：

```
.env  <  .env.development  (开发模式)
.env  <  .env.production   (生产模式)
```

---

## ⚙️ 环境变量加载机制

### Vite 环境变量规则

1. **必须以 `VITE_` 开头**
   - ✅ `VITE_API_BASE_URL` - 会被暴露给客户端
   - ❌ `API_BASE_URL` - 不会被暴露

2. **自动注入到 `import.meta.env`**
   ```typescript
   // 在代码中访问
   const apiUrl = import.meta.env.VITE_API_BASE_URL
   ```

3. **内置环境变量**
   - `import.meta.env.MODE` - 当前模式（development/production）
   - `import.meta.env.DEV` - 是否为开发环境（boolean）
   - `import.meta.env.PROD` - 是否为生产环境（boolean）
   - `import.meta.env.BASE_URL` - 应用的基础路径

---

## 🚀 npm命令与环境对应关系

### 1. 开发模式 - `npm run dev`

```bash
npm run dev
# 等同于: vite --host
```

**加载的环境文件**:
1. `.env` (基础配置)
2. `.env.development` (开发配置，覆盖基础配置)

**环境变量**:
```javascript
import.meta.env.MODE = "development"
import.meta.env.DEV = true
import.meta.env.PROD = false
```

**实际配置**:
```bash
VITE_API_BASE_URL=http://192.168.0.41:8211
VITE_API_PREFIX=/api/v1
VITE_AUTH_BASE_URL=http://192.168.0.14:8000
VITE_WS_BASE_URL=http://192.168.0.41:8211
VITE_CONTINUE_API_BASE_URL=http://192.168.1.51:8300
```

**访问地址**: http://localhost:3000

---

### 2. 生产构建 - `npm run build`

```bash
npm run build
# 等同于: vite build
```

**加载的环境文件**:
1. `.env` (基础配置)
2. `.env.production` (生产配置，覆盖基础配置)

**环境变量**:
```javascript
import.meta.env.MODE = "production"
import.meta.env.DEV = false
import.meta.env.PROD = true
```

**实际配置**:
```bash
VITE_API_BASE_URL=https://your-production-domain.com
VITE_API_PREFIX=/api/v1
VITE_AUTH_BASE_URL=https://your-auth-domain.com
VITE_WS_BASE_URL=https://your-production-domain.com
VITE_CONTINUE_API_BASE_URL=https://your-continue-api-domain.com
```

**输出目录**: `dist/`

---

### 3. 预览构建 - `npm run preview`

```bash
npm run preview
# 等同于: vite preview
```

**说明**: 预览生产构建的结果，使用的是 **生产环境配置**

**访问地址**: http://localhost:4173

---

## 📝 环境变量列表

### 当前项目的环境变量

| 变量名 | 说明 | 开发环境值 | 生产环境值 |
|--------|------|-----------|-----------|
| `VITE_API_BASE_URL` | 主API服务地址 | http://192.168.0.41:8211 | https://your-production-domain.com |
| `VITE_API_PREFIX` | API路径前缀 | /api/v1 | /api/v1 |
| `VITE_AUTH_BASE_URL` | 认证服务地址 | http://192.168.0.14:8000 | https://your-auth-domain.com |
| `VITE_WS_BASE_URL` | WebSocket服务地址 | http://192.168.0.41:8211 | https://your-production-domain.com |
| `VITE_CONTINUE_API_BASE_URL` | 核算服务地址 | http://192.168.1.51:8300 | https://your-continue-api-domain.com |

### 在代码中的使用

项目通过 `src/config/env.ts` 统一管理环境变量：

```typescript
// src/config/env.ts
export const config = {
  // API基础URL
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://192.168.0.41:8211',
  
  // API前缀
  API_PREFIX: import.meta.env.VITE_API_PREFIX || '/api/v1',
  
  // 认证服务基础URL
  AUTH_BASE_URL: import.meta.env.VITE_AUTH_BASE_URL || 'http://localhost:8000',
  
  // WebSocket基础URL
  WS_BASE_URL: import.meta.env.VITE_WS_BASE_URL || 'http://192.168.0.41:8211',
  
  // Continue接口专用URL
  CONTINUE_API_BASE_URL: import.meta.env.VITE_CONTINUE_API_BASE_URL || 'http://192.168.1.51:8300',
  
  // 计算属性
  get API_URL() {
    return `${this.API_BASE_URL}${this.API_PREFIX}`
  },
  
  get WS_URL() {
    const wsBaseUrl = this.WS_BASE_URL.replace(/^https?:\/\//, '')
    const protocol = this.WS_BASE_URL.startsWith('https') ? 'wss' : 'ws'
    return `${protocol}://${wsBaseUrl}/ws`
  },
  
  // 环境判断
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
}
```

---

## 💡 使用方法

### 方法1: 直接使用 import.meta.env（不推荐）

```typescript
// ❌ 不推荐：直接使用
const apiUrl = import.meta.env.VITE_API_BASE_URL
```

### 方法2: 使用统一配置（推荐）

```typescript
// ✅ 推荐：使用统一配置
import { config } from '@/config/env'

// 使用配置
const apiUrl = config.API_URL  // http://192.168.0.41:8211/api/v1
const wsUrl = config.WS_URL    // ws://192.168.0.41:8211/ws
const authUrl = config.AUTH_URL // http://192.168.0.14:8000

// 环境判断
if (config.isDev) {
  console.log('开发环境')
}
```

### 在组件中使用

```typescript
import { config } from '@/config/env'
import axios from 'axios'

// API请求
const fetchData = async () => {
  const response = await axios.get(`${config.API_URL}/jobs`)
  return response.data
}

// WebSocket连接
const connectWebSocket = () => {
  const ws = new WebSocket(`${config.WS_URL}/${jobId}`)
  ws.onmessage = (event) => {
    console.log('收到消息:', event.data)
  }
}
```

---

## 🔧 修改环境配置

### 修改开发环境配置

编辑 `.env.development` 文件：

```bash
# 修改API地址
VITE_API_BASE_URL=http://192.168.0.100:8000

# 修改认证服务地址
VITE_AUTH_BASE_URL=http://192.168.0.100:8000
```

**重启开发服务器**（环境变量修改后必须重启）：

```bash
# 停止当前服务 (Ctrl+C)
# 重新启动
npm run dev
```

### 修改生产环境配置

编辑 `.env.production` 文件：

```bash
# 修改为实际的生产域名
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_AUTH_BASE_URL=https://auth.yourdomain.com
VITE_WS_BASE_URL=https://api.yourdomain.com
```

**重新构建**：

```bash
npm run build
```

---

## 🎯 不同场景的启动方式

### 场景1: 本地开发（连接本地后端）

```bash
# 1. 确保 .env.development 配置正确
# VITE_API_BASE_URL=http://localhost:8000
# VITE_AUTH_BASE_URL=http://localhost:8000

# 2. 启动开发服务器
npm run dev

# 3. 访问 http://localhost:3000
```

### 场景2: 本地开发（连接远程后端）

```bash
# 1. 修改 .env.development
# VITE_API_BASE_URL=http://192.168.0.41:8211
# VITE_AUTH_BASE_URL=http://192.168.0.14:8000

# 2. 启动开发服务器
npm run dev
```

### 场景3: 生产构建

```bash
# 1. 确保 .env.production 配置正确
# VITE_API_BASE_URL=https://api.yourdomain.com

# 2. 构建
npm run build

# 3. 预览构建结果（可选）
npm run preview

# 4. 部署 dist/ 目录到服务器
```

### 场景4: 临时覆盖环境变量

```bash
# 在命令行临时设置环境变量（仅本次有效）
# Windows (CMD)
set VITE_API_BASE_URL=http://test.com && npm run dev

# Windows (PowerShell)
$env:VITE_API_BASE_URL="http://test.com"; npm run dev

# Linux/Mac
VITE_API_BASE_URL=http://test.com npm run dev
```

---

## ❓ 常见问题

### Q1: 修改了 .env 文件，为什么不生效？

**A**: 环境变量在构建时注入，修改后必须**重启开发服务器**或**重新构建**。

```bash
# 停止服务 (Ctrl+C)
# 重新启动
npm run dev
```

### Q2: 为什么我的环境变量是 undefined？

**A**: 检查以下几点：
1. 变量名是否以 `VITE_` 开头
2. 是否重启了开发服务器
3. 文件名是否正确（`.env.development` 不是 `.env.dev`）

### Q3: 如何查看当前使用的环境变量？

**A**: 在代码中打印：

```typescript
console.log('环境变量:', import.meta.env)
console.log('API地址:', config.API_URL)
console.log('当前模式:', import.meta.env.MODE)
console.log('是否开发环境:', import.meta.env.DEV)
```

### Q4: 生产环境如何配置不同的后端地址？

**A**: 修改 `.env.production` 文件，然后重新构建：

```bash
# 1. 编辑 .env.production
VITE_API_BASE_URL=https://api.production.com

# 2. 重新构建
npm run build

# 3. 部署 dist/ 目录
```

### Q5: 可以创建自定义环境吗（如测试环境）？

**A**: 可以！创建 `.env.test` 文件，然后使用 `--mode` 参数：

```bash
# 创建 .env.test 文件
VITE_API_BASE_URL=http://test.yourdomain.com

# 使用测试环境启动
vite --mode test

# 或在 package.json 中添加脚本
"scripts": {
  "dev:test": "vite --mode test"
}

# 运行
npm run dev:test
```

### Q6: 如何在不同网络环境下快速切换配置？

**A**: 推荐方法：

1. **创建多个环境文件**：
   ```
   .env.local      # 本地开发
   .env.office     # 办公室网络
   .env.home       # 家庭网络
   ```

2. **在 package.json 中添加脚本**：
   ```json
   "scripts": {
     "dev": "vite --mode development",
     "dev:local": "vite --mode local",
     "dev:office": "vite --mode office",
     "dev:home": "vite --mode home"
   }
   ```

3. **使用对应的命令启动**：
   ```bash
   npm run dev:office  # 办公室
   npm run dev:home    # 家里
   ```

---

## 📊 环境变量流程图

```
┌─────────────────┐
│  npm run dev    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Vite 启动              │
│  MODE = development     │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  加载环境文件           │
│  1. .env               │
│  2. .env.development   │
│  (后者覆盖前者)         │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  注入到 import.meta.env │
│  VITE_* 变量可访问      │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  应用启动               │
│  http://localhost:3000  │
└─────────────────────────┘
```

---

## 🔐 安全注意事项

1. **不要提交敏感信息**
   - `.env.local` 应该添加到 `.gitignore`
   - 不要在 `.env` 文件中存储密码、密钥等敏感信息

2. **生产环境配置**
   - 生产环境的敏感配置应该通过 CI/CD 或服务器环境变量注入
   - 不要在代码仓库中暴露生产环境的真实地址

3. **环境变量暴露**
   - 所有 `VITE_` 开头的变量都会被打包到客户端代码中
   - 不要使用环境变量存储后端密钥或敏感信息

---

## 📚 参考资料

- [Vite 环境变量官方文档](https://vitejs.dev/guide/env-and-mode.html)
- [Vite 配置参考](https://vitejs.dev/config/)

---

**最后更新**: 2026-02-10  
**文档版本**: v1.0
