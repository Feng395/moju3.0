"""Tests for the src-owned CAD input prepare runtime."""

from __future__ import annotations

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_cad_prepare_runtime_downloads_and_converts():
    import asyncio

    from mold_cost.infrastructure.cad.cad_prepare_runtime import prepare_dxf_input

    calls = []

    class _FakeStorageManager:
        async def get_file(self, source, save_path, use_minio=False):
            calls.append(("storage", source, save_path, use_minio))
            return True

    class _FakeConverter:
        def __init__(self, oda_converter_path):
            calls.append(("converter_init", oda_converter_path))

        def convert_dwg_to_dxf(self, input_path, output_path):
            calls.append(("convert", input_path, output_path))
            return True

    result = asyncio.run(
        prepare_dxf_input(
            dwg_source="dwg/2026/04/demo.dwg",
            use_minio=True,
            temp_dir="D:/temp/cad",
            storage_manager=_FakeStorageManager(),
            converter_factory=_FakeConverter,
            oda_converter_path="D:/tools/ODAFileConverter.exe",
        )
    )

    assert result == {
        "success": True,
        "temp_dwg": "D:/temp/cad\\input.dwg",
        "temp_dxf": "D:/temp/cad\\input.dxf",
    }
    assert calls == [
        ("storage", "dwg/2026/04/demo.dwg", "D:/temp/cad\\input.dwg", True),
        ("converter_init", "D:/tools/ODAFileConverter.exe"),
        ("convert", "D:/temp/cad\\input.dwg", "D:/temp/cad\\input.dxf"),
    ]


def test_cad_prepare_runtime_returns_error_when_download_fails():
    import asyncio

    from mold_cost.infrastructure.cad.cad_prepare_runtime import prepare_dxf_input

    class _FakeStorageManager:
        async def get_file(self, *_args, **_kwargs):
            return False

    result = asyncio.run(
        prepare_dxf_input(
            dwg_source="bucket/demo.dwg",
            use_minio=False,
            temp_dir="D:/temp/cad",
            storage_manager=_FakeStorageManager(),
            converter_factory=lambda _path: None,
            oda_converter_path=None,
        )
    )

    assert result == {
        "success": False,
        "message": "获取 DWG 文件失败",
        "temp_dwg": "D:/temp/cad\\input.dwg",
        "temp_dxf": "D:/temp/cad\\input.dxf",
    }


def test_cad_prepare_runtime_returns_error_when_convert_fails():
    import asyncio

    from mold_cost.infrastructure.cad.cad_prepare_runtime import prepare_dxf_input

    class _FakeStorageManager:
        async def get_file(self, *_args, **_kwargs):
            return True

    class _FakeConverter:
        def __init__(self, _oda_converter_path):
            return None

        def convert_dwg_to_dxf(self, _input_path, _output_path):
            return False

    result = asyncio.run(
        prepare_dxf_input(
            dwg_source="bucket/demo.dwg",
            use_minio=True,
            temp_dir="D:/temp/cad",
            storage_manager=_FakeStorageManager(),
            converter_factory=_FakeConverter,
            oda_converter_path="D:/tools/oda.exe",
        )
    )

    assert result == {
        "success": False,
        "message": "DWG -> DXF 转换失败",
        "temp_dwg": "D:/temp/cad\\input.dwg",
        "temp_dxf": "D:/temp/cad\\input.dxf",
    }
