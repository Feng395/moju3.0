"""Src-owned 智能文本处理实现。"""

import re
from collections import Counter
from typing import Dict, List


class IntelligentTextProcessor:
    """智能文字处理器（过滤无效文本）"""

    def __init__(self):
        self.noise_patterns = [
            r"^\d+\.?\d*$",
            r"^[\d\.\-\+\s]+$",
            r"^\d+\.?\d*[LWTHDRC]$",
            r"^Φ\d+\.?\d*",
            r"^R\d+\.?\d*",
            r"^M\d+x",
            r"^\d+\.?\d*°$",
            r"^\d+\.?\d*mm$",
            r"^\d+\.?\d*[×xX]\d+\.?\d*",
            r".*深$",
            r".*攻$",
            r".*钻$",
        ]
        self.meaningful_keywords = [
            "品名",
            "编号",
            "材料",
            "热处理",
            "数量",
            "加工说明",
            "尺寸",
            "修改",
            "备注",
            "规格",
            "型号",
            "零件名称",
            "名称",
            "部件",
            "组件",
        ]

    def process_text_list(self, texts: List[Dict]) -> List[Dict]:
        """处理文本列表（过滤噪音）"""
        if not texts:
            return []
        counter = Counter([text["content"].strip() for text in texts])
        processed = []
        for text in texts:
            content = text["content"].strip()
            if self._should_keep_text(content, counter):
                processed.append(text)
        return processed

    def _should_keep_text(self, content: str, counter: Counter) -> bool:
        """判断是否保留文本"""
        if not content:
            return False
        if len(content) > 50:
            return False
        if any(keyword in content for keyword in self.meaningful_keywords):
            return True
        if any(re.match(pattern, content) for pattern in self.noise_patterns):
            return False
        if len(content) <= 3 and counter[content] > 8:
            return False
        if len(content) <= 1 and counter[content] > 3:
            return False
        return True
