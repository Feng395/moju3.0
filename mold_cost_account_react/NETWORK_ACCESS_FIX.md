# 局域网访问配置修复

## 🐛 问题描述

同事通过 `http://192.168.1.143:3000` 访问前端时：
- ✅ 可以打开页面
- ✅ 可以登录
- ❌ 历史记录无法显示
- ❌ 其他 API 请求失败

## 🔍 问题原因

### 1. 前端配置问题

前端的环境变量配置使用了 `localhost:8000`：

```bash
# .env.local
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=http://localhost:8000
```

### 2. 问题分析

当同事从其他机器访问时：
- 前端页面：`http://192.168.1.143:3000` ✅ 正确
- API 请求：`http://localhost:8000` ❌ 指向同事自己的机器

**localhost 的含义**：
- 在你的机器上：`localhost` = `192.168.1.143` ✅
- 在同事的机器上：`localhost` = 同事的机器 ❌

### 3. 为什么登录可以但历史记录不行？

可能的原因：
1. 登录使用了不同的 API 端点
2. 登录信息缓存在浏览器中
3. 历史记录需要实时请求后端 API

## ✅ 解决方案

### 1. 修改环境变量配置

将所有 `localhost` 改为服务器 IP 地址 `192.168.1.143`。

#### .env 文件

```bash
# 修改前
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=http://localhost:8000

# 修改后
VITE_API_BASE_URL=http://192.168.1.143:8000
VITE_WS_BASE_URL=http://192.168.1.143:8000
```

#### .env.local 文件（优先级更高）

```bash
# 修改前
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=http://localhost:8000

# 修改后
VITE_API_BASE_URL=http://192.168.1.143:8000
VITE_WS_BASE_URL=http://192.168.1.143:8000
```

### 2. 修改 Vite 配置

在 `vite.config.ts` 中添加 `host: '0.0.0.0'`：

```typescript
export default defineConfig({
  server: {
    host: '0.0.0.0',  // 允许外部访问
    port: 3000,
    // ...
  },
})
```

### 3. 重启前端服务

```bash
# 停止当前服务（Ctrl+C）
# 重新启动
npm run dev
```

## 📊 修改的文件

### 已修改

1. ✅ `mold_cost_account_react/.env`
   - 所有 `localhost:8000` → `192.168.1.143:8000`

2. ✅ `mold_cost_account_react/.env.local`
   - 所有 `localhost:8000` → `192.168.1.143:8000`

3. ✅ `mold_cost_account_react/vite.config.ts`
   - 添加 `host: '0.0.0.0'`

### 环境变量优先级

Vite 的环境变量加载顺序（从高到低）：

1. `.env.local` - 本地覆盖（优先级最高）
2. `.env.development` - 开发环境
3. `.env.production` - 生产环境
4. `.env` - 默认配置

**重要**：`.env.local` 的配置会覆盖其他文件！

## 🧪 验证步骤

### 1. 重启前端服务

```bash
cd mold_cost_account_react
npm run dev
```

### 2. 检查输出

应该看到：

```
VITE v5.4.21  ready in 297 ms

➜  Local:   http://localhost:3000/
➜  Network: http://192.168.1.143:3000/
➜  press h + enter to show help
```

### 3. 测试访问

**在你的机器上**：
- ✅ `http://localhost:3000`
- ✅ `http://192.168.1.143:3000`

**在同事的机器上**：
- ✅ `http://192.168.1.143:3000`

### 4. 测试功能

1. ✅ 登录
2. ✅ 查看历史记录
3. ✅ 上传文件
4. ✅ WebSocket 连接
5. ✅ 所有 API 请求

## 🔧 开发环境 vs 生产环境

### 开发环境（当前配置）

```bash
# .env.local
VITE_API_BASE_URL=http://192.168.1.143:8000
```

**优点**：
- ✅ 局域网内所有设备都可以访问
- ✅ 便于团队协作测试

**缺点**：
- ⚠️ 需要确保后端服务在 192.168.1.143 上运行
- ⚠️ IP 地址变化时需要更新配置

### 生产环境（推荐）

```bash
# .env.production
VITE_API_BASE_URL=https://your-domain.com
```

**优点**：
- ✅ 使用域名，不受 IP 变化影响
- ✅ 支持 HTTPS 加密
- ✅ 更专业的部署方式

## 📝 最佳实践

### 1. 使用环境变量

不要在代码中硬编码 URL：

```typescript
// ❌ 不好
const API_URL = 'http://localhost:8000'

// ✅ 好
const API_URL = import.meta.env.VITE_API_BASE_URL
```

### 2. 提供多个环境配置

```bash
# .env.local - 本地开发
VITE_API_BASE_URL=http://192.168.1.143:8000

# .env.colleague - 同事的配置示例
VITE_API_BASE_URL=http://192.168.1.143:8000

# .env.production - 生产环境
VITE_API_BASE_URL=https://api.your-domain.com
```

### 3. 文档说明

在 README.md 中说明如何配置：

```markdown
## 环境配置

1. 复制 `.env.local.example` 为 `.env.local`
2. 修改 `VITE_API_BASE_URL` 为你的后端地址
3. 重启前端服务
```

## 🎯 常见问题

### Q1: 为什么要用 IP 地址而不是 localhost？

**A**: `localhost` 只能在本机访问，局域网内其他设备无法访问。使用 IP 地址可以让团队成员都能访问。

### Q2: IP 地址变化了怎么办？

**A**: 
1. 短期：手动更新 `.env.local`
2. 长期：使用域名或配置静态 IP

### Q3: 为什么要配置 host: '0.0.0.0'？

**A**: 
- `localhost`：只监听本机
- `0.0.0.0`：监听所有网络接口，允许外部访问

### Q4: 生产环境怎么配置？

**A**: 使用域名和反向代理：

```bash
# .env.production
VITE_API_BASE_URL=https://api.your-domain.com
```

配合 Nginx 反向代理：

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location /api {
        proxy_pass http://localhost:8000;
    }
    
    location / {
        proxy_pass http://localhost:3000;
    }
}
```

## 🎉 总结

### 问题

- ❌ 前端使用 `localhost:8000`
- ❌ 同事无法访问后端 API
- ❌ 历史记录等功能失效

### 解决

- ✅ 修改为 `192.168.1.143:8000`
- ✅ 添加 `host: '0.0.0.0'`
- ✅ 重启前端服务

### 效果

- ✅ 局域网内所有设备都可以访问
- ✅ 所有功能正常工作
- ✅ 团队协作更方便

---

**文档版本**: 1.0.0  
**更新日期**: 2026-03-02  
**维护人员**: 前端团队
