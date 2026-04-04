"""Bridge the existing CAD split flow into the new domain layer."""

from __future__ import annotations


class LegacyCadSplitService:
    async def split(self, dwg_url: str | None, job_id: str, minio_client=None) -> dict:
        from scripts.cad_chaitu.main import chaitu_process, init_managers

        init_managers(minio_client=minio_client)
        return await chaitu_process(dwg_url=dwg_url, job_id=job_id, minio_client=minio_client)


cad_split_service = LegacyCadSplitService()
