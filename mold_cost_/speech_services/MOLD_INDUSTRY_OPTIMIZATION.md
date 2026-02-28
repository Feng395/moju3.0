# 模具行业语音识别优化指南

## 📋 概述

本文档说明如何针对模具成本核算系统优化语音识别服务，基于 `USER_MODIFICATION_EXAMPLES.md` 中的实际使用场景进行优化。

## 🎯 优化目标

1. 准确识别模具行业专业术语
2. 支持用户修改指令的语音输入
3. 支持查询计算过程的语音输入
4. 提高中文混合数字、英文的识别准确率

## 📚 术语字典结构

### 字典文件位置

```
mold_cost_/speech_services/dictionaries/mold_industry_terms.json
```

### 字典分类

字典按照以下类别组织，共 9 大类，覆盖 100+ 术语：

#### 1. 线切割工艺 (wire_cutting_process)
- 慢丝割一刀、慢丝割一修一、慢丝割一修二、慢丝割一修三
- 快丝割一刀
- 中丝割一修一、中丝割一修二、中丝割二修二
- 慢丝、快丝、中丝、线割

**常见误识别**：
- "慢丝" → "慢思"、"慢死"
- "割一刀" → "割一道"、"割1刀"
- "修一" → "秀一"、"休一"、"修1"

#### 2. 材料材质 (materials)
- Cr12MoV、SKD11、P20、718、S136、45#
- T00L0X44、T00L0X33

**常见误识别**：
- "Cr12MoV" → "CR12MOV"、"cr12mov"
- "45#" → "45号"、"四五号"
- "T00L0X44" → "TOOLOX44"（数字0识别为字母O）

#### 3. 零件类型 (part_types)
- 上模板、下模板、导柱、导套
- 冲头、镶件、滑块、斜顶
- 下夹板、下模座

**常见误识别**：
- "模板" → "模版"、"摸板"
- "导柱" → "导住"、"倒柱"
- "冲头" → "充头"、"冲投"

#### 4. 零件编号 (part_codes)
- UP01、UP02、UP03
- DIE-03、DIE-04
- LP-02、PH2-04

**常见误识别**：
- "UP01" → "up01"、"UP 01"、"UP零一"
- "DIE-03" → "die-03"、"DIE 03"、"DIE03"

#### 5. 尺寸单位 (dimensions)
- mm、长度、宽度、厚度

**常见误识别**：
- "mm" → "MM"、"毫米"、"m m"
- "长度" → "常度"
- "厚度" → "后度"

#### 6. 修改动作 (modification_actions)
- 改成、改为、修改、调整、设置

**常见误识别**：
- "改成" → "改称"、"盖成"
- "修改" → "休改"、"秀改"
- "调整" → "条整"、"掉整"

#### 7. 查询关键词 (query_keywords)
- 怎么算、详情、明细、计算过程
- NC、NC开粗、NC精铣、NC钻床

**常见误识别**：
- "怎么算" → "怎么蒜"、"怎么酸"
- "详情" → "祥情"、"香情"
- "NC" → "nc"、"N C"、"恩西"

#### 8. 概念词 (concept_keywords)
- 冲头类、刀口入块、模架
- 切边冲头、废料刀、刀口入子
- 切边入子、冲孔入子、凹模
- 模座、垫脚、托板

**用途**：用于批量修改，如"冲头类都改成慢丝割一修二"

**常见误识别**：
- "冲头类" → "冲头累"、"充头类"
- "刀口入块" → "刀口入快"
- "模架" → "摸架"、"模加"

#### 9. 价格术语 (price_terms)
- 单价、价格、按重量计算、重量计算

**常见误识别**：
- "单价" → "单家"、"丹价"
- "按重量计算" → "按重量计蒜"

## 🔧 使用方法

### 1. 加载模具行业字典

修改 `dict_manager.py` 以支持加载模具行业字典：

```python
# 在 DictionaryManager 类中添加
def _get_dict_file_path(self) -> Optional[str]:
    """获取字典文件路径"""
    if self.dict_path:
        return self.dict_path
    
    # 优先加载模具行业字典
    root = get_project_root()
    mold_dict = os.path.join(root, 'dictionaries', 'mold_industry_terms.json')
    if os.path.exists(mold_dict):
        return mold_dict
    
    # 回退到程序员术语字典
    default_path = os.path.join(root, 'dictionaries', 'programmer_terms.json')
    return default_path if os.path.exists(default_path) else None
```

### 2. 配置提示词

在 `config/base_config.json` 中配置：

```json
{
  "prompt_prefix": "模具成本核算系统用户：",
  "user_dict_path": "config/user_dict.json",
  "base_dict_path": "config/base_dict.json",
  "max_user_terms": 30,
  "prompt_total_terms": 15,
  "prompt_base_terms": 10,
  "user_term_min_freq": 2
}
```

### 3. 更新基础词库

在 `config/base_dict.json` 中添加常用术语：

```json
{
  "terms": [
    "模具", "线切割", "慢丝", "快丝", "中丝",
    "慢丝割一修一", "慢丝割一修二", "慢丝割一修三",
    "快丝割一刀", "中丝割一修一",
    "Cr12MoV", "SKD11", "P20", "718", "45#",
    "上模板", "下模板", "导柱", "导套", "冲头",
    "UP01", "UP02", "DIE-03", "LP-02",
    "改成", "改为", "修改", "调整", "设置",
    "怎么算", "详情", "明细", "计算过程",
    "NC", "NC开粗", "NC精铣", "NC钻床",
    "单价", "价格", "按重量计算"
  ]
}
```

## 📝 实际使用示例

### 示例 1：修改工艺

**用户语音**：
```
"将这套的线割慢丝割一修二的单价改成0.0018"
```

**识别前可能的错误**：
```
"将这套的线个慢思割一修2的单家改称0.0018"
```

**术语修正后**：
```
"将这套的线割慢丝割一修二的单价改成0.0018"
```

**修正详情**：
- "线个" → "线割"
- "慢思" → "慢丝"
- "修2" → "修二"
- "单家" → "单价"
- "改称" → "改成"

### 示例 2：修改材质

**用户语音**：
```
"将DIE-03的材质改为Cr12mov"
```

**识别前可能的错误**：
```
"将die-03的材质改围CR12MOV"
```

**术语修正后**：
```
"将DIE-03的材质改为Cr12MoV"
```

**修正详情**：
- "die-03" → "DIE-03"
- "改围" → "改为"
- "CR12MOV" → "Cr12MoV"

### 示例 3：批量修改

**用户语音**：
```
"冲头类的零件全部改成慢丝割一修一"
```

**识别前可能的错误**：
```
"充头累的零件全部改称慢思割一修1"
```

**术语修正后**：
```
"冲头类的零件全部改成慢丝割一修一"
```

**修正详情**：
- "充头累" → "冲头类"
- "改称" → "改成"
- "慢思" → "慢丝"
- "修1" → "修一"

### 示例 4：查询计算过程

**用户语音**：
```
"UP01的NC开粗怎么算的"
```

**识别前可能的错误**：
```
"up01的nc开初怎么蒜的"
```

**术语修正后**：
```
"UP01的NC开粗怎么算的"
```

**修正详情**：
- "up01" → "UP01"
- "nc" → "NC"
- "开初" → "开粗"
- "怎么蒜" → "怎么算"

## 🎨 字典维护

### 添加新术语

1. 打开 `mold_industry_terms.json`
2. 找到对应的类别
3. 添加新术语：

```json
"新术语": {
  "correct": "新术语",
  "description": "术语说明",
  "variants": [
    {"wrong": "错误识别1", "description": "误识别原因"},
    {"wrong": "错误识别2", "description": "误识别原因"}
  ]
}
```

### 添加新类别

```json
"new_category": {
  "name": "新类别名称",
  "description": "类别说明",
  "terms": {
    // 术语定义
  }
}
```

## 📊 性能优化建议

### 1. 模型选择

根据场景选择合适的模型：

| 场景 | 推荐模型 | 原因 |
|------|---------|------|
| 实时语音输入 | small | 速度快，准确率较高 |
| 离线批量处理 | medium | 准确率更高 |
| 专业场景 | large | 最高准确率 |

### 2. 提示词优化

在转录时使用行业术语作为提示词：

```python
whisper = get_whisper_instance("small")
result = whisper.transcribe(
    audio_file,
    language="zh",
    initial_prompt="模具成本核算系统：慢丝割一修一、快丝割一刀、Cr12MoV、SKD11、P20"
)
```

### 3. 学习功能

启用学习功能，系统会自动记录用户常用术语：

```python
result = whisper.transcribe(
    audio_file,
    fix_programmer_terms=True,
    learn_user_terms=True  # 启用学习
)
```

## 🔍 测试验证

### 测试脚本

创建 `test_mold_speech.py`：

```python
from speech_services.core.transcriber import CodeWhisper

# 初始化
whisper = CodeWhisper(model_name="small")

# 测试用例
test_cases = [
    "将这套的线割慢丝割一修二的单价改成0.0018",
    "将DIE-03的材质改为Cr12mov",
    "冲头类的零件全部改成慢丝割一修一",
    "UP01的NC开粗怎么算的"
]

for text in test_cases:
    # 模拟识别后的文本（带错误）
    result = whisper.dict_manager.fix_text(text)
    print(f"原文: {text}")
    print(f"修正: {result}")
    print(f"修正数: {whisper.dict_manager.stats['replacements_made']}")
    print("---")
```

### 预期结果

所有测试用例应该正确识别并修正术语。

## 📈 统计信息

查看术语修正统计：

```python
stats = whisper.get_dict_stats()
print(f"总规则数: {stats['total_rules']}")
print(f"修正次数: {stats['replacements_made']}")

categories = whisper.get_dict_categories()
for cat, count in categories.items():
    print(f"{cat}: {count} 条规则")
```

## 🚀 部署建议

### 1. 生产环境配置

```bash
# 使用 medium 模型以获得更高准确率
python main.py --model medium --host 0.0.0.0 --port 8888
```

### 2. Docker 部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py", "--model", "small", "--host", "0.0.0.0"]
```

### 3. 监控和日志

启用详细日志以监控识别效果：

```python
result = whisper.transcribe(
    audio_file,
    verbose=True  # 启用详细日志
)
```

## 💡 最佳实践

1. **定期更新字典**：根据用户反馈添加新的误识别模式
2. **使用学习功能**：让系统自动学习用户习惯
3. **提供反馈机制**：允许用户报告识别错误
4. **A/B 测试**：对比不同模型和配置的效果
5. **性能监控**：记录识别准确率和响应时间

## 📞 技术支持

如有问题，请查看：
- [语音服务 README](README.md)
- [快速开始指南](QUICKSTART.md)
- [用户修改示例](../../USER_MODIFICATION_EXAMPLES.md)

---

**最后更新**：2026-02-28
**版本**：1.0.0
