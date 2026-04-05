"""Src 侧的数据修改 review handler。"""

from __future__ import annotations

import copy
import os
import re
import uuid
from typing import Any

from shared.timezone_utils import now_shanghai

from ...core.logging import get_logger
from ..db.repositories.chat_history_repository import ChatHistoryRepository
from .pending_action_store import RedisReviewPendingActionStore
from .review_action_handlers import BaseReviewActionHandler, ReviewActionResult

logger = get_logger(__name__)


class DataModificationReviewActionHandler(BaseReviewActionHandler):
    """在 src 侧承接自然语言修改、校验与待确认动作生成。"""

    _SUBGRAPH_PREFIXES = (
        r"UP_JIAT",
        r"PS_JIAT",
        r"LOW_JIAT",
        r"UP_ITEM",
        r"PSITEM",
        r"LOW_ITEM",
        r"DIE2_P",
        r"PS2_P",
        r"PPS2_P",
        r"PH2_P",
        r"LB2_P",
        r"UP_P",
        r"UB_P",
        r"PH_P",
        r"PU_P",
        r"PPS_P",
        r"PS_P",
        r"DIE_P",
        r"GU_P",
        r"LB_P",
        r"TEMP[12]",
        r"ST[123]",
        r"DIE2",
        r"PS2",
        r"PPS2",
        r"PH2",
        r"LB2",
        r"STRIP",
        r"PPS",
        r"DIE",
        r"CAM",
        r"BOL",
        r"UP",
        r"LP",
        r"PS",
        r"PH",
        r"UB",
        r"PU",
        r"LB",
        r"EB",
        r"EJ",
        r"CV",
        r"CJ",
        r"CB",
        r"GU",
        r"RP",
        r"CP",
        r"TP",
        r"BP",
        r"SP",
        r"MP",
        r"PP",
        r"U[12]",
        r"B[12]",
    )
    _SUBGRAPH_PATTERN = re.compile(
        rf"((?:{'|'.join(_SUBGRAPH_PREFIXES)})[-_]?(?:\d{{2}}|[A-Z]+\d+))",
        re.IGNORECASE,
    )

    def __init__(
        self,
        *,
        pending_action_store: RedisReviewPendingActionStore | None = None,
        nlp_parser=None,
        chat_history_repository: ChatHistoryRepository | None = None,
        validator=None,
        display_view_builder=None,
        use_chat_history: bool | None = None,
    ) -> None:
        super().__init__(pending_action_store=pending_action_store)
        self._nlp_parser = nlp_parser
        self._chat_history_repository = chat_history_repository or ChatHistoryRepository()
        self._validator = validator
        self._display_view_builder = display_view_builder
        self._use_chat_history = (
            use_chat_history
            if use_chat_history is not None
            else os.getenv("USE_CHAT_HISTORY", "true").lower() == "true"
        )

    @property
    def nlp_parser(self):
        if self._nlp_parser is None:
            from agents.nlp_parser import NLPParser

            self._nlp_parser = NLPParser(use_llm=True)
        return self._nlp_parser

    @property
    def validator(self):
        if self._validator is None:
            from shared.validators import ModificationValidator

            self._validator = ModificationValidator
        return self._validator

    @property
    def display_view_builder(self):
        if self._display_view_builder is None:
            from agents.data_view_builder import DataViewBuilder

            self._display_view_builder = DataViewBuilder
        return self._display_view_builder

    async def handle(self, intent_result, job_id: str, context: dict[str, Any], db_session) -> ReviewActionResult:
        try:
            raw_data = self._get_raw_data(context)
            parse_context = {**context, "db_session": db_session}
            parsed_changes = await self.nlp_parser.parse(getattr(intent_result, "raw_message", ""), parse_context)
            if not parsed_changes:
                return ReviewActionResult(status="error", message="无法解析修改指令，请换一种方式描述")

            parsed_changes = await self._infer_target_from_history(
                parsed_changes=parsed_changes,
                user_message=getattr(intent_result, "raw_message", ""),
                job_id=job_id,
                context=context,
                db_session=db_session,
            )
            if not parsed_changes:
                return ReviewActionResult(
                    status="error",
                    message="无法确定要修改的目标。请明确指定子图ID，例如：'PH2-04 材质改为 45#'",
                )

            validation_result = self.validator.validate_changes(parsed_changes, raw_data)
            if not validation_result.is_valid:
                return ReviewActionResult(
                    status="error",
                    message=f"修改验证失败: {validation_result.error_message}",
                )

            modified_data = self._apply_changes(
                data=raw_data,
                changes=parsed_changes,
                job_id=job_id,
                user_id=context.get("user_id", "system"),
            )
            modified_display_view = self.display_view_builder.build_display_view(modified_data)
            modification_record = {
                "id": str(uuid.uuid4()),
                "text": getattr(intent_result, "raw_message", ""),
                "parsed": parsed_changes,
                "timestamp": now_shanghai().isoformat(),
            }

            await self._save_pending_action(
                job_id=job_id,
                payload={
                    "action_type": "DATA_MODIFICATION",
                    "changes": parsed_changes,
                    "modified_data": modified_data,
                    "modified_display_view": modified_display_view,
                    "modification_record": modification_record,
                },
            )
            return ReviewActionResult(
                status="ok",
                message=self._format_modification_message(parsed_changes),
                requires_confirmation=True,
                pending_action={"action_type": "DATA_MODIFICATION", "changes": parsed_changes},
                data={
                    "modification_id": modification_record["id"],
                    "parsed_changes": parsed_changes,
                    "modified_data": modified_data,
                    "display_view": modified_display_view,
                },
            )
        except Exception as exc:
            logger.error("Data modification review action failed", exc_info=True)
            return ReviewActionResult(status="error", message=f"处理修改失败：{exc}")

    def _apply_changes(self, *, data: dict[str, Any], changes: list[dict[str, Any]], job_id: str, user_id: str) -> dict[str, Any]:
        modified_data = copy.deepcopy(data)
        table_mapping = {
            "price_snapshots": "job_price_snapshots",
            "process_snapshots": "job_process_snapshots",
        }
        reverse_mapping = {value: key for key, value in table_mapping.items()}

        for change in changes:
            table = change.get("table")
            field = change.get("field")
            value = change.get("value")
            data_key = table
            if data_key not in modified_data:
                data_key = reverse_mapping.get(table, table)
            if data_key not in modified_data:
                data_key = table_mapping.get(table, table)
            if data_key not in modified_data:
                continue

            record_id = change.get("id")
            filter_conditions = change.get("filter")
            for record in modified_data[data_key]:
                if record.get("job_id") != job_id:
                    continue
                if record_id:
                    if record.get(self._get_id_field(table)) != record_id:
                        continue
                elif filter_conditions and not self._match_filter(record, filter_conditions):
                    continue

                normalized_value = value
                if isinstance(field, str) and field.lower() in {"material", "材质"}:
                    normalized_value = self._normalize_material(value)

                record[field] = normalized_value
                if table in {"job_price_snapshots", "job_process_snapshots"}:
                    record["is_modified"] = True
                    record["modified_by"] = user_id
                    record["modified_at"] = now_shanghai()
        return modified_data

    async def _infer_target_from_history(
        self,
        *,
        parsed_changes: list[dict[str, Any]],
        user_message: str,
        job_id: str,
        context: dict[str, Any],
        db_session,
    ) -> list[dict[str, Any]]:
        if not self._use_chat_history:
            return parsed_changes

        unique_ids = {change.get("id") for change in parsed_changes if change.get("id")}
        if len(unique_ids) <= 1:
            return parsed_changes

        if any(keyword in user_message for keyword in ["全部", "所有", "全体", "整体", "类", "类型", "分类", "种类", "类别", "开头", "结尾", "开始", "结束", "都"]):
            return parsed_changes
        if self._SUBGRAPH_PATTERN.search(user_message) or re.search(r"[A-Z]{2,}开头", user_message):
            return parsed_changes

        inferred_subgraph = await self._infer_subgraph_from_history(db_session=db_session, job_id=job_id)
        if not inferred_subgraph:
            return parsed_changes

        display_view = self._get_display_view(context)
        filtered_changes: list[dict[str, Any]] = []
        for change in parsed_changes:
            table = change.get("table")
            if table in {"job_price_snapshots", "price_snapshots"}:
                filtered_changes.append(change)
                continue
            if table != "subgraphs":
                filtered_changes.append(change)
                continue

            record_id = change.get("id")
            target_record = next(
                (
                    record
                    for record in display_view
                    if (record.get("_source") or {}).get("subgraph_id") == record_id
                ),
                None,
            )
            if target_record is None:
                continue
            part_code = str(target_record.get("part_code", "")).upper()
            source_subgraph_id = str((target_record.get("_source") or {}).get("subgraph_id", "")).upper()
            if (
                part_code == inferred_subgraph
                or part_code.endswith(f"_{inferred_subgraph}")
                or source_subgraph_id == inferred_subgraph
                or source_subgraph_id.endswith(f"_{inferred_subgraph}")
            ):
                filtered_changes.append(change)

        if filtered_changes:
            return filtered_changes

        all_price_changes = all(
            change.get("table") in {"job_price_snapshots", "price_snapshots"} for change in parsed_changes
        )
        return parsed_changes if all_price_changes else []

    async def _infer_subgraph_from_history(self, *, db_session, job_id: str) -> str | None:
        history = await self._chat_history_repository.get_recent_session_history(
            db_session,
            session_id=job_id,
            limit=10,
        )
        if not history:
            return None

        prioritized_messages = [
            *[message for message in reversed(history) if message.get("role") == "user"],
            *[message for message in reversed(history) if message.get("role") == "assistant"],
        ]
        for message in prioritized_messages:
            content = message.get("content", "")
            matches = self._SUBGRAPH_PATTERN.findall(content)
            if matches:
                return matches[0].upper()
        return None

    @staticmethod
    def _match_filter(record: dict[str, Any], filter_conditions: dict[str, Any]) -> bool:
        for key, value in filter_conditions.items():
            record_value = record.get(key)
            if isinstance(record_value, str) and isinstance(value, str):
                if record_value.lower() != value.lower():
                    return False
            elif record_value != value:
                return False
        return True

    @staticmethod
    def _get_id_field(table: str | None) -> str:
        id_fields = {
            "features": "feature_id",
            "job_price_snapshots": "snapshot_id",
            "price_snapshots": "snapshot_id",
            "subgraphs": "subgraph_id",
        }
        return id_fields.get(table or "", "id")

    @staticmethod
    def _normalize_material(material: Any) -> Any:
        if not material or not isinstance(material, str):
            return material
        normalized = material.upper().strip()
        return re.sub(r"TOOLOX(\d+)", r"T00L0X\1", normalized)

    @staticmethod
    def _format_modification_message(changes: list[dict[str, Any]]) -> str:
        if not changes:
            return "未检测到有效的修改"
        return "已应用修改，请确认"
