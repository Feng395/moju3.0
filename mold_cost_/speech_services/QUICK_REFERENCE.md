# 模具行业语音识别 - 快速参考

## 🚀 快速开始

```bash
# 1. 启动服务
cd mold_cost_/speech_services
python main.py --model small

# 2. 测试服务
curl http://localhost:8888/api/health

# 3. 运行测试
python test_mold_speech.py
```

## 📚 术语速查表

### 线切割工艺

| 正确术语 | 常见错误 |
|---------|---------|
| 慢丝割一修一 | 慢思割一修1、慢丝割一秀一 |
| 慢丝割一修二 | 慢思割一修2、慢丝割一秀二 |
| 快丝割一刀 | 快思割一道、快丝割1刀 |
| 中丝割一修一 | 中思割一修1、中丝割一秀一 |

### 材料材质

| 正确术语 | 常见错误 |
|---------|---------|
| Cr12MoV | CR12MOV、cr12mov |
| SKD11 | skd11、SKD 11 |
| P20 | p20、P 20 |
| 45# | 45号、四五号 |
| T00L0X44 | TOOLOX44、t00l0x44 |

### 零件类型

| 正确术语 | 常见错误 |
|---------|---------|
| 上模板 | 上模版、上摸板 |
| 下模板 | 下模版、下摸板 |
| 导柱 | 导住、倒柱 |
| 导套 | 导头、倒套 |
| 冲头 | 充头、冲投 |

### 零件编号

| 正确术语 | 常见错误 |
|---------|---------|
| UP01 | up01、UP 01 |
| DIE-03 | die-03、DIE 03 |
| LP-02 | lp-02、LP 02 |
| PH2-04 | ph2-04、PH2 04 |

### 修改动作

| 正确术语 | 常见错误 |
|---------|---------|
| 改成 | 改称、盖成 |
| 改为 | 改围、改位 |
| 修改 | 休改、秀改 |
| 调整 | 条整、掉整 |
| 设置 | 设制、社置 |

### 查询关键词

| 正确术语 | 常见错误 |
|---------|---------|
| 怎么算 | 怎么蒜、怎么酸 |
| 详情 | 祥情、香情 |
| 明细 | 名细、铭细 |
| NC | nc、N C、恩西 |
| NC开粗 | NC开初、NC凯粗 |

### 概念词

| 正确术语 | 包含零件 |
|---------|---------|
| 冲头类 | 切边冲头、切冲冲头、冲子、废料刀、冲头 |
| 刀口入块 | 刀口入子、切边入子、冲孔入子、凹模 |
| 模架 | 模座、垫脚、托板 |

## 💬 使用示例

### 修改工艺

```
语音: "将这套的线割慢丝割一修二的单价改成0.0018"
识别: "将这套的线个慢思割一修2的单家改称0.0018"
修正: "将这套的线割慢丝割一修二的单价改成0.0018" ✅
```

### 修改材质

```
语音: "将DIE-03的材质改为Cr12MoV"
识别: "将die-03的材质改围CR12MOV"
修正: "将DIE-03的材质改为Cr12MoV" ✅
```

### 批量修改

```
语音: "冲头类的零件全部改成慢丝割一修一"
识别: "充头累的零件全部改称慢思割一修1"
修正: "冲头类的零件全部改成慢丝割一修一" ✅
```

### 查询计算

```
语音: "UP01的NC开粗怎么算的"
识别: "up01的nc开初怎么蒜的"
修正: "UP01的NC开粗怎么算的" ✅
```

## 🔧 API 使用

### Python

```python
import requests

with open('audio.wav', 'rb') as f:
    response = requests.post(
        'http://localhost:8888/api/transcribe',
        files={'file': f},
        data={'model': 'small', 'language': 'zh', 'fix_terms': 'true'}
    )
    
result = response.json()
print(result['text'])
```

### cURL

```bash
curl -X POST http://localhost:8888/api/transcribe \
  -F "file=@audio.wav" \
  -F "model=small" \
  -F "language=zh" \
  -F "fix_terms=true"
```

### JavaScript

```javascript
const formData = new FormData();
formData.append('file', audioFile);
formData.append('model', 'small');
formData.append('language', 'zh');
formData.append('fix_terms', 'true');

fetch('http://localhost:8888/api/transcribe', {
  method: 'POST',
  body: formData
})
.then(res => res.json())
.then(data => console.log(data.text));
```

## 📊 模型选择

| 模型 | 速度 | 准确率 | 内存 | 推荐场景 |
|------|------|--------|------|----------|
| tiny | ⚡⚡⚡⚡⚡ | ⭐⭐ | 1GB | 快速测试 |
| base | ⚡⚡⚡⚡ | ⭐⭐⭐ | 2GB | 实时应用 |
| small | ⚡⚡⚡ | ⭐⭐⭐⭐ | 4GB | 推荐使用 ⭐ |
| medium | ⚡⚡ | ⭐⭐⭐⭐⭐ | 8GB | 高准确率 |
| large | ⚡ | ⭐⭐⭐⭐⭐ | 16GB | 专业场景 |

## 🐛 常见问题

### Q: 识别结果为空？

**A**: 检查以下几点：
- 录音时间是否太短（建议至少 1-2 秒）
- 音量是否太小
- 音频格式是否支持（wav, mp3, m4a 等）

### Q: 术语修正不生效？

**A**: 确认：
- `fix_terms` 参数设置为 `true`
- 字典文件存在且格式正确
- 查看日志确认字典加载成功

### Q: 识别速度慢？

**A**: 尝试：
- 使用更小的模型（tiny 或 base）
- 启用 GPU 加速
- 减少音频文件大小

### Q: 如何添加自定义术语？

**A**: 编辑 `dictionaries/mold_industry_terms.json`：
```json
"新术语": {
  "correct": "新术语",
  "description": "说明",
  "variants": [
    {"wrong": "错误识别", "description": "原因"}
  ]
}
```

## 📁 文件结构

```
speech_services/
├── dictionaries/
│   ├── mold_industry_terms.json    # 模具行业字典 ⭐
│   └── programmer_terms.json       # 程序员术语字典
├── config/
│   ├── base_config.json            # 基础配置
│   ├── base_dict.json              # 基础词库 ⭐
│   └── user_dict.json              # 用户学习词库
├── core/
│   ├── dict_manager.py             # 字典管理器 ⭐
│   ├── transcriber.py              # 转录器
│   └── ...
├── main.py                         # 服务入口
├── test_mold_speech.py             # 测试脚本 ⭐
├── MOLD_INDUSTRY_OPTIMIZATION.md   # 优化指南 ⭐
├── OPTIMIZATION_SUMMARY.md         # 优化总结 ⭐
└── QUICK_REFERENCE.md              # 本文件 ⭐
```

## 🎯 测试清单

- [ ] 启动服务成功
- [ ] 健康检查通过
- [ ] 运行测试脚本全部通过
- [ ] 测试实际音频文件
- [ ] 验证术语修正效果
- [ ] 检查学习功能
- [ ] 查看统计信息

## 📞 获取帮助

- 详细文档: [MOLD_INDUSTRY_OPTIMIZATION.md](MOLD_INDUSTRY_OPTIMIZATION.md)
- 优化总结: [OPTIMIZATION_SUMMARY.md](OPTIMIZATION_SUMMARY.md)
- 服务文档: [README.md](README.md)
- 快速开始: [QUICKSTART.md](QUICKSTART.md)

---

**版本**: 1.0.0 | **更新**: 2026-02-28
