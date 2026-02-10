"""
InteractionAgent - 用户交互Agent
负责人：人员B2
"""
from typing import Dict, Any, List
from .base_agent import BaseAgent, OpResult

class InteractionAgent(BaseAgent):
    """
    用户交互Agent
    处理参数缺失时的用户交互
    """
    
    def __init__(self):
        super().__init__("InteractionAgent")
    
    async def process(self, context: Dict[str, Any]) -> OpResult:
        """处理用户交互"""
        missing_params = context.get("missing_params", [])
        
        if not missing_params:
            return OpResult(status="ok", message="无需用户交互")
        
        # 生成交互卡片
        card = self._generate_interaction_card(
            job_id=context.get("job_id"),
            subgraph_id=context.get("subgraph_id"),
            missing_params=missing_params
        )
        
        return OpResult(
            status="ok",
            data={"card": card},
            message="等待用户输入"
        )
    
    def _generate_interaction_card(
        self,
        job_id: str,
        subgraph_id: str,
        missing_params: List[str]
    ) -> Dict[str, Any]:
        """生成交互卡片"""
        fields = []
        
        for param in missing_params:
            if param == "thickness_mm":
                fields.append({
                    "name": "thickness_mm",
                    "label": "厚度(mm)",
                    "type": "number",
                    "required": True,
                    "validation": {"min": 0.1, "max": 500}
                })
            elif param == "material":
                fields.append({
                    "name": "material",
                    "label": "材质",
                    "type": "select",
                    "options": ["45#", "S136", "NAK80", "718H"],
                    "required": True
                })
        
        return {
            "card_id": f"{job_id}_{subgraph_id}_input",
            "card_type": "missing_input",
            "title": f"子图 {subgraph_id} 缺少参数",
            "fields": fields,
            "actions": [
                {"type": "submit", "label": "提交"},
                {"type": "re_recognize", "label": "重新识别"}
            ]
        }
