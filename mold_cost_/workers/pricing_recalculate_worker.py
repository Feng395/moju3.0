"""Pricing recalculation worker."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from refactor_bootstrap import ensure_src_path
from shared.message_queue import MessageQueue, QUEUE_PRICING_RECALCULATE
from shared.unified_logging import get_logger, init_logging

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
ensure_src_path()

from mold_cost.domain.pricing.services.pricing_service import pricing_service

init_logging()
logger = get_logger("workers.pricing_recalculate_worker")


class PricingRecalculateWorker:
    """Consume pricing recalculation messages."""

    def __init__(self):
        self.mq = MessageQueue()
        logger.info("PricingRecalculateWorker initialized")

    async def start(self):
        logger.info("=" * 80)
        logger.info("PricingRecalculateWorker starting")
        logger.info("=" * 80)
        logger.info("Listening queue: %s", QUEUE_PRICING_RECALCULATE)
        await self.mq.consume(
            queue_name=QUEUE_PRICING_RECALCULATE,
            callback=self.handle_message,
            early_ack=True,
        )

    async def handle_message(self, message: dict):
        job_id = message.get("job_id")
        subgraph_ids = message.get("subgraph_ids", [])
        user_params = message.get("user_params", {})
        logger.info(
            "Received pricing message: job_id=%s subgraph_count=%s",
            job_id,
            len(subgraph_ids),
        )

        try:
            result = await pricing_service.calculate_batch(
                {
                    "job_id": job_id,
                    "subgraph_ids": subgraph_ids,
                    "user_params": user_params,
                }
            )
            if result.get("status") in {"ok", "partial"}:
                logger.info(
                    "Pricing recalculation completed: job_id=%s total_cost=%s",
                    job_id,
                    result.get("total_cost"),
                )
            else:
                logger.error(
                    "Pricing recalculation failed: job_id=%s message=%s",
                    job_id,
                    result.get("message"),
                )
        except Exception as exc:
            logger.error(
                "Pricing message handling crashed: job_id=%s error=%s",
                job_id,
                exc,
                exc_info=True,
            )


async def main():
    worker = PricingRecalculateWorker()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
