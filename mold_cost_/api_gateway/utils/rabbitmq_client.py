"""Compatibility wrapper for the refactored RabbitMQ client."""

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.messaging.rabbitmq_client import RabbitMQClient, rabbitmq_client

__all__ = ["RabbitMQClient", "rabbitmq_client"]
