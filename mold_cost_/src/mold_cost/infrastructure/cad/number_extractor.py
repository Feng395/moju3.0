"""Src-owned 图纸编号提取实现。"""

import re
from collections import Counter
from typing import Dict, List, Optional, Tuple


class ProfessionalDrawingNumberExtractor:
    """专业图纸编号提取器 + 子图文件名提取"""

    def __init__(self):
        # 中文说明：这里保留 legacy 规则顺序，确保迁移阶段提取结果保持一致。
        self.number_inline_res = [
            re.compile(r"^\s*编号\s*[：:]\s*(\S+)\s*$", re.IGNORECASE),
            re.compile(r"编号\s*[：:]\s*(\S+)", re.IGNORECASE),
            re.compile(r"编号\s*:\([^)]+\)_(\S+)", re.IGNORECASE),
        ]
        self.processing_inline_res = [
            re.compile(
                r"加工说明[^\r\n]*?[_\-\s]*([A-Za-z]{1,4}\d{1,3}(?:[-_][A-Za-z0-9]+)*)",
                re.IGNORECASE,
            ),
            re.compile(
                r"加工说明\s*(?:[：:]\s*)?(?:\([^)]*\)\s*)?([A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*)",
                re.IGNORECASE,
            ),
            re.compile(r"加工说明\s*(?:\([^)]*\)\s*)?[：:]\s*(\S+)", re.IGNORECASE),
        ]
        self.number_label_only_res = re.compile(r"^\s*编号\s*[:：]?\s*$", re.IGNORECASE)
        self.processing_label_only_res = re.compile(r"^\s*加工说明\s*[:：]?\s*$", re.IGNORECASE)
        self.processing_label_anchor_res = re.compile(r"^\s*加工说明.*$", re.IGNORECASE)

        self.confirm_code_res = [
            re.compile(
                r"("
                r"U[12](?:-\s*[A-Z0-9]+)?|"
                r"(?:UP|UB|PH|PU|PS|GU|LB|LP|EB|EJ|FB|CV|CJ|CB|PM)(?:-\s*[A-Z0-9]+)?|"
                r"(?:PPS|DIE|BOL|BOI)(?:-\s*[A-Z0-9]+)?|"
                r"B\d{2}(?:-\s*[A-Z0-9]+)?|"
                r"(?:DIE2|PPS2|PS2|PH2|LB2)(?:-\s*[A-Z0-9]+)?|"
                r"(?:UB_P|PH_P|PU_P|PPS_P|PS_P|GU_P|LB_P|DIE_P)(?:-\s*[A-Z0-9]+)?|"
                r"(?:DIE2_P|PPS2_P|PS2_P|PH2_P|LB2_P)(?:-\s*[A-Z0-9]+)?|"
                r"(?:UP_JIAT|PS_JIAT|LOW_JIAT)(?:-\s*[A-Z0-9]+)?|"
                r"(?:UP_ITEM|PSITEM|LOW_ITEM)(?:-\s*[A-Z0-9]+)?|"
                r"(?:STRIP|CAM)(?:-\s*[A-Z0-9]+)?|"
                r"ST[23](?:-\s*[A-Z0-9]+)?|"
                r"TEMP[12](?:-\s*[A-Z0-9]+)?|"
                r"[A-Z]-\d{1,3}(?:-\s*[A-Z0-9]+)?"
                r")(?=\s|$|[^\w-])",
                re.IGNORECASE,
            ),
            re.compile(
                r"(?:[\(_])"
                r"("
                r"U[12](?:-\s*[A-Z0-9]+)?|"
                r"(?:UP|UB|PH|PU|PS|GU|LB|LP|EB|EJ|FB|CV|CJ|CB|PM)(?:-\s*[A-Z0-9]+)?|"
                r"(?:PPS|DIE|BOL|BOI)(?:-\s*[A-Z0-9]+)?|"
                r"B\d{2}(?:-\s*[A-Z0-9]+)?|"
                r"(?:DIE2|PPS2|PS2|PH2|LB2)(?:-\s*[A-Z0-9]+)?|"
                r"(?:UB_P|PH_P|PU_P|PPS_P|PS_P|GU_P|LB_P|DIE_P)(?:-\s*[A-Z0-9]+)?|"
                r"(?:DIE2_P|PPS2_P|PS2_P|PH2_P|LB2_P)(?:-\s*[A-Z0-9]+)?|"
                r"(?:UP_JIAT|PS_JIAT|LOW_JIAT)(?:-\s*[A-Z0-9]+)?|"
                r"(?:UP_ITEM|PSITEM|LOW_ITEM)(?:-\s*[A-Z0-9]+)?|"
                r"(?:STRIP|CAM)(?:-\s*[A-Z0-9]+)?|"
                r"ST[23](?:-\s*[A-Z0-9]+)?|"
                r"TEMP[12](?:-\s*[A-Z0-9]+)?|"
                r"[A-Z]-\d{1,3}(?:-\s*[A-Z0-9]+)?"
                r")(?=\s|$|[^\w-])",
                re.IGNORECASE,
            ),
        ]

        self.primary_patterns = [
            r"PH-[A-Z0-9]+",
            r"DIE-[A-Z0-9]+",
            r"[A-Z]{1,2}[0-9]{1,3}-[A-Z]{1,2}",
            r"[A-Z]{1,2}[0-9]{2,3}",
            r"[A-Z]{2,4}-[0-9]{1,3}",
        ]

        self.excluded_terms = {
            "图纸", "设计", "审核", "标准", "规格", "材料", "备注", "品名", "编号",
            "数量", "热处理", "修改", "尺寸", "所有", "全周", "已订购",
            "TITLE", "DRAWING", "DESIGN", "SCALE", "DATE", "制图", "日期",
            "单位", "比例", "共页", "第页", "版本", "PCS", "深", "攻", "钻",
            "割", "铰", "倒角", "沉头", "背", "穿", "让位", "合销", "导套",
            "螺丝", "基准", "弹簧", "定位", "精铣", "慢丝", "线割", "垂直度",
            "位置度", "加工", "夹板", "入子", "连接块", "外形", "绿色", "虚线",
            "直身", "拼装", "零件", "模板", "精磨",
        }

        self.cad_annotations = {
            "M", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10",
            "G", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9",
            "L", "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9",
            "U", "U1", "U2", "U3", "U4", "U5", "X", "X1", "X2", "X3", "X4", "X5", "X6", "X7", "X8", "X9",
            "K", "K1", "K2", "K3", "K4", "K5", "A", "A1", "A2", "A3", "A4", "A5",
            "Q", "Q1", "Q2", "Q3", "Q4", "Q5", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9",
        }

    def _text_pos(self, text: Dict, fallback: Tuple[float, float]) -> Tuple[float, float]:
        position = text.get("position")
        if isinstance(position, (tuple, list)) and len(position) >= 2:
            try:
                return float(position[0]), float(position[1])
            except Exception:
                return fallback
        return fallback

    def _extract_inline(self, texts: List[Dict], regexes: List[re.Pattern]) -> Optional[str]:
        for text in texts:
            content = (text.get("content") or "").strip()
            if not content:
                continue
            for regex in regexes:
                match = regex.search(content)
                if match and match.group(1):
                    candidate = self._clean_candidate_after_label(match.group(1))
                    if self._validate_drawing_number(candidate):
                        return candidate
        return None

    def _extract_near_label(
        self,
        bounds: Dict,
        texts: List[Dict],
        label_only_re: re.Pattern,
    ) -> Optional[str]:
        if not texts:
            return None
        min_x, max_x = bounds.get("min_x", 0.0), bounds.get("max_x", 0.0)
        min_y, max_y = bounds.get("min_y", 0.0), bounds.get("max_y", 0.0)
        width = max(max_x - min_x, 1.0)
        height = max(max_y - min_y, 1.0)
        fallback = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)

        label_texts = []
        for text in texts:
            content = (text.get("content") or "").strip()
            if content and label_only_re.match(content):
                label_texts.append(text)
        if not label_texts:
            return None

        candidates = []
        for text in texts:
            content = (text.get("content") or "").strip()
            if not content:
                continue
            candidate = self._clean_candidate_after_label(content)
            if not self._validate_drawing_number(candidate):
                continue
            x_pos, y_pos = self._text_pos(text, fallback)
            candidates.append((candidate, x_pos, y_pos))
        if not candidates:
            return None

        best = None
        best_score = None
        for label_text in label_texts:
            label_x, label_y = self._text_pos(label_text, fallback)
            for candidate, x_pos, y_pos in candidates:
                dx = abs(x_pos - label_x)
                dy = abs(y_pos - label_y)
                same_line = dy <= height * 0.06
                right_side = x_pos >= label_x - width * 0.02
                below = y_pos <= label_y + height * 0.02

                score = (dy * 2.0 + dx)
                if same_line and right_side:
                    score *= 0.25
                elif below and right_side:
                    score *= 0.45
                if dx > width * 0.5 or dy > height * 0.5:
                    score *= 3.0

                if best_score is None or score < best_score:
                    best_score = score
                    best = candidate
        return best

    def _normalize_confirmed_code(self, code: str) -> str:
        normalized = (code or "").strip().upper()
        if not normalized:
            return ""
        normalized = re.sub(r"\s*-\s*", "-", normalized)
        normalized = re.sub(r"\s+", "", normalized)
        return normalized

    def _extract_confirmed_codes_from_text(self, text: str) -> List[str]:
        stripped_text = (text or "").strip()
        if not stripped_text:
            return []
        found: List[str] = []
        for regex in self.confirm_code_res:
            for match in regex.finditer(stripped_text):
                try:
                    group = match.group(1)
                except Exception:
                    group = None
                if not group:
                    continue
                code = self._normalize_confirmed_code(group)
                if code:
                    found.append(code)
        unique_codes: List[str] = []
        seen = set()
        for code in found:
            if code not in seen:
                unique_codes.append(code)
                seen.add(code)
        return unique_codes

    def _extract_near_label_confirmed(
        self,
        bounds: Dict,
        texts: List[Dict],
        label_re: re.Pattern,
    ) -> Optional[str]:
        if not texts:
            return None
        min_x, max_x = bounds.get("min_x", 0.0), bounds.get("max_x", 0.0)
        min_y, max_y = bounds.get("min_y", 0.0), bounds.get("max_y", 0.0)
        width = max(max_x - min_x, 1.0)
        height = max(max_y - min_y, 1.0)
        fallback = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)

        label_texts = []
        for text in texts:
            content = (text.get("content") or "").strip()
            if content and label_re.match(content):
                label_texts.append(text)
        if not label_texts:
            return None

        candidates: List[Tuple[str, float, float]] = []
        for text in texts:
            content = (text.get("content") or "").strip()
            if not content:
                continue
            codes = self._extract_confirmed_codes_from_text(content)
            if not codes:
                continue
            x_pos, y_pos = self._text_pos(text, fallback)
            for code in codes:
                candidates.append((code, x_pos, y_pos))
        if not candidates:
            return None

        best = None
        best_score = None
        for label_text in label_texts:
            label_x, label_y = self._text_pos(label_text, fallback)
            for code, x_pos, y_pos in candidates:
                dx = abs(x_pos - label_x)
                dy = abs(y_pos - label_y)
                same_line = dy <= height * 0.06
                right_side = x_pos >= label_x - width * 0.02
                below = y_pos <= label_y + height * 0.02

                score = (dy * 2.0 + dx)
                if same_line and right_side:
                    score *= 0.25
                elif below and right_side:
                    score *= 0.45
                if dx > width * 0.6 or dy > height * 0.6:
                    score *= 3.0

                if best_score is None or score < best_score:
                    best_score = score
                    best = code
        return best

    def _extract_from_top_left(self, bounds: Dict, texts: List[Dict]) -> Optional[str]:
        if not texts:
            return None
        min_x, max_x = bounds.get("min_x", 0.0), bounds.get("max_x", 0.0)
        min_y, max_y = bounds.get("min_y", 0.0), bounds.get("max_y", 0.0)
        width = max(max_x - min_x, 1.0)
        height = max(max_y - min_y, 1.0)
        fallback = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)

        x_cut = min_x + width * 0.35
        y_cut = max_y - height * 0.35
        corner_x, corner_y = min_x, max_y

        best = None
        best_distance = None
        for text in texts:
            content = (text.get("content") or "").strip()
            if not content:
                continue
            candidate = self._clean_candidate_after_label(content)
            if not self._validate_drawing_number(candidate):
                continue
            x_pos, y_pos = self._text_pos(text, fallback)
            if x_pos > x_cut or y_pos < y_cut:
                continue
            distance = ((x_pos - corner_x) ** 2 + (y_pos - corner_y) ** 2) ** 0.5
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best = candidate
        return best

    def extract_region_filename_by_patterns(self, subdrawing_data: Dict) -> Optional[str]:
        """按"编号">"加工说明">"左上角编号"优先级提取子图文件名"""
        texts = subdrawing_data.get("texts", []) or []
        bounds = subdrawing_data.get("bounds") or {}

        candidate = self._extract_inline(texts, self.number_inline_res)
        if candidate:
            return self.generate_safe_filename(candidate)

        candidate = self._extract_near_label(bounds, texts, self.number_label_only_res)
        if candidate:
            return self.generate_safe_filename(candidate)

        candidate = self._extract_inline(texts, self.processing_inline_res)
        if candidate:
            return self.generate_safe_filename(candidate)

        candidate = self._extract_near_label(bounds, texts, self.processing_label_only_res)
        if candidate:
            return self.generate_safe_filename(candidate)

        candidate = self._extract_near_label_confirmed(bounds, texts, self.processing_label_anchor_res)
        if candidate:
            return self.generate_safe_filename(candidate)

        candidate = self._extract_from_top_left(bounds, texts)
        if candidate:
            return self.generate_safe_filename(candidate)

        return None

    def extract_drawing_number_from_region(self, subdrawing_data: Dict) -> Optional[str]:
        """备用：图纸编号提取逻辑"""
        bounds = subdrawing_data["bounds"]
        texts = subdrawing_data["texts"]

        filtered_texts = self._preprocess_texts(texts)
        if not filtered_texts:
            return None

        extraction_methods = [
            self._extract_from_explicit_labels,
            self._extract_from_key_positions,
            self._extract_from_pattern_matching,
        ]
        for method in extraction_methods:
            result = method(bounds, filtered_texts)
            if result and self._validate_drawing_number(result):
                return result
        return None

    def _preprocess_texts(self, texts: List) -> List:
        """文本预处理（过滤无效文本）"""
        content_frequency = Counter([text["content"].strip() for text in texts])
        processed = []
        for text in texts:
            content = text["content"].strip()
            layer = (text.get("layer") or "").lower()
            if not content or len(content) > 30:
                continue
            if layer not in {"0", "dim", "dimension"}:
                if any(term in content for term in self.excluded_terms):
                    continue
                if content in self.cad_annotations:
                    continue
                if len(content) <= 2 and content_frequency[content] > 5:
                    continue
                if self._is_dimension_or_value(content):
                    continue
            processed.append(text)
        return processed

    def _is_dimension_or_value(self, content: str) -> bool:
        """判断是否为尺寸/数值文本"""
        dimension_patterns = [
            r"^\d+\.?\d*$",
            r"^\d+\.?\d*[LWTHDRC]$",
            r"^Φ\d+\.?\d*$",
            r"^R\d+\.?\d*$",
            r"^\d+\.?\d*°$",
            r"^\d+\.?\d*mm$",
            r"^M\d+x\d+\.?\d*$",
            r"^\d+\.?\d*深$",
            r"^C\d+\.?\d*$",
        ]
        return any(re.match(pattern, content) for pattern in dimension_patterns)

    def _extract_from_explicit_labels(self, bounds: Dict, texts: List) -> Optional[str]:
        """从显式标签提取"""
        candidate = self._extract_inline(texts, self.number_inline_res)
        if candidate:
            return candidate
        candidate = self._extract_near_label(bounds, texts, self.number_label_only_res)
        if candidate:
            return candidate
        candidate = self._extract_inline(texts, self.processing_inline_res)
        if candidate:
            return candidate
        candidate = self._extract_near_label(bounds, texts, self.processing_label_only_res)
        if candidate:
            return candidate
        candidate = self._extract_near_label_confirmed(bounds, texts, self.processing_label_anchor_res)
        if candidate:
            return candidate
        return None

    def _extract_from_key_positions(self, bounds: Dict, texts: List) -> Optional[str]:
        """从关键位置提取"""
        return self._extract_from_top_left(bounds, texts)

    def _extract_from_pattern_matching(self, bounds: Dict, texts: List) -> Optional[str]:
        """从正则模式提取"""
        if not texts:
            return None

        for text in texts:
            content = text.get("content", "").strip()
            for pattern in self.primary_patterns:
                match = re.search(pattern, content)
                if match:
                    candidate = match.group(0)
                    if self._validate_drawing_number(candidate):
                        return candidate
        return None

    def _clean_candidate_after_label(self, value: str) -> str:
        """清洗提取到的候选文件名"""
        cleaned = (value or "").strip()
        if not cleaned:
            return cleaned

        match = re.match(r"^([A-Z0-9\-_]+)(?:\(|（)", cleaned)
        if match:
            cleaned = match.group(1)
        else:
            cleaned = cleaned.split()[0]
            cleaned = cleaned.strip("，,。.;；:：)]】）'\"").strip("([【（'\"")

        cleaned = re.sub(r"^[\s\-_]+|[\s\-_]+$", "", cleaned)
        return cleaned[:64] if len(cleaned) > 64 else cleaned

    def _validate_drawing_number(self, content: str) -> bool:
        """验证编号有效性"""
        if not content or len(content) > 50:
            return False
        try:
            normalized = self._normalize_confirmed_code(content)
            if normalized and normalized in self._extract_confirmed_codes_from_text(normalized):
                return True
        except Exception:
            pass
        invalid_patterns = [
            r"^[:：].*",
            r".*[:：]\s*$",
            r"^\d+\.\d+$",
            r"^[0-9]{4,}$",
            r".*说明.*",
            r".*加工.*",
        ]
        if any(re.match(pattern, content) for pattern in invalid_patterns):
            return False
        valid_patterns = [
            r"^[A-Z]{1,4}[0-9]*$",
            r"^[A-Z]+[0-9]*(-[A-Z0-9]+)+$",
            r"^[A-Z]{2,4}$",
            r"^[A-Z0-9]+\([^)]+\)$",
        ]
        return any(re.match(pattern, content) for pattern in valid_patterns)

    def generate_safe_filename(self, name: str) -> str:
        """生成安全文件名"""
        if not name:
            return "未知编号"
        safe_name = name.strip()
        match = re.match(r"^([^(]+)", safe_name)
        if match:
            safe_name = match.group(1).strip()
        if not safe_name:
            safe_name = name.strip()
        safe_name = re.sub(r'[<>:"/\\|?*]', "_", safe_name).replace(" ", "_")
        safe_name = safe_name.rstrip(" .")
        return safe_name if len(safe_name) <= 80 else safe_name[:80]
