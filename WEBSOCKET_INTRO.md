# 项目 WebSocket 使用说明

## 1. 概览

这个项目里的 WebSocket 不是一个边缘功能，而是主流程的一部分。它承担了三类实时能力：

1. 任务处理进度推送
2. 审核/补全/修改确认等交互消息推送
3. 历史会话恢复后的实时续连

整体链路是：

`前端 WebSocket 连接 -> FastAPI WebSocket 路由 -> ConnectionManager -> Redis Pub/Sub -> 业务消息 -> 前端页面消费`

## 2. 整体架构

核心流程如下：

1. 前端根据 `job_id` 连接 `ws://host/ws/{job_id}`
2. API Gateway 建立连接，并按 `job_id` 把连接存进连接池
3. 后端其它模块把进度消息或审核消息发布到 Redis
4. `ConnectionManager` 订阅 Redis 频道
5. 收到 Redis 消息后，转换成 WebSocket 消息并广播给对应 `job_id`
6. 前端按消息类型更新聊天、进度、补全卡片或审核界面

涉及的两类 Redis 频道：

- `job:{job_id}:progress`
- `job:{job_id}:review`

## 3. 后端实现

### 3.1 WebSocket 路由入口

文件：[mold_cost_/api_gateway/routers/websocket_router.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/routers/websocket_router.py)

关键点：

- 暴露 WebSocket 端点 `/ws/{job_id}`，见 [websocket_router.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/routers/websocket_router.py#L22)
- 连接建立后先发送一条 `connected` 消息
- 持续监听前端发来的消息
- 如果收到 `ping`，服务端返回 `pong`
- 其它消息默认走 echo，主要用于调试

同时还暴露了两个辅助 HTTP 接口：

- `GET /ws/{job_id}/history`：拿最近消息历史
- `GET /ws/status`：查看当前连接数和活跃任务

### 3.2 WebSocket 管理器

文件：[mold_cost_/api_gateway/websocket.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/websocket.py)

这里的 `ConnectionManager` 是真正的核心。

主要职责：

- `active_connections` 维护 `job_id -> WebSocket[]` 的连接池
- `connect()` 接受连接并登记
- `disconnect()` 断开并清理
- `broadcast()` 向某个 `job_id` 下的所有连接广播消息，见 [websocket.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/websocket.py#L63)
- `start_redis_subscriber()` 监听 Redis，见 [websocket.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/websocket.py#L98)

Redis 订阅逻辑：

- 监听 `job:*:progress`
- 监听 `job:*:review`

收到消息后：

- 如果是 `progress` 频道，包装成：
  - `{ type: "progress", job_id, timestamp, data }`
- 如果是 `review` 频道，直接透传业务消息
  - 若缺少 `job_id` / `timestamp`，会补齐

广播完成后还会做两件事：

1. 保存到 Redis 历史列表 `job:{job_id}:messages`
2. 对 `progress` 消息做数据库持久化

### 3.3 应用启动时自动挂载 Redis 订阅

文件：[mold_cost_/api_gateway/main.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/main.py)

在应用生命周期启动阶段，会创建后台任务启动 Redis 订阅器，见 [main.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/main.py#L91)。

这意味着：

- WebSocket 不只是一个“前端直连接口”
- API Gateway 还承担了“Redis 消息桥接器”的角色

## 4. 消息来源

### 4.1 进度消息

文件：[mold_cost_/shared/progress_publisher.py](/d:/workspace/project/python/mold3.0/mold_cost_/shared/progress_publisher.py)

这里负责把进度发布到 Redis：

- 频道：`job:{job_id}:progress`
- 内容通常包含：
  - `stage`
  - `progress`
  - `message`
  - `details`

这类消息最终会被网关转换成 `type = "progress"` 的 WebSocket 消息。

### 4.2 审核/补全/修改类消息

文件：[mold_cost_/agents/interaction_agent.py](/d:/workspace/project/python/mold3.0/mold_cost_/agents/interaction_agent.py)

这里会发布大量审核阶段消息到 `job:{job_id}:review`。

项目里能看到的主要类型包括：

- `review_data`
- `review_display_view`
- `completion_request`
- `modification_confirmation`
- `review_completed`
- `operation_completed`
- `system_message`

这些消息多数是“审核流程中的关键交互状态”。

### 4.3 直接 WebSocket 广播消息

文件：[mold_cost_/api_gateway/services/interaction_service.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/services/interaction_service.py)

这里有一类消息不通过 Redis，而是直接调用 `manager.broadcast(...)` 推给前端：

- `need_user_input`
- `interaction_response_received`

它们通常代表：

- 系统要求用户填写卡片/参数
- 系统确认已经收到用户提交

## 5. 前端实现

### 5.1 WebSocket 地址配置

文件：[mold_cost_account_react/src/config/env.ts](/d:/workspace/project/python/mold3.0/mold_cost_account_react/src/config/env.ts)

关键点：

- `VITE_WS_BASE_URL` 是基础配置
- `config.WS_URL` 会自动把 `http/https` 转成 `ws/wss`
- 最终连接地址形式为：

```ts
${config.WS_URL}/${jobId}
```

### 5.2 前端 WebSocket 服务

文件：[mold_cost_account_react/src/services/websocketService.ts](/d:/workspace/project/python/mold3.0/mold_cost_account_react/src/services/websocketService.ts)

这是前端实时通信的总入口。

关键结论：

- 当前实际使用的是浏览器原生 `WebSocket`
- 不是 `socket.io-client` 协议

虽然依赖里仍然保留了 `socket.io-client`：

- [mold_cost_account_react/package.json](/d:/workspace/project/python/mold3.0/mold_cost_account_react/package.json#L32)

但源码运行链路里实际调用的是：

- `new WebSocket(wsUrl)`，见 [websocketService.ts](/d:/workspace/project/python/mold3.0/mold_cost_account_react/src/services/websocketService.ts#L194)

这个服务统一封装了：

- 连接建立
- 历史消息加载
- 心跳保活
- 连接质量检测
- 断线重连
- 消息分发

### 5.3 历史消息恢复

连接前会先拉历史消息：

- 新上传或断线重连时：
  - 调用 `/ws/{job_id}/history`
- 从历史会话切换时：
  - 调用 `historyService.getChatHistory(jobId, { limit: 100 })`

对应实现见：

- [websocketService.ts](/d:/workspace/project/python/mold3.0/mold_cost_account_react/src/services/websocketService.ts#L134)

### 5.4 心跳与重连

前端自己维护了一套心跳：

- 定时发送 `ping`
- 服务端返回 `pong`
- 超时计数达到阈值后主动关闭连接
- 再走指数退避重连

相关逻辑见：

- [websocketService.ts](/d:/workspace/project/python/mold3.0/mold_cost_account_react/src/services/websocketService.ts#L252)
- [websocketService.ts](/d:/workspace/project/python/mold3.0/mold_cost_account_react/src/services/websocketService.ts#L480)

## 6. 前端消费层

### 6.1 Hook 封装

文件：[mold_cost_account_react/src/hooks/useWebSocket.ts](/d:/workspace/project/python/mold3.0/mold_cost_account_react/src/hooks/useWebSocket.ts)

`useWebSocket` 负责把底层服务包装成 React 可用状态：

- `status`
- `isConnected`
- `messages`
- `latestMessage`
- `progressData`
- `currentInteractionCard`
- `connectionStats`
- `connectionQuality`

同时把不同消息类型通过回调派发给页面。

### 6.2 主要业务消费组件

文件：[mold_cost_account_react/src/components/FileUpload.tsx](/d:/workspace/project/python/mold3.0/mold_cost_account_react/src/components/FileUpload.tsx)

作用：

- 文件上传成功后立即建立 WebSocket
- 消费 `progress`、`completion_request`、`review_display_view`
- 驱动聊天区中的“处理中 / 等待确认 / 等待补全”状态

文件：[mold_cost_account_react/src/components/HistorySessions.tsx](/d:/workspace/project/python/mold3.0/mold_cost_account_react/src/components/HistorySessions.tsx)

作用：

- 切换历史会话时先断开旧连接
- 再连接新的 `job_id`
- 恢复旧会话对应的实时流

文件：[mold_cost_account_react/src/components/Sidebar.tsx](/d:/workspace/project/python/mold3.0/mold_cost_account_react/src/components/Sidebar.tsx)

作用：

- 也承担一部分会话切换后的 WebSocket 重连逻辑

## 7. 消息类型说明

前端已声明的主要消息类型见：

- [websocketService.ts](/d:/workspace/project/python/mold3.0/mold_cost_account_react/src/services/websocketService.ts#L5)

包含：

- `connected`
- `progress`
- `need_user_input`
- `interaction_response_received`
- `error`
- `pong`
- `review_data`
- `modification_confirmation`
- `review_completed`
- `review_display_view`
- `completion_request`

其中最关键的几类如下。

### 7.1 connected

服务端建立连接后的欢迎消息。

用途：

- 告知前端当前连接已经可用
- 返回当前 `job_id`
- 附带当前连接数

### 7.2 progress

最通用的实时进度消息。

常用字段：

- `data.stage`
- `data.progress`
- `data.message`
- `data.details`

常用于：

- 上传后解析进度
- 特征识别进度
- 价格计算进度
- 全流程阶段流转

### 7.3 review_display_view

表示识别结果已经整理成可展示视图。

前端里它通常不会被当成普通文本消息，而是会被映射成：

- “特征识别完成”
- “等待用户检查/确认”

也就是说，这类消息在 UI 层有二次语义转换。

### 7.4 completion_request

表示当前数据不完整，需要用户补全缺失字段。

前端会据此生成：

- 缺失字段提示
- 补全卡片
- 交互式填写流程

### 7.5 need_user_input

表示系统要求用户填写或确认一张交互卡片。

这类消息通常不是来自 Redis review 流，而是来自网关直接广播。

### 7.6 review_completed

表示审核阶段已完成。

通常意味着：

- 审核处理结束
- 前端可以结束等待状态

## 8. 历史与持久化

### 8.1 Redis 短历史

`ConnectionManager._save_to_history()` 会把消息写到：

- `job:{job_id}:messages`

策略：

- 只保留最近 10 条
- 过期时间 1 小时

用途：

- 页面刷新后快速恢复最近上下文
- 断线重连时补最近消息

### 8.2 数据库持久化

文件：[mold_cost_/agents/message_persistence_manager.py](/d:/workspace/project/python/mold3.0/mold_cost_/agents/message_persistence_manager.py)

这里会决定哪些 WebSocket 消息需要入库。

当前高价值持久化消息包括：

- `need_user_input`
- `modification_confirmation`
- `review_data`
- `review_display_view`
- `completion_request`
- `review_completed`
- `operation_completed`
- `system_message`
- `progress`

它的作用是把 WebSocket 消息转成聊天系统可回放的内容，而不是只存在内存里。

## 9. 当前设计的几个关键特点

1. 前端实际协议是原生 WebSocket，不是 Socket.IO
2. WebSocket 在这个项目里是主业务通道，不只是附属进度条
3. 消息按 `job_id` 隔离，同一任务可以有多个连接同时接收
4. 后端使用 Redis Pub/Sub 解耦多进程业务模块和网关推送层
5. 前端对特殊消息做了 UI 语义转换，不是所有消息都直接原样展示
6. 历史会话切换时会显式断开旧连接，避免串流

## 10. 排查问题时建议优先看这些文件

- [mold_cost_/api_gateway/routers/websocket_router.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/routers/websocket_router.py)
- [mold_cost_/api_gateway/websocket.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/websocket.py)
- [mold_cost_/api_gateway/main.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/main.py)
- [mold_cost_/shared/progress_publisher.py](/d:/workspace/project/python/mold3.0/mold_cost_/shared/progress_publisher.py)
- [mold_cost_/agents/interaction_agent.py](/d:/workspace/project/python/mold3.0/mold_cost_/agents/interaction_agent.py)
- [mold_cost_/api_gateway/services/interaction_service.py](/d:/workspace/project/python/mold3.0/mold_cost_/api_gateway/services/interaction_service.py)
- [mold_cost_/agents/message_persistence_manager.py](/d:/workspace/project/python/mold3.0/mold_cost_/agents/message_persistence_manager.py)
- [mold_cost_account_react/src/config/env.ts](/d:/workspace/project/python/mold3.0/mold_cost_account_react/src/config/env.ts)
- [mold_cost_account_react/src/services/websocketService.ts](/d:/workspace/project/python/mold3.0/mold_cost_account_react/src/services/websocketService.ts)
- [mold_cost_account_react/src/hooks/useWebSocket.ts](/d:/workspace/project/python/mold3.0/mold_cost_account_react/src/hooks/useWebSocket.ts)
- [mold_cost_account_react/src/components/FileUpload.tsx](/d:/workspace/project/python/mold3.0/mold_cost_account_react/src/components/FileUpload.tsx)
- [mold_cost_account_react/src/components/HistorySessions.tsx](/d:/workspace/project/python/mold3.0/mold_cost_account_react/src/components/HistorySessions.tsx)
- [mold_cost_account_react/src/components/Sidebar.tsx](/d:/workspace/project/python/mold3.0/mold_cost_account_react/src/components/Sidebar.tsx)

## 11. 一句话总结

这个项目的 WebSocket 体系，本质上是“以 `job_id` 为隔离维度、以 Redis 为中转总线、由 API Gateway 统一对前端推送”的实时消息通道；它覆盖了任务进度、审核交互、缺失补全和历史恢复，是核心业务链路的一部分。
