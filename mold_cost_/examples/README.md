# Examples 示例代码

## 📋 概述

本目录包含系统各个功能模块的示例代码和测试脚本，帮助开发者快速理解和使用系统功能。

## 📁 文件分类

### 🔐 认证和会话

- `setup_test_token.py` - 设置测试 Token
- `test_chat_history.py` - 聊天历史测试
- `test_chat_history_simple.py` - 简化版聊天历史测试

### 📤 文件上传

- `test_upload_with_chat_session.py` - 带会话的文件上传
- `test_presigned_url.py` - 预签名 URL 测试

### 💬 聊天和交互

- `interaction_agent_example.py` - 交互 Agent 示例
- `orchestrator_interaction_example.py` - 编排器交互示例
- `test_sse_chat.py` - SSE 聊天测试
- `sse_chat_demo.html` - SSE 聊天前端演示

### 🔍 意图识别和 NLP

- `test_intent_recognition_basic.py` - 基础意图识别
- `test_intent_integration.py` - 意图集成测试
- `test_nlp_parser.py` - NLP 解析器测试
- `test_entity_extraction.py` - 实体提取测试

### 💰 价格和材料

- `test_material_extraction.py` - 材料提取测试
- `test_material_field_mapping.py` - 材料字段映射
- `test_material_price_fix.py` - 材料价格修复

### 🔧 工艺规则

- `test_process_rules_query.py` - 工艺规则查询
- `test_process_code_mapping.py` - 工艺代码映射
- `test_process_id_mapping.py` - 工艺 ID 映射
- `test_process_part_code.py` - 工艺零件代码

### ✏️ 数据修改

- `test_all_modification.py` - 所有修改测试
- `test_batch_modification.py` - 批量修改测试
- `test_process_modification.py` - 工艺修改测试
- `test_process_modification_fix.py` - 工艺修改修复
- `test_process_batch_modification.py` - 工艺批量修改
- `test_all_process_modification.py` - 所有工艺修改

### 🔄 多零件处理

- `test_multi_part_process.py` - 多零件处理测试
- `test_subgraph_extraction.py` - 子图提取测试

### 📊 数据视图

- `test_display_view_flow.py` - 显示视图流程测试

### ✅ 验证和检查

- `test_completeness_check.py` - 完整性检查
- `test_validators.py` - 验证器测试

### 🔒 并发和锁

- `test_optimistic_lock_manual.py` - 乐观锁手动测试
- `test_confirm_timeout.py` - 确认超时测试

### 🔌 API 和集成

- `check_api_gateway.py` - API Gateway 检查
- `test_llm_api.py` - LLM API 测试
- `test_llm_fix.py` - LLM 修复测试
- `test_db_connection_fix.py` - 数据库连接修复

### 📡 消息队列

- `test_rabbitmq_message.py` - RabbitMQ 消息测试

### 🎯 阶段测试

- `test_stage2_api.py` - 第二阶段 API 测试
- `test_stage2_api_mock.py` - 第二阶段 API Mock 测试
- `test_stage3_e2e.py` - 第三阶段端到端测试
- `test_stage3_quick.py` - 第三阶段快速测试

### 📝 日志

- `logging_example.py` - 日志使用示例
- `chat_logger_usage.py` - 聊天日志使用

## 🚀 快速开始

### 环境准备

```bash
# 确保系统已启动
python main.py

# 安装依赖
pip install -r requirements.txt
```

### 运行示例

```bash
# 进入示例目录
cd examples

# 运行特定示例
python test_intent_recognition_basic.py
python interaction_agent_example.py
python test_upload_with_chat_session.py
```

## 📖 详细说明

### 1. 认证示例

#### setup_test_token.py

设置测试环境的 Token。

```python
# 使用方式
python examples/setup_test_token.py

# 功能
- 创建测试用户
- 生成 JWT Token
- 保存到环境变量
```

### 2. 文件上传示例

#### test_upload_with_chat_session.py

演示如何在聊天会话中上传文件。

```python
# 使用方式
python examples/test_upload_with_chat_session.py

# 功能
- 创建聊天会话
- 上传 CAD 文件
- 关联文件和会话
- 触发处理流程
```

**代码示例**:
```python
import asyncio
from api_gateway.services.file_service import FileService

async def upload_example():
    service = FileService()
    
    # 上传文件
    result = await service.upload_file(
        file_path="path/to/file.dwg",
        job_id="job-123",
        session_id="session-456"
    )
    
    print(f"上传成功: {result}")

asyncio.run(upload_example())
```

### 3. 聊天交互示例

#### interaction_agent_example.py

演示如何使用交互 Agent。

```python
# 使用方式
python examples/interaction_agent_example.py

# 功能
- 创建交互 Agent
- 发送用户消息
- 接收 AI 响应
- 处理交互卡片
```

**代码示例**:
```python
from agents.interaction_agent import InteractionAgent

async def chat_example():
    agent = InteractionAgent()
    
    # 发送消息
    response = await agent.process_message(
        message="帮我计算这个零件的价格",
        job_id="job-123"
    )
    
    print(f"AI 响应: {response}")
```

### 4. SSE 聊天示例

#### test_sse_chat.py

演示 Server-Sent Events 实时聊天。

```python
# 使用方式
python examples/test_sse_chat.py

# 功能
- 建立 SSE 连接
- 接收实时消息
- 处理进度更新
```

#### sse_chat_demo.html

前端 SSE 聊天演示页面。

```html
<!-- 使用方式 -->
<!-- 在浏览器中打开 sse_chat_demo.html -->

<!-- 功能 -->
- 可视化聊天界面
- 实时消息显示
- 进度条展示
```

### 5. 意图识别示例

#### test_intent_recognition_basic.py

演示基础意图识别功能。

```python
# 使用方式
python examples/test_intent_recognition_basic.py

# 功能
- 识别用户意图
- 提取关键信息
- 返回意图类型
```

**代码示例**:
```python
from agents.intent_recognizer import IntentRecognizer

async def intent_example():
    recognizer = IntentRecognizer()
    
    # 识别意图
    intent = await recognizer.recognize(
        message="帮我计算价格"
    )
    
    print(f"识别的意图: {intent.type}")
    print(f"置信度: {intent.confidence}")
```

### 6. 数据修改示例

#### test_batch_modification.py

演示批量数据修改。

```python
# 使用方式
python examples/test_batch_modification.py

# 功能
- 批量修改字段
- 验证修改数据
- 更新数据库
```

**代码示例**:
```python
from agents.action_handlers.data_modification_handler import DataModificationHandler

async def batch_modify_example():
    handler = DataModificationHandler()
    
    # 批量修改
    result = await handler.batch_modify(
        job_id="job-123",
        modifications=[
            {"field": "material", "value": "45#钢"},
            {"field": "quantity", "value": 10}
        ]
    )
    
    print(f"修改结果: {result}")
```

### 7. 工艺规则示例

#### test_process_rules_query.py

演示工艺规则查询。

```python
# 使用方式
python examples/test_process_rules_query.py

# 功能
- 查询工艺规则
- 匹配规则条件
- 返回适用规则
```

### 8. 多零件处理示例

#### test_multi_part_process.py

演示多零件并行处理。

```python
# 使用方式
python examples/test_multi_part_process.py

# 功能
- 并行处理多个零件
- 汇总处理结果
- 生成总报表
```

### 9. 完整性检查示例

#### test_completeness_check.py

演示数据完整性检查。

```python
# 使用方式
python examples/test_completeness_check.py

# 功能
- 检查必填字段
- 验证数据格式
- 返回缺失项
```

### 10. 阶段测试示例

#### test_stage3_e2e.py

端到端完整流程测试。

```python
# 使用方式
python examples/test_stage3_e2e.py

# 功能
- 完整业务流程
- 从上传到报表
- 验证所有环节
```

## 🧪 测试技巧

### 1. 使用 Mock 数据

```python
from unittest.mock import Mock, patch

@patch('api_gateway.services.file_service.FileService')
async def test_with_mock(mock_service):
    mock_service.upload_file.return_value = {"success": True}
    # 测试代码
```

### 2. 异步测试

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### 3. 数据库事务

```python
from shared.database import get_db_connection

async def test_with_transaction():
    async with get_db_connection() as conn:
        async with conn.transaction():
            # 测试代码
            # 自动回滚
```

## 📝 编写新示例

### 示例模板

```python
"""
示例名称: XXX 功能示例
功能描述: 演示如何使用 XXX 功能
作者: Your Name
日期: 2026-02-22
"""

import asyncio
from shared.logging_config import get_logger

logger = get_logger(__name__)

async def main():
    """主函数"""
    try:
        logger.info("开始执行示例")
        
        # 示例代码
        result = await your_function()
        
        logger.info(f"执行结果: {result}")
        
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
```

### 最佳实践

1. **添加详细注释** - 解释每个步骤
2. **错误处理** - 捕获和记录异常
3. **日志记录** - 记录关键步骤
4. **清理资源** - 使用 try-finally
5. **独立运行** - 不依赖其他示例

## 🔍 调试技巧

### 启用详细日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 使用断点

```python
import pdb
pdb.set_trace()  # 设置断点
```

### 打印中间结果

```python
print(f"中间结果: {result}")
logger.debug(f"调试信息: {data}")
```

## 📚 相关文档

- [API Gateway 文档](../api_gateway/README.md)
- [Agents 文档](../agents/README.md)
- [主项目文档](../README.md)

## 🤝 贡献示例

1. 创建新的示例文件
2. 添加详细注释
3. 测试示例代码
4. 更新本 README
5. 提交 Pull Request

## 📞 获取帮助

如有问题，请：
- 查看相关文档
- 运行示例代码
- 提交 Issue

---

**最后更新**: 2026-02-22  
**维护者**: 示例代码团队
