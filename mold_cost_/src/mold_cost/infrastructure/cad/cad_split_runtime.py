"""Runtime helpers for the CAD split gateway."""

from __future__ import annotations

from typing import Any, Awaitable, Callable


EntryPointLoader = Callable[[], tuple[Callable[..., Awaitable[dict[str, Any]]], Callable[..., Any]]]


async def run_cad_split(
    *,
    dwg_url: str | None,
    job_id: str,
    minio_client: Any | None,
    load_entrypoints: EntryPointLoader,
) -> dict[str, Any]:
    """Run the legacy CAD split entrypoints behind a src-owned runtime boundary."""

    chaitu_process, init_managers = load_entrypoints()
    # 中文说明：先初始化 legacy manager，再执行拆图主流程，保持历史调用时序不变。
    init_managers(minio_client=minio_client)
    return await chaitu_process(
        dwg_url=dwg_url,
        job_id=job_id,
        minio_client=minio_client,
    )
