"""Src-owned completeness validator for review workflow."""

from __future__ import annotations

from typing import Any


class SrcReviewCompletenessValidator:
    """Validate required review fields and build completion prompts."""

    REQUIRED_FIELDS = {
        "features": {
            "length_mm": "长度(mm)",
            "width_mm": "宽度(mm)",
            "thickness_mm": "厚度(mm)",
            "quantity": "数量",
            "material": "材质",
        }
    }

    def check_data_completeness(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        missing_fields: list[dict[str, Any]] = []
        for feature in raw_data.get("features", []):
            missing = self._check_feature(feature)
            if not missing:
                continue
            missing_fields.append(
                {
                    "table": "features",
                    "record_id": str(feature.get("feature_id")),
                    "record_name": feature.get("subgraph_id", "Unknown"),
                    "part_code": feature.get("part_code"),
                    "part_name": feature.get("part_name"),
                    "missing": missing,
                    "current_values": {
                        field: feature.get(field)
                        for field in self.REQUIRED_FIELDS["features"]
                    },
                }
            )

        is_complete = len(missing_fields) == 0
        return {
            "is_complete": is_complete,
            "missing_fields": missing_fields,
            "summary": f"发现 {len(missing_fields)} 条记录缺少必填字段" if not is_complete else "数据完整",
        }

    def generate_completion_prompt(
        self,
        missing_fields: list[dict[str, Any]],
        raw_data: dict[str, Any],
    ) -> str:
        prompt_parts = ["以下零件记录缺少必填字段,请根据已知信息推理并给出补全建议:\n"]

        for index, item in enumerate(missing_fields, start=1):
            prompt_parts.append(f"\n【记录 {index}】")
            prompt_parts.append(f"子图ID: {item['record_name']}")
            if item.get("part_code"):
                prompt_parts.append(f"零件编号: {item['part_code']}")
            if item.get("part_name"):
                prompt_parts.append(f"零件名称: {item['part_name']}")
            prompt_parts.append(f"记录ID: {item['record_id']}")
            prompt_parts.append(f"缺失字段: {', '.join(item['missing'].values())}")

            feature = self._find_feature(raw_data, item["record_id"])
            if not feature:
                continue

            prompt_parts.append("已知信息:")
            current_values = item.get("current_values", {})
            if current_values.get("length_mm"):
                prompt_parts.append(f"  - 长度: {current_values['length_mm']}mm")
            if current_values.get("width_mm"):
                prompt_parts.append(f"  - 宽度: {current_values['width_mm']}mm")
            if current_values.get("thickness_mm"):
                prompt_parts.append(f"  - 厚度: {current_values['thickness_mm']}mm")
            if current_values.get("quantity"):
                prompt_parts.append(f"  - 数量: {current_values['quantity']}")
            if current_values.get("material"):
                prompt_parts.append(f"  - 材质: {current_values['material']}")

            processing_instructions = feature.get("processing_instructions")
            if processing_instructions and isinstance(processing_instructions, dict):
                instruction_parts: list[str] = []
                for value in processing_instructions.values():
                    if isinstance(value, list):
                        instruction_parts.append(", ".join(str(item) for item in value))
                    else:
                        instruction_parts.append(str(value))
                prompt_parts.append(f"  - 加工说明: {', '.join(instruction_parts)[:100]}")

            if feature.get("heat_treatment"):
                prompt_parts.append(f"  - 热处理: {feature['heat_treatment']}")

        # 中文注释：这里沿用旧 prompt 文案，避免 suggestion 模型侧因为措辞变化产生额外漂移。
        prompt_parts.extend(
            [
                "\n请以自然语言形式给出补全建议,格式如下:",
                "'零件 PH2-04 的长度设为 309.5mm, 宽度设为 87mm, 厚度设为 47mm, 数量设为 1, 材质设为 Cr12mov'",
                "\n注意:",
                "1. 根据零件编号和加工说明推理合理的尺寸",
                "2. 材质通常从热处理信息中推断",
                "3. 数量默认为 1",
            ]
        )
        return "\n".join(prompt_parts)

    def _check_feature(self, feature: dict[str, Any]) -> dict[str, str]:
        missing: dict[str, str] = {}
        for field, display_name in self.REQUIRED_FIELDS["features"].items():
            value = feature.get(field)
            if value is None or value == "" or (isinstance(value, (int, float)) and value == 0):
                missing[field] = display_name
        return missing

    @staticmethod
    def _find_feature(raw_data: dict[str, Any], feature_id: str) -> dict[str, Any] | None:
        for feature in raw_data.get("features", []):
            if str(feature.get("feature_id")) == feature_id:
                return feature
        return None
