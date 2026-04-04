"""Reusable helpers for workflow golden regression samples."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_repo_path(relative_path: str) -> Path:
    return REPO_ROOT / Path(relative_path)


def load_inventory(inventory_path: Path | None = None) -> dict[str, Any]:
    inventory_path = inventory_path or REPO_ROOT / "tests" / "golden" / "pricing_bridge_inventory.json"
    return load_json(inventory_path)


def load_sample_bundle(sample_entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "manifest": load_json(resolve_repo_path(sample_entry["manifest_path"])),
        "expected_summary": load_json(resolve_repo_path(sample_entry["expected_summary_path"])),
        "assertion_rules": load_json(resolve_repo_path(sample_entry["assertion_rules_path"])),
    }


def build_stage_index(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {stage["name"]: stage for stage in manifest["stages"]}


def assert_manifest_contract(manifest: dict[str, Any]) -> None:
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
    for stage in manifest["stages"]:
        for artifact in stage.get("artifacts", []):
            repo_path = artifact.get("repo_path")
            if repo_path:
                yield stage["name"], artifact, resolve_repo_path(repo_path)


def read_csv_records(path: Path) -> list[dict[str, str]]:
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
            normalized_rows.append({(key or "").strip(): (value or "").strip() for key, value in row.items()})
        return normalized_rows

    raise AssertionError(f"Unable to decode CSV file: {path}") from last_error


def evaluate_assertion_rules(
    manifest: dict[str, Any],
    expected_summary: dict[str, Any],
    assertion_rules: dict[str, Any],
    inventory: dict[str, Any],
) -> None:
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
            actual_value = stage["summary"][rule["path"]]
            assert actual_value == rule["expected"]
            continue

        if rule_type == "pricing_inventory_counts":
            expected = rule["expected"]
            assert len(inventory["search_modules"]) == expected["search_modules"]
            assert len(inventory["calculator_modules"]) == expected["calculator_modules"]
            continue

        if rule_type == "expected_summary_matches":
            assert expected_summary[rule["path"]] == rule["expected"]
            continue

        raise AssertionError(f"Unsupported rule type: {rule_type}")


def load_pause_resume_template(template_path: Path) -> dict[str, Any]:
    return load_json(template_path)


def hydrate_pause_resume_fixture(
    *,
    template: dict[str, Any],
    manifest: dict[str, Any],
    expected_summary: dict[str, Any],
    job_graph,
    review_graph,
) -> dict[str, Any]:
    stage_names = [stage["name"] for stage in manifest["stages"]]
    stage_index = build_stage_index(manifest)
    resume_stage = template["resume_from_stage"]
    resume_stage_position = stage_names.index(resume_stage)
    last_completed_stage = stage_names[resume_stage_position - 1]

    upload_stage = stage_index["upload"]
    review_stage = stage_index["review"]
    pricing_stage = stage_index["pricing"]

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
        },
        errors=list(template["job_state"].get("errors", [])),
    )
    review_state = review_graph.to_state(
        job_id=template["job_id"],
        review_id=template["review_state"]["review_id"],
        status=template["review_state"]["status"],
        suggestions=list(template["review_state"].get("suggestions", [])),
        messages=list(template["review_state"].get("messages", [])),
    )

    return {
        "fixture_version": template["fixture_version"],
        "job_state": job_graph.serialize_state(job_state),
        "review_state": review_graph.serialize_state(review_state),
        "resume_request": dict(template["resume_request"]),
    }
