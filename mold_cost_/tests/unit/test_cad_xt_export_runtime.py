"""Tests for the src-owned CAD .x_t export runtime."""

from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_cad_xt_export_runtime_skips_without_nx():
    from mold_cost.infrastructure.cad.cad_xt_export_runtime import export_xt_files

    class _FakeDbManager:
        def get_prt_file_path(self, _job_id):
            raise AssertionError("db lookup should not run when NX is unavailable")

    class _FakeStorageManager:
        async def get_file(self, *_args, **_kwargs):
            raise AssertionError("storage should not run when NX is unavailable")

    result = asyncio.run(
        export_xt_files(
            job_id="job-1",
            temp_dir="D:/temp/cad",
            export_files=[{"sub_code": "A1"}],
            storage_manager=_FakeStorageManager(),
            db_manager=_FakeDbManager(),
            minio_client=object(),
            export_xt_from_prt=lambda **_kwargs: {"A1": "xt/path"},
            nx_importer=lambda: (_ for _ in ()).throw(ImportError("no nx")),
        )
    )

    assert result == {}


def test_cad_xt_export_runtime_downloads_prt_and_exports(monkeypatch):
    from mold_cost.infrastructure.cad import cad_xt_export_runtime as runtime

    calls = []

    class _FakeDbManager:
        def get_prt_file_path(self, job_id):
            calls.append(("db", job_id))
            return "prt/2026/04/demo.prt"

    class _FakeStorageManager:
        async def get_file(self, source, save_path, use_minio=False):
            calls.append(("storage", source, save_path, use_minio))
            return True

    monkeypatch.setattr(
        runtime,
        "datetime",
        type(
            "_FixedDatetime",
            (),
            {
                "now": staticmethod(lambda: datetime(2026, 4, 5, 9, 30, 0)),
            },
        ),
    )

    result = asyncio.run(
        runtime.export_xt_files(
            job_id="job-2",
            temp_dir="D:/temp/cad",
            export_files=[{"sub_code": "A1", "part_code": "P-001"}],
            storage_manager=_FakeStorageManager(),
            db_manager=_FakeDbManager(),
            minio_client="minio-client",
            export_xt_from_prt=lambda **kwargs: calls.append(("export", kwargs)) or {"A1": "xt/2026/04/job-2/P-001.x_t"},
            nx_importer=lambda: object(),
        )
    )

    assert result == {"A1": "xt/2026/04/job-2/P-001.x_t"}
    assert calls[0] == ("db", "job-2")
    assert calls[1] == ("storage", "prt/2026/04/demo.prt", "D:/temp/cad\\source.prt", True)
    assert calls[2][0] == "export"
    assert calls[2][1]["xt_minio_base"] == "xt/2026/04/job-2"
    assert calls[2][1]["minio_client"] == "minio-client"


def test_cad_xt_export_runtime_uses_local_prt_without_minio():
    from mold_cost.infrastructure.cad.cad_xt_export_runtime import export_xt_files

    calls = []

    class _FakeDbManager:
        def get_prt_file_path(self, _job_id):
            return r"D:\cad\demo.prt"

    class _FakeStorageManager:
        async def get_file(self, source, save_path, use_minio=False):
            calls.append((source, save_path, use_minio))
            return True

    result = asyncio.run(
        export_xt_files(
            job_id="job-3",
            temp_dir="D:/temp/cad",
            export_files=[{"sub_code": "A1"}],
            storage_manager=_FakeStorageManager(),
            db_manager=_FakeDbManager(),
            minio_client="minio-client",
            export_xt_from_prt=lambda **_kwargs: {},
            nx_importer=lambda: object(),
        )
    )

    assert result == {}
    assert calls == [(r"D:\cad\demo.prt", "D:/temp/cad\\source.prt", False)]


def test_cad_xt_export_runtime_exports_matching_components_with_nxopen():
    from mold_cost.infrastructure.cad.cad_xt_export_runtime import export_xt_from_prt_with_nxopen

    uploads = []
    exporter_instances = []

    class _FakePrototype:
        def __init__(self, full_path):
            self.FullPath = full_path

    class _FakeComponent:
        def __init__(self, full_path):
            self.Prototype = _FakePrototype(full_path)

    class _FakeComponentAssembly:
        @staticmethod
        def GetComponents():
            return [
                _FakeComponent(r"D:\cad\P-001.prt"),
                _FakeComponent(r"D:\cad\P-002.prt"),
            ]

    class _FakeAssemblyPart:
        ComponentAssembly = _FakeComponentAssembly()

        def __init__(self):
            self.closed = False

        def Close(self, *_args):
            self.closed = True

    class _FakeExporter:
        def __init__(self):
            self.ExportFrom = None
            self.InputFile = None
            self.OutputFile = None
            self.FlattenAssembly = None
            self.destroyed = False
            exporter_instances.append(self)

        def Commit(self):
            with open(self.OutputFile, "w", encoding="utf-8") as file:
                file.write(self.InputFile)

        def Destroy(self):
            self.destroyed = True

    class _FakeDexManager:
        @staticmethod
        def CreateParasolidExporter():
            return _FakeExporter()

    class _FakeParts:
        def __init__(self, assembly_part):
            self._assembly_part = assembly_part

        def Open(self, _prt_local):
            return self._assembly_part

        @staticmethod
        def SetDisplay(*_args):
            return None

        @staticmethod
        def SetWork(*_args):
            return None

    class _FakeSession:
        def __init__(self, assembly_part):
            self.Parts = _FakeParts(assembly_part)
            self.DexManager = _FakeDexManager()

    assembly_part = _FakeAssemblyPart()
    fake_nxopen = type(
        "_FakeNXOpen",
        (),
        {
            "Session": type(
                "_FakeSessionAccessor",
                (),
                {"GetSession": staticmethod(lambda: _FakeSession(assembly_part))},
            ),
            "BasePart": type(
                "_FakeBasePart",
                (),
                {"CloseWholeTree": type("_CloseWholeTree", (), {"TrueValue": True})},
            ),
            "ParasolidExporter": type(
                "_FakeParasolidExporter",
                (),
                {"ExportFromOption": type("_ExportFromOption", (), {"ExistingPart": "existing-part"})},
            ),
        },
    )

    class _FakeMinioClient:
        def upload_file(self, local_path, minio_path):
            uploads.append((local_path, minio_path))
            return True

    with tempfile.TemporaryDirectory(prefix="cad-xt-export-") as temp_dir:
        result = export_xt_from_prt_with_nxopen(
            prt_local=f"{temp_dir}\\source.prt",
            export_files=[
                {"sub_code": "SG-1", "part_code": "P-001"},
                {"sub_code": "SG-2", "part_code": "P-002-A"},
                {"sub_code": "SG-3", "part_code": "P-404"},
            ],
            temp_dir=temp_dir,
            xt_minio_base="xt/2026/04/job-9",
            minio_client=_FakeMinioClient(),
            nx_importer=lambda: fake_nxopen,
        )

    assert result == {
        "SG-1": "xt/2026/04/job-9/P-001.x_t",
        "SG-2": "xt/2026/04/job-9/P-002-A.x_t",
    }
    assert uploads[0][0].endswith("P-001.x_t")
    assert uploads[0][1] == "xt/2026/04/job-9/P-001.x_t"
    assert uploads[1][0].endswith("P-002-A.x_t")
    assert uploads[1][1] == "xt/2026/04/job-9/P-002-A.x_t"
    assert [exporter.InputFile for exporter in exporter_instances] == [r"D:\cad\P-001.prt", r"D:\cad\P-002.prt"]
    assert all(exporter.ExportFrom == "existing-part" for exporter in exporter_instances)
    assert all(exporter.FlattenAssembly is True for exporter in exporter_instances)
    assert all(exporter.destroyed is True for exporter in exporter_instances)
    assert assembly_part.closed is True
