"""Shared exception types."""


class MoldCostError(Exception):
    """Base exception for the refactored codebase."""


class InfrastructureError(MoldCostError):
    """Raised when an infrastructure dependency fails."""


class WorkflowError(MoldCostError):
    """Raised when workflow orchestration fails."""
