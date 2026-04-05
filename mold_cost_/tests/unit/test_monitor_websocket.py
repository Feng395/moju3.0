from __future__ import annotations

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.messaging.monitor_websocket import RedisWebSocketActivityTracker


def test_tracker_marks_activity_and_expires_stale_jobs():
    tracker = RedisWebSocketActivityTracker(activity_timeout_seconds=5)

    became_active = tracker.mark_seen(
        job_id="job-1",
        channel="job:job-1:progress",
        message_type="progress",
        payload={"progress": 10},
        now=100.0,
    )

    assert became_active is True
    assert tracker.get_connection_count("job-1", now=100.0) == 1
    assert tracker.get_all_job_ids(now=100.0) == ["job-1"]

    became_active_again = tracker.mark_seen(
        job_id="job-1",
        channel="job:job-1:progress",
        message_type="progress",
        payload={"progress": 20},
        now=101.0,
    )

    assert became_active_again is False
    assert tracker.describe("job-1")["message_count"] == 2

    expired = tracker.prune_stale(now=107.5)
    assert expired == ["job-1"]
    assert tracker.get_connection_count("job-1", now=107.5) == 0
    assert tracker.get_all_job_ids(now=107.5) == []


def test_tracker_snapshot_counts_active_jobs():
    tracker = RedisWebSocketActivityTracker(activity_timeout_seconds=5)
    tracker.mark_seen(job_id="job-1", channel="job:job-1:progress", message_type="progress", now=10.0)
    tracker.mark_seen(job_id="job-2", channel="job:job-2:review", message_type="review", now=11.0)

    assert tracker.get_connection_count(now=11.0) == 2
    assert tracker.snapshot(now=11.0) == {"job-1": 1, "job-2": 1}
