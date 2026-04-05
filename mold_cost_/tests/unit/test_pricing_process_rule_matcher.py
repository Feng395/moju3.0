"""Tests for migrated pricing process rule matcher."""

from __future__ import annotations

import asyncio
import importlib


def test_process_rule_matcher_updates_only_empty_subgraphs(monkeypatch):
    module = importlib.import_module("mold_cost.domain.pricing.services.process_rule_matcher")

    updates: list[tuple[str | None, str | None, str]] = []

    class _FakeDb:
        async def fetch_all(self, sql: str, *args):
            if "FROM subgraphs" in sql:
                return [
                    {
                        "subgraph_id": "sg-1",
                        "part_name": "DIE-01",
                        "wire_process_note": None,
                        "wire_process": None,
                    },
                    {
                        "subgraph_id": "sg-2",
                        "part_name": "DIE-02",
                        "wire_process_note": "existing",
                        "wire_process": "keep",
                    },
                ]
            if "FROM process_rules" in sql:
                return [
                    {
                        "name": "DIE-01",
                        "description": "rule-note",
                        "conditions": "rule-process",
                    }
                ]
            raise AssertionError(sql)

        async def execute(self, sql: str, *args):
            updates.append((args[0], args[1], args[2]))

    monkeypatch.setattr(module, "db", _FakeDb())

    result = asyncio.run(module.match_and_update_process_rules("job-1", ["sg-1", "sg-2"]))

    assert result == {"status": "ok"}
    assert updates == [("rule-note", "rule-process", "sg-1")]
