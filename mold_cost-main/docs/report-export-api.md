# 价格报表导出API文档

## 概述

价格报表导出功能支持两种模式：
- **同步导出**：适用于小型报表（<100个子图），立即返回Excel文件
- **异步导出**：适用于大型报表（>=100个子图），后台生成，通过轮询获取结果

系统会根据子图数量自动选择合适的模式，也可以手动指定。

## API端点

### 导出价格报表

**端点**: `GET /api/v1/reports/{job_id}/export`

**描述**: 导出指定任务的价格报表为Excel文件

**参数**:
- `job_id` (路径参数, 必需): 任务ID (UUID格式)
- `format` (查询参数, 可选): 导出格式，默认为 `xlsx`
  - `xlsx`: Excel格式 (当前支持)
  - `csv`: CSV格式 (暂不支持)

**响应**:
- 成功: 返回Excel文件流，文件名格式为 `M{文件名}_报价单_{日期}.xlsx`
- 失败: 返回错误信息

**状态码**:
- `200`: 成功
- `404`: 任务不存在或没有子图数据
- `400`: 不支持的格式
- `500`: 服务器错误

## 使用示例

### 1. 使用命令行下载报表

#### Linux/Mac (bash)
```bash
# 导出Excel格式
curl -X GET "http://localhost:8000/api/v1/reports/{job_id}/export?format=xlsx" \
  -o report.xlsx

# 使用实际的job_id
curl -X GET "http://localhost:8000/api/v1/reports/550e8400-e29b-41d4-a716-446655440000/export" \
  -o report.xlsx
```

#### Windows PowerShell
```powershell
# 方法1: 使用 Invoke-WebRequest
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/reports/{job_id}/export" -OutFile report.xlsx

# 方法2: 使用简写
iwr "http://localhost:8000/api/v1/reports/{job_id}/export" -OutFile report.xlsx

# 方法3: 使用 curl.exe (如果已安装)
curl.exe -X GET "http://localhost:8000/api/v1/reports/{job_id}/export" -o report.xlsx

# 方法4: 使用测试脚本
.\scripts\test_report_export.ps1 -JobId "550e8400-e29b-41d4-a716-446655440000"
```

### 2. 使用Python测试脚本

```bash
# 导出指定任务的报表
python scripts/test_report_export.py <job_id>

# 列出所有可用任务
python scripts/test_report_export.py --list

# 示例
python scripts/test_report_export.py 550e8400-e29b-41d4-a716-446655440000
```

### 3. 使用Python requests库

```python
import requests

job_id = "550e8400-e29b-41d4-a716-446655440000"
url = f"http://localhost:8000/api/v1/reports/{job_id}/export"

response = requests.get(url, params={"format": "xlsx"})

if response.status_code == 200:
    with open("report.xlsx", "wb") as f:
        f.write(response.content)
    print("报表下载成功")
else:
    print(f"下载失败: {response.json()}")
```

### 4. 使用JavaScript/Fetch

```javascript
const jobId = "550e8400-e29b-41d4-a716-446655440000";
const url = `http://localhost:8000/api/v1/reports/${jobId}/export?format=xlsx`;

fetch(url)
  .then(response => {
    if (!response.ok) throw new Error('下载失败');
    return response.blob();
  })
  .then(blob => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'report.xlsx';
    document.body.appendChild(a);
    a.click();
    a.remove();
  })
  .catch(error => console.error('错误:', error));
```

## 报表格式

导出的Excel报表包含以下内容：

### 标题行
- 格式: `M{文件名} P4 {日期}模具核算清单`

### 数据列
1. 序号
2. 零件名称
3. 编号
4. 材质
5. 长/mm
6. 宽/mm
7. 厚/mm
8. 数量
9. 实际重量/kg
10. 热处理
11. 工艺
12. 工艺说明
13. 工艺
14. 线割工艺说明
15. NC开粗(元)
16. NC精铣(元)
17. 钻床(元)
18. 铣床(元)
19. 大磨床(元)
20. 小磨床(元)
21. 慢丝(元)
22. 慢丝侧割(元)
23. 中丝(元)
24. 快丝(元)
25. 放电(元)
26. 雕刻(元)
27. 单独计费(元)
28. 加工费合计(元)
29. 精铣开粗备注
30. 3D精铣(h)
31. 3D精铣(元)
32. 3D开粗+除钻(h)
33. 3D开粗+除钻(元)

### 合计行
- 自动计算所有费用列的合计

## 数据来源

报表数据从以下数据库表获取：
- `jobs`: 任务基本信息
- `subgraphs`: 子图详细数据（零件信息、工艺、费用等）
- `features`: 特征数据（尺寸、重量等）

## 样式说明

- 标题: 14号加粗宋体，居中
- 表头: 11号加粗宋体，灰色背景，居中
- 数据: 10号宋体，居中（零件名称左对齐）
- 边框: 所有单元格带细边框
- 数字格式: 保留两位小数

## 错误处理

### 常见错误

1. **任务不存在**
   ```json
   {
     "detail": "任务不存在"
   }
   ```

2. **没有子图数据**
   ```json
   {
     "detail": "没有找到子图数据"
   }
   ```

3. **不支持的格式**
   ```json
   {
     "detail": "不支持的格式"
   }
   ```

## 性能考虑

- 大型报表（>1000行）可能需要较长时间生成
- 建议在后台任务中生成大型报表
- 考虑添加缓存机制避免重复生成

## 未来扩展

计划支持的功能：
- [ ] CSV格式导出
- [ ] PDF格式导出
- [ ] 自定义列选择
- [ ] 报表模板配置
- [ ] 批量导出多个任务
- [ ] 异步生成大型报表
- [ ] 报表缓存机制

## 相关文档

- [API Gateway文档](./project-structure.md)
- [数据库ER图](./数据库ER图.md)
- [系统架构](./system-architecture-interfaces.md)
