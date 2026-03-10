# 路径配置指南

## 📋 概述

为了方便不同开发环境下的部署和测试，板料线模块将所有绝对路径配置集中到 `path_config.py` 文件中管理。

## 🎯 配置目标

- ✅ 集中管理所有绝对路径
- ✅ 支持多环境配置（开发、测试、生产）
- ✅ 避免硬编码路径
- ✅ 提供路径检查和自动创建功能
- ✅ 不将个人路径配置提交到版本控制

## 📁 相关文件

```
banliaoxian/
├── path_config.py              # 实际配置文件（不提交到 git）
├── path_config.example.py      # 配置示例文件（提交到 git）
├── .gitignore                  # 忽略 path_config.py
└── PATH_CONFIG_GUIDE.md        # 本文档
```

## 🚀 快速开始

### 1. 复制配置文件

```bash
cd mold_cost_/scripts/banliaoxian
```

### 2. 编辑配置

打开 `path_config.py`，修改以下关键配置：

```python
# ODA File Converter 路径
ODA_CONVERTER_PATH = r"D:\your_path\ODAFileConverter.exe"

# 测试文件目录
TEST_DXF_DIR = r"D:\your_path\test_files"
```

### 3. 运行环境检查

```bash
python path_config.py
```

查看输出，确认所有路径配置正确。

## 📝 配置项说明

### 外部工具路径

```python
# ODA File Converter 主路径
ODA_CONVERTER_PATH = r"D:\workspace\ODA\ODAFileConverter.exe"

# 备用路径（按顺序尝试）
ODA_CONVERTER_FALLBACK_PATHS = [
    r"D:\workspace\ODA\ODAFileConverter.exe",
    r"C:\Program Files\ODA\ODAFileConverter.exe",
]
```

**说明**：
- 用于 DWG → DXF 转换
- 如果主路径不存在，会自动尝试备用路径
- 可以添加多个备用路径

### 测试文件路径

```python
# 测试文件目录
TEST_DXF_DIR = r"D:\my_project\cadagent\sheet_line"

# 测试文件映射
TEST_FILES = {
    'ceshitu': os.path.join(TEST_DXF_DIR, 'ceshitu.dxf'),
    'M250286_P8': os.path.join(TEST_DXF_DIR, 'M250286-P8-20260203.dxf'),
}
```

**说明**：
- 用于单元测试和集成测试
- 可以添加自定义测试文件
- 使用键名访问：`get_test_file('ceshitu')`

### 输出路径

```python
# 默认输出目录
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output', 'banliaoxian')

# 日志目录
DEFAULT_LOG_DIR = os.path.join(PROJECT_ROOT, 'logs', 'banliaoxian')

# 失败文件目录
DEFAULT_FAIL_DIR = os.path.join(DEFAULT_OUTPUT_DIR, 'fail_file')
```

**说明**：
- 相对于项目根目录
- 会自动创建（如果不存在）
- 可以修改为任意目录

## 🔧 工具函数

### get_oda_converter_path()

获取 ODA File Converter 路径，自动检测主路径和备用路径。

```python
from path_config import get_oda_converter_path

oda_path = get_oda_converter_path()
print(f"ODA 路径: {oda_path}")
```

### get_test_file(file_key)

获取测试文件路径。

```python
from path_config import get_test_file

dxf_file = get_test_file('ceshitu')
print(f"测试文件: {dxf_file}")
```

### ensure_output_dirs()

确保所有输出目录存在，如果不存在则自动创建。

```python
from path_config import ensure_output_dirs

ensure_output_dirs()
```

### get_output_path(filename, output_dir=None)

获取输出文件的完整路径。

```python
from path_config import get_output_path

output_file = get_output_path('result.dxf')
print(f"输出文件: {output_file}")
```

### check_environment()

检查环境配置是否正确，打印详细信息。

```python
from path_config import check_environment

check_environment()
```

## 🔄 使用示例

### 在脚本中使用

```python
# 导入路径配置
try:
    from path_config import get_oda_converter_path, get_test_file
    
    # 获取 ODA 路径
    oda_path = get_oda_converter_path()
    
    # 获取测试文件
    dxf_file = get_test_file('ceshitu')
    
except ImportError:
    # 如果无法导入配置，使用默认路径
    print("⚠️ 警告: 无法导入 path_config，使用默认路径")
    oda_path = r"D:\my_project\ODAFileConverter.exe"
    dxf_file = r"D:\my_project\test.dxf"
```

### 在测试代码中使用

```python
if __name__ == "__main__":
    try:
        from path_config import get_test_file, DEFAULT_OUTPUT_DIR
        
        # 使用配置的路径
        dxf_file = get_test_file('ceshitu')
        output_dir = DEFAULT_OUTPUT_DIR
        
    except (ImportError, KeyError):
        # 回退到默认路径
        print("⚠️ 警告: 使用默认测试路径")
        dxf_file = "test.dxf"
        output_dir = "./output"
    
    # 处理文件
    process_file(dxf_file, output_dir)
```

## 🌍 多环境配置

### 开发环境

```python
# path_config.py (开发环境)
ODA_CONVERTER_PATH = r"D:\dev\ODA\ODAFileConverter.exe"
TEST_DXF_DIR = r"D:\dev\test_files"
```

### 测试环境

```python
# path_config.py (测试环境)
ODA_CONVERTER_PATH = r"C:\test\ODA\ODAFileConverter.exe"
TEST_DXF_DIR = r"C:\test\dxf_files"
```

### 生产环境

```python
# path_config.py (生产环境)
ODA_CONVERTER_PATH = r"C:\Program Files\ODA\ODAFileConverter.exe"
TEST_DXF_DIR = r"C:\production\data"
```

## ⚠️ 注意事项

### Windows 路径

使用原始字符串（`r"..."`）或双反斜杠（`"\\\\"`）：

```python
# 推荐：原始字符串
path = r"D:\my_project\file.dxf"

# 或者：双反斜杠
path = "D:\\my_project\\file.dxf"

# 错误：单反斜杠会被转义
path = "D:\my_project\file.dxf"  # ❌
```

### Linux/Mac 路径

使用正斜杠（`"/"`）：

```python
path = "/home/user/project/file.dxf"
```

### 相对路径

相对路径会自动转换为绝对路径：

```python
# 相对于项目根目录
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output', 'banliaoxian')
```

### 路径检查

使用前检查路径是否存在：

```python
import os

if not os.path.exists(dxf_file):
    print(f"❌ 文件不存在: {dxf_file}")
    print("💡 提示: 请在 path_config.py 中配置正确的路径")
```

## 🐛 常见问题

### 1. ImportError: No module named 'path_config'

**原因**：`path_config.py` 文件不存在

**解决**：
```bash
cp path_config.example.py path_config.py
```

### 2. KeyError: 未知的测试文件键名

**原因**：测试文件键名不存在

**解决**：
```python
# 在 path_config.py 中添加测试文件
TEST_FILES = {
    'your_file': os.path.join(TEST_DXF_DIR, 'your_file.dxf'),
}
```

### 3. ODA File Converter 未找到

**原因**：ODA 路径配置错误

**解决**：
1. 检查 ODA 是否已安装
2. 在 `path_config.py` 中配置正确的路径
3. 添加备用路径到 `ODA_CONVERTER_FALLBACK_PATHS`

### 4. 输出目录创建失败

**原因**：权限不足或路径无效

**解决**：
1. 检查目录路径是否有效
2. 确保有写入权限
3. 手动创建目录

## 📚 最佳实践

1. **不要提交个人配置**
   - `path_config.py` 已添加到 `.gitignore`
   - 只提交 `path_config.example.py`

2. **使用工具函数**
   - 使用 `get_oda_converter_path()` 而不是直接访问 `ODA_CONVERTER_PATH`
   - 使用 `get_test_file()` 而不是直接访问 `TEST_FILES`

3. **提供回退方案**
   - 在无法导入配置时使用默认路径
   - 显示警告信息

4. **运行环境检查**
   - 首次配置后运行 `python path_config.py`
   - 定期检查配置是否正确

5. **文档化自定义配置**
   - 在团队文档中说明特殊配置
   - 提供配置示例

## 🔄 更新日志

- **2026-03-10**：创建路径配置系统
  - 提取所有绝对路径到 `path_config.py`
  - 添加配置示例文件
  - 添加环境检查功能
  - 更新所有脚本使用新配置

## 📞 支持

如有问题或建议，请联系开发团队。

---

**最后更新**：2026-03-10  
**维护者**：Kiro AI
