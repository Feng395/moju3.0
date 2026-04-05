"""Workflow golden 回归样本的复用辅助函数。"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    """统一读取 utf-8 JSON，避免测试侧重复写样板代码。"""
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve_repo_path(relative_path: str) -> Path:
    return REPO_ROOT / Path(relative_path)


def load_inventory(inventory_path: Path | None = None) -> dict[str, Any]:
    """读取 pricing bridge inventory，同时兼容显式路径覆盖。"""
    inventory_path = inventory_path or REPO_ROOT / "tests" / "golden" / "pricing_bridge_inventory.json"
    return load_json(inventory_path)


def load_sample_bundle(sample_entry: dict[str, Any]) -> dict[str, Any]:
    """将样本三件套一次性装载为测试可消费的数据结构。"""
    return {
        "manifest": load_json(resolve_repo_path(sample_entry["manifest_path"])),
        "expected_summary": load_json(resolve_repo_path(sample_entry["expected_summary_path"])),
        "assertion_rules": load_json(resolve_repo_path(sample_entry["assertion_rules_path"])),
    }


def build_stage_index(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """把 stage 列表转成按名称索引，方便规则执行阶段随机访问。"""
    return {stage["name"]: stage for stage in manifest["stages"]}


def resolve_data_path(data: Any, path: str) -> Any:
    """中文注释：支持 dot path 读取嵌套 dict/list，让 golden 规则能直接比对关键费用字段。"""
    current = data
    for segment in path.split("."):
        if isinstance(current, dict):
            assert segment in current, f"Missing path segment '{segment}' in '{path}'"
            current = current[segment]
            continue
        if isinstance(current, list):
            try:
                current = current[int(segment)]
            except (ValueError, IndexError) as exc:
                raise AssertionError(f"Invalid list segment '{segment}' in '{path}'") from exc
            continue
        raise AssertionError(f"Unable to resolve path '{path}' at segment '{segment}'")
    return current


def assert_manifest_contract(manifest: dict[str, Any]) -> None:
    """校验 manifest 的最小合同，保证样本目录结构可复用。"""
    assert manifest["schema_version"] == "golden.sample.v1"
    assert manifest["sample_id"]
    assert manifest["stages"]

    stage_names = [stage["name"] for stage in manifest["stages"]]
    assert len(stage_names) == len(set(stage_names))

    for stage in manifest["stages"]:
        assert stage["name"]
        assert stage["status"]
        assert "summary" in stage


def iter_repo_artifacts(manifest: dict[str, Any]):
    """遍历声明了 repo_path 的产物，用于存在性和内容断言。"""
    for stage in manifest["stages"]:
        for artifact in stage.get("artifacts", []):
            repo_path = artifact.get("repo_path")
            if repo_path:
                yield stage["name"], artifact, resolve_repo_path(repo_path)


def read_csv_records(path: Path) -> list[dict[str, str]]:
    """按多编码顺序读取 CSV，并标准化表头/字段空白字符。"""
    last_error: Exception | None = None

    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                rows = list(csv.DictReader(handle))
        except UnicodeDecodeError as exc:
            last_error = exc
            continue

        normalized_rows = []
        for row in rows:
            # 中文注释：CSV 来自历史脚本，字段可能带 BOM 或尾部空格，这里先做一次统一清洗。
            normalized_rows.append({(key or "").strip(): (value or "").strip() for key, value in row.items()})
        return normalized_rows

    raise AssertionError(f"Unable to decode CSV file: {path}") from last_error


def evaluate_assertion_rules(
    manifest: dict[str, Any],
    expected_summary: dict[str, Any],
    assertion_rules: dict[str, Any],
    inventory: dict[str, Any],
) -> None:
    """执行 assertion_rules 中声明的程序化规则。"""
    stage_index = build_stage_index(manifest)

    for rule in assertion_rules["rules"]:
        rule_type = rule["type"]

        if rule_type == "stage_sequence":
            actual = [stage["name"] for stage in manifest["stages"]]
            assert actual == rule["expected"]
            continue

        if rule_type == "repo_artifacts_exist":
            for stage_name in rule["stages"]:
                stage = stage_index[stage_name]
                for artifact in stage.get("artifacts", []):
                    repo_path = artifact.get("repo_path")
                    if repo_path:
                        assert resolve_repo_path(repo_path).exists(), repo_path
            continue

        if rule_type == "csv_row_count":
            stage = stage_index[rule["stage"]]
            csv_artifact = next(
                artifact for artifact in stage["artifacts"] if artifact.get("format") == "csv"
            )
            rows = read_csv_records(resolve_repo_path(csv_artifact["repo_path"]))
            assert len(rows) == rule["expected_rows"]

            first_row = rows[0]
            # 中文注释：先覆盖最稳定的首行摘要字段，避免把高噪声细节写死。
            for key, expected_value in rule.get("expected_fields", {}).items():
                assert first_row[key] == str(expected_value)
            continue

        if rule_type == "csv_field_contains":
            stage = stage_index[rule["stage"]]
            csv_artifact = next(
                artifact for artifact in stage["artifacts"] if artifact.get("format") == "csv"
            )
            rows = read_csv_records(resolve_repo_path(csv_artifact["repo_path"]))
            assert rows, csv_artifact["repo_path"]
            assert rule["expected_substring"] in rows[0][rule["field"]]
            continue

        if rule_type == "summary_contains":
            stage = stage_index[rule["stage"]]
            actual_value = resolve_data_path(stage["summary"], rule["path"])
            assert actual_value == rule["expected"]
            continue

        if rule_type == "pricing_inventory_counts":
            expected = rule["expected"]
            assert len(inventory["search_modules"]) == expected["search_modules"]
            assert len(inventory["calculator_modules"]) == expected["calculator_modules"]
            continue

        if rule_type == "expected_summary_matches":
            actual_value = resolve_data_path(expected_summary, rule["path"])
            assert actual_value == rule["expected"]
            continue

        raise AssertionError(f"Unsupported rule type: {rule_type}")


def load_pause_resume_template(template_path: Path) -> dict[str, Any]:
    """读取 workflow 暂停/恢复夹具模板。"""
    return load_json(template_path)


def hydrate_pause_resume_fixture(
    *,
    template: dict[str, Any],
    manifest: dict[str, Any],
    expected_summary: dict[str, Any],
    job_graph,
    review_graph,
) -> dict[str, Any]:
    """把 golden 样本和 fixture 模板组装成可序列化的 workflow 恢复快照。"""
    stage_names = [stage["name"] for stage in manifest["stages"]]
    stage_index = build_stage_index(manifest)
    resume_stage = template["resume_from_stage"]
    resume_stage_position = stage_names.index(resume_stage)
    last_completed_stage = stage_names[resume_stage_position - 1]

    upload_stage = stage_index["upload"]
    review_stage = stage_index["review"]
    pricing_stage = stage_index["pricing"]
    pricing_key_fields = dict(expected_summary.get("business_outcome", {}).get("pricing_baseline", {}))
    review_pending_fields = list(review_stage["summary"].get("pending_fields", []))

    # 中文注释：这里不依赖真实外部基础设施，只构造 workflow 恢复所需的最小状态。
    job_state = job_graph.to_state(
        job_id=template["job_id"],
        user_id=template["user_id"],
        status=template["job_state"]["status"],
        dwg_file_path=upload_stage["summary"].get("dwg_logical_path"),
        prt_file_path=upload_stage["summary"].get("prt_logical_path"),
        artifacts={
            **template["job_state"].get("artifacts", {}),
            "golden_sample_id": manifest["sample_id"],
            "stage_order": expected_summary["stage_order"],
            "last_completed_stage": last_completed_stage,
            "resume_boundary_stage": resume_stage,
            "next_stage": template["resume_request"]["expected_next_stage"],
            "feature_summary": stage_index["feature_recognition"]["summary"],
            "review_summary": review_stage["summary"],
            "pricing_summary": pricing_stage["summary"],
            "pricing_key_fields": pricing_key_fields,
        },
        errors=list(template["job_state"].get("errors", [])),
    )
    review_state = review_graph.to_state(
        job_id=template["job_id"],
        review_id=template["review_state"]["review_id"],
        status=template["review_state"]["status"],
        suggestions=list(template["review_state"].get("suggestions", [])),
        messages=list(template["review_state"].get("messages", [])),
        # 中文注释：把 review 暂停点和 pricing 关键费用一并塞进 fixture，方便回归测试确认恢复边界没漂移。
        current_node="confirm_and_resume",
        waiting_for="confirmation",
        resume_from="confirm_and_resume",
        checkpoint_id="confirm_and_resume",
        extra={
            "golden_sample_id": manifest["sample_id"],
            "pending_fields": review_pending_fields,
            "expected_next_stage": template["resume_request"]["expected_next_stage"],
            "pricing_key_fields": pricing_key_fields,
        },
    )

    # 中文注释：返回序列化结果，便于测试直接断言，也为后续 checkpoint 落库预留接口。
    return {
        "fixture_version": template["fixture_version"],
        "job_state": job_graph.serialize_state(job_state),
        "review_state": review_graph.serialize_state(review_state),
        "resume_request": dict(template["resume_request"]),
    }
