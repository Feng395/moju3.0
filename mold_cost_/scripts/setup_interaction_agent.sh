#!/bin/bash
# InteractionAgent 安装和验证脚本

set -e

echo "=========================================="
echo "InteractionAgent 安装和验证"
echo "=========================================="
echo ""

# 1. 检查 Python 版本
echo "📋 检查 Python 版本..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "   Python 版本: $python_version"

if [[ $(python -c "import sys; print(sys.version_info >= (3, 8))") != "True" ]]; then
    echo "❌ 错误: 需要 Python 3.8 或更高版本"
    exit 1
fi
echo "✅ Python 版本检查通过"
echo ""

# 2. 安装依赖
echo "📦 安装依赖..."
pip install -q "langchain>=1.0,<2.0" "langgraph>=1.0,<2.0" "langchain-openai>=0.1.0,<1.0" "openai>=1.0,<2.0"
echo "✅ 依赖安装完成"
echo ""

# 3. 验证导入
echo "🔍 验证模块导入..."
python -c "
import sys
sys.path.insert(0, '.')

try:
    from agents.interaction_agent import InteractionAgent
    print('✅ InteractionAgent 导入成功')
except ImportError as e:
    print(f'❌ 导入失败: {e}')
    sys.exit(1)
"
echo ""

# 4. 运行测试
echo "🧪 运行测试..."
if command -v pytest &> /dev/null; then
    pytest tests/test_interaction_agent.py -v --tb=short
    echo "✅ 测试通过"
else
    echo "⚠️  pytest 未安装，跳过测试"
fi
echo ""

# 5. 运行示例
echo "🚀 运行示例..."
python examples/interaction_agent_example.py
echo ""

# 6. 完成
echo "=========================================="
echo "✅ InteractionAgent 安装和验证完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 阅读文档: agents/README.md"
echo "2. 查看示例: examples/interaction_agent_example.py"
echo "3. 运行测试: pytest tests/test_interaction_agent.py -v"
echo ""
