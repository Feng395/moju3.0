# 板料线生成系统备份

备份时间：2026-03-10

## 系统说明

这是完整的板料线自动生成系统，包含以下核心功能：

### 核心文件

1. **dxf_auto_sheetline.py** - 主处理脚本
   - 集成三重条件系统和精密L/W/T提取器
   - 支持多零件模式
   - 自动识别视图并添加板料线

2. **triple_condition_processor_optimized.py** - 三重条件处理器
   - 性能优化版本（网格索引去重）
   - 支持大尺寸视图（最大5000mm）
   - 大尺寸视图优先策略

3. **triple_condition_config.py** - 配置文件
   - 三重条件参数配置
   - 容差和阈值设置

4. **subgraph_detector.py** - 子图检测器
   - 识别DXF中的独立子图
   - 用于多零件分离

5. **precision_lwt_extractor.py** - 精密L/W/T提取器
   - 高精度尺寸提取
   - 备用提取方案

6. **dwg_to_dxf_converter.py** - DWG转DXF工具
   - 使用ODA File Converter
   - 支持批量转换

7. **auto_process_dwg.py** - 自动化处理脚本
   - 一键完成：DWG转换 → 添加板料线 → 输出

### 使用方法

#### 方式1：自动化处理（推荐）
```bash
python auto_process_dwg.py
```

#### 方式2：手动指定文件
```bash
python dxf_auto_sheetline.py your_file.dxf
```

#### 方式3：使用默认文件
```bash
python dxf_auto_sheetline.py
```

### 输出说明

- 输出目录：`output/`
- 输出文件名：与输入文件相同
- 失败文件：`output/fail_file/`

### 性能优化

1. 网格索引去重（O(n²) → O(n)）
2. 限制跨图层矩形组合数量
3. 大尺寸视图优先（70%权重）
4. 早期过滤候选视图
5. 文件保存重试机制

### 配置

- 处理模式：`PROCESSING_MODE['triple_condition'] = True`
- 多零件模式：`multi_part_mode = True`
- 默认输入：`ceshitua3.dxf`

### 依赖

- Python 3.7+
- ezdxf
- numpy (可选)

### 更新日志

- 2026-03-10: 性能优化，解决KeyboardInterrupt问题
- 2026-03-10: 支持大尺寸视图（5000mm）
- 2026-03-10: 添加文件保存重试机制
- 2026-03-10: 支持命令行参数
