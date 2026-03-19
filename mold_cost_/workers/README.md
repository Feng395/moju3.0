# Workers

RabbitMQ-backed background processors live in this directory.

## Current workers

- `orchestrator_worker.py`
  Consumes `job_processing` and starts the main orchestration flow.
- `pricing_recalculate_worker.py`
  Consumes `pricing_recalculate` and runs pricing recalculation jobs.
- `review_worker.py`
  Consumes `review_queue` and starts the review workflow.
- `all_tasks_worker.py`
  Multi-queue worker for the main business queues.

## Typical startup commands

```bash
python -m workers.orchestrator_worker
python -m workers.pricing_recalculate_worker
python -m workers.review_worker
python -m workers.all_tasks_worker
```

## Queue ownership

- `job_processing` -> `orchestrator_worker.py`
- `pricing_recalculate` -> `pricing_recalculate_worker.py`
- `review_queue` -> `review_worker.py`
