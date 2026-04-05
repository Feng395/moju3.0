"""Tests for the src-owned CAD material-line runtime."""

from __future__ import annotations

from refactor_bootstrap import ensure_src_path

ensure_src_path()


def test_cad_material_line_runtime_processes_files_and_saves_debug(monkeypatch):
    from mold_cost.infrastructure.cad.cad_material_line_runtime import process_material_lines

    calls = []

    class _FakeIntegrator:
        def __init__(self, enable=True):
            calls.append(("init", enable))

        def add_material_lines_to_subgraph(self, **kwargs):
            calls.append(("add", kwargs))
            return True

        def print_stats(self):
            calls.append(("stats",))

    monkeypatch.setenv("ENABLE_MATERIAL_LINES", "true")
    monkeypatch.setenv("SAVE_MATERIAL_LINE_DEBUG_FILES", "true")

    result = process_material_lines(
        job_id="job-1",
        export_files=[
            {"sub_code": "SG-1", "local_path": "D:/temp/SG-1.dxf", "part_name": "零件A", "part_code": "P-A"},
            {"sub_code": "SG-2", "local_path": "D:/temp/SG-2.dxf", "part_name": "零件B", "part_code": "P-B"},
        ],
        region_info_map={
            "SG-1": {"region": {"x": 1}},
            "SG-2": {"region": {"x": 2}},
        },
        material_line_available=True,
        integrator_factory=_FakeIntegrator,
        resolve_subgraph_lwt=lambda local_path, region: (
            ({"L": 10.0, "W": 20.0, "T": 30.0}, "resolved") if local_path.endswith("SG-1.dxf") else (None, "missing")
        ),
        save_debug_files=lambda job_id, export_files: calls.append(("debug", job_id, export_files)) or "D:/debug/job-1",
    )

    assert result == {"processed": True, "debug_output_dir": "D:/debug/job-1"}
    assert calls == [
        ("init", True),
        (
            "add",
            {
                "dxf_path": "D:/temp/SG-1.dxf",
                "lwt": {"L": 10.0, "W": 20.0, "T": 30.0},
                "sub_code": "SG-1",
                "part_info": {"part_name": "零件A", "part_code": "P-A", "lwt_source": "resolved"},
            },
        ),
        ("stats",),
        (
            "debug",
            "job-1",
            [
                {"sub_code": "SG-1", "local_path": "D:/temp/SG-1.dxf", "part_name": "零件A", "part_code": "P-A"},
                {"sub_code": "SG-2", "local_path": "D:/temp/SG-2.dxf", "part_name": "零件B", "part_code": "P-B"},
            ],
        ),
    ]


def test_cad_material_line_runtime_skips_when_disabled(monkeypatch):
    from mold_cost.infrastructure.cad.cad_material_line_runtime import process_material_lines

    monkeypatch.setenv("ENABLE_MATERIAL_LINES", "false")

    result = process_material_lines(
        job_id="job-2",
        export_files=[{"sub_code": "SG-1"}],
        region_info_map={},
        material_line_available=True,
        integrator_factory=lambda **_kwargs: None,
        resolve_subgraph_lwt=lambda *_args: (None, "missing"),
        save_debug_files=lambda *_args: "ignored",
    )

    assert result == {"processed": False, "debug_output_dir": None}
