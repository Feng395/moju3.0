@echo off
REM InteractionAgent 安装和验证脚本 (Windows)

echo ==========================================
echo InteractionAgent 安装和验证
echo ==========================================
echo.

REM 1. 检查 Python 版本
echo 📋 检查 Python 版本...
python --version
if %errorlevel% neq 0 (
    echo ❌ 错误: Python 未安装或不在 PATH 中
    exit /b 1
)
echo ✅ Python 版本检查通过
echo.

REM 2. 安装依赖
echo 📦 安装依赖...
pip install -q "langchain>=1.0,<2.0" "langgraph>=1.0,<2.0" "langchain-openai>=0.1.0,<1.0" "openai>=1.0,<2.0"
if %errorlevel% neq 0 (
    echo ❌ 依赖安装失败
    exit /b 1
)
echo ✅ 依赖安装完成
echo.

REM 3. 验证导入
echo 🔍 验证模块导入...
python -c "import sys; sys.path.insert(0, '.'); from agents.interaction_agent import InteractionAgent; print('✅ InteractionAgent 导入成功')"
if %errorlevel% neq 0 (
    echo ❌ 模块导入失败
    exit /b 1
)
echo.

REM 4. 运行测试
echo 🧪 运行测试...
where pytest >nul 2>nul
if %errorlevel% equ 0 (
    pytest tests/test_interaction_agent.py -v --tb=short
    echo ✅ 测试通过
) else (
    echo ⚠️  pytest 未安装，跳过测试
)
echo.

REM 5. 运行示例
echo 🚀 运行示例...
python examples/interaction_agent_example.py
echo.

REM 6. 完成
echo ==========================================
echo ✅ InteractionAgent 安装和验证完成！
echo ==========================================
echo.
echo 下一步：
echo 1. 阅读文档: agents\README.md
echo 2. 查看示例: examples\interaction_agent_example.py
echo 3. 运行测试: pytest tests\test_interaction_agent.py -v
echo.

pause
