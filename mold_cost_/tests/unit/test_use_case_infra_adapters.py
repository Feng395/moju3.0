"""Application use case infrastructure adapter tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_use_case_modules_do_not_import_api_gateway():
    """Ensure the targeted use case modules no longer depend on api_gateway directly."""
    repo_root = Path(__file__).resolve().parents[2]
    use_case_files = (
        repo_root / "src" / "mold_cost" / "application" / "use_cases" / "create_job.py",
        repo_root / "src" / "mold_cost" / "application" / "use_cases" / "get_job.py",
        repo_root / "src" / "mold_cost" / "application" / "use_cases" / "get_job_file.py",
    )

    for file_path in use_case_files:
        source = file_path.read_text(encoding="utf-8")
        assert "api_gateway.repositories" not in source
        assert "api_gateway.utils" not in source


def test_create_job_use_case_uses_infrastructure_adapters(monkeypatch):
    """Verify create-job use case delegates to the new infrastructure adapters."""
    from mold_cost.application.use_cases.create_job import CreateJobFromUploadUseCase

    calls: list[tuple[str, tuple, dict]] = []

    class FakeJobRepository:
        async def create_job(self, **kwargs):
            calls.append(("job", tuple(), kwargs))

    class FakeAuditRepository:
        async def create_audit_log(self, **kwargs):
            calls.append(("audit", tuple(), kwargs))

    class FakeSnapshotRepository:
        async def create_price_snapshots(self, db, job_id):
            calls.append(("snapshot", (job_id,), {}))
            return 3

    class FakeChatHistoryRepository:
        async def create_session(self, **kwargs):
            calls.append(("chat", tuple(), kwargs))
            return {"session_id": kwargs["session_id"]}

    async def fake_validate(file, file_type="文件"):
        calls.append(("validate", (file.filename, file_type), {}))

    async def fake_encryption(file, encryption_key=None):
        calls.append(("encrypt", (file.filename, encryption_key), {}))
        return file

    class FakeMinioClient:
        async def upload_file(self, file, prefix="files"):
            calls.append(("upload", (file.filename, prefix), {}))
            return {"file_id": f"{prefix}-id", "object_name": f"{prefix}/obj", "file_size": 11}

        def delete_file(self, object_name, bucket=None):
            calls.append(("delete", (object_name, bucket), {}))

    class FakeRabbitMQClient:
        queue_job_processing = "queue-job-processing"

        async def publish_job_message(self, **kwargs):
            calls.append(("publish", tuple(), kwargs))

    async def fake_commit_sleep(seconds):
        calls.append(("sleep", (seconds,), {}))

    monkeypatch.setattr(
        "mold_cost.application.use_cases.create_job.JobRepository",
        lambda: FakeJobRepository(),
    )
    monkeypatch.setattr(
        "mold_cost.application.use_cases.create_job.AuditRepository",
        lambda: FakeAuditRepository(),
    )
    monkeypatch.setattr(
        "mold_cost.application.use_cases.create_job.SnapshotRepository",
        lambda: FakeSnapshotRepository(),
    )
    monkeypatch.setattr(
        "mold_cost.application.use_cases.create_job.ChatHistoryRepository",
        lambda: FakeChatHistoryRepository(),
    )
    monkeypatch.setattr("mold_cost.application.use_cases.create_job.validate_dwg_file", fake_validate)
    monkeypatch.setattr("mold_cost.application.use_cases.create_job.validate_prt_file", fake_validate)
    monkeypatch.setattr("mold_cost.application.use_cases.create_job.process_file_encryption", fake_encryption)
    monkeypatch.setattr("mold_cost.application.use_cases.create_job.asyncio.sleep", fake_commit_sleep)
    monkeypatch.setattr(
        "mold_cost.application.use_cases.create_job.CreateJobFromUploadUseCase._get_minio_client",
        staticmethod(lambda: FakeMinioClient()),
    )
    monkeypatch.setattr(
        "mold_cost.application.use_cases.create_job.CreateJobFromUploadUseCase._get_rabbitmq_client",
        staticmethod(lambda: FakeRabbitMQClient()),
    )

    class FakeDB:
        class _Begin:
            async def __aenter__(self):
                return None

            async def __aexit__(self, exc_type, exc, tb):
                return False

        def begin(self):
            return self._Begin()

        async def commit(self):
            calls.append(("commit", tuple(), {}))

    use_case = CreateJobFromUploadUseCase()
    class FakeUploadFile:
        def __init__(self, filename: str):
            self.filename = filename

    dwg_file = FakeUploadFile("sample.dwg")
    prt_file = FakeUploadFile("sample.prt")

    result = asyncio.run(
        use_case.execute(
            db=FakeDB(),
            user_id="user-1",
            dwg_file=dwg_file,
            prt_file=prt_file,
            encryption_key="secret",
        )
    )

    assert result["status"] == "pending"
    assert any(call[0] == "job" for call in calls)
    assert any(call[0] == "audit" for call in calls)
    assert any(call[0] == "chat" for call in calls)
    assert any(call[0] == "snapshot" for call in calls)
    assert any(call[0] == "publish" for call in calls)


def test_get_job_use_cases_use_infrastructure_repositories(monkeypatch):
    """Verify status and snapshot queries rely on the new repository adapters."""
    from mold_cost.application.use_cases.get_job import GetJobStatusUseCase, GetPriceSnapshotsUseCase, GetProcessSnapshotsUseCase

    class FakeJob:
        job_id = "job-1"
        user_id = "user-1"
        status = "processing"
        current_stage = "stage-1"
        progress = 30
        dwg_file_name = "a.dwg"
        prt_file_name = "b.prt"
        total_cost = 100.5
        created_at = None
        updated_at = None
        completed_at = None

    class FakeJobRepository:
        async def get_job_by_id(self, db, job_id):
            return FakeJob()

    class FakeSnapshotRepository:
        async def get_price_snapshots(self, db, job_id):
            return []

        async def get_process_snapshots(self, db, job_id):
            return []

    monkeypatch.setattr("mold_cost.application.use_cases.get_job.JobRepository", lambda: FakeJobRepository())
    monkeypatch.setattr("mold_cost.application.use_cases.get_job.SnapshotRepository", lambda: FakeSnapshotRepository())

    status_use_case = GetJobStatusUseCase()
    price_use_case = GetPriceSnapshotsUseCase()
    process_use_case = GetProcessSnapshotsUseCase()

    status_result = asyncio.run(status_use_case.execute(db=None, job_id="job-1", user_id="user-1"))
    price_result = asyncio.run(price_use_case.execute(db=None, job_id="job-1", user_id="user-1"))
    process_result = asyncio.run(process_use_case.execute(db=None, job_id="job-1", user_id="user-1"))

    assert status_result["job_id"] == "job-1"
    assert price_result["count"] == 0
    assert process_result["count"] == 0


def test_get_job_file_use_case_uses_infrastructure_repository(monkeypatch):
    """Verify file download lookup uses the new repository adapter."""
    from mold_cost.application.use_cases.get_job_file import GetJobFileUseCase

    class FakeJob:
        user_id = "user-1"
        dwg_file_path = "dwg/object"
        prt_file_path = "prt/object"

    class FakeJobRepository:
        async def get_job_by_id(self, db, job_id):
            return FakeJob()

    class FakeMinioClient:
        def get_file(self, object_name, bucket=None):
            return f"payload:{object_name}".encode()

        def generate_presigned_url(self, object_name, expires):
            return f"url:{object_name}"

    monkeypatch.setattr("mold_cost.application.use_cases.get_job_file.JobRepository", lambda: FakeJobRepository())
    monkeypatch.setattr(
        "mold_cost.application.use_cases.get_job_file.GetJobFileUseCase._get_minio_client",
        staticmethod(lambda: FakeMinioClient()),
    )

    use_case = GetJobFileUseCase()
    payload = asyncio.run(use_case.get_file(db=None, job_id="job-1", file_type="dwg", user_id="user-1"))
    url = asyncio.run(use_case.get_presigned_url(db=None, job_id="job-1", file_type="prt", user_id="user-1"))

    assert payload == b"payload:dwg/object"
    assert url == "url:prt/object"
