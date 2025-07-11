import logging
from typing import Dict, List

# In-memory logs for alerts and retry counts - useful for testing
ALERTS: List[str] = []
RETRY_COUNTS: Dict[str, int] = {}


async def log_error(agent_name: str, error: Exception) -> None:
    """Simple error logger used by agents."""
    logger = logging.getLogger(agent_name)
    logger.error("%s", error)


async def send_alert(message: str) -> None:
    """Record alert messages for critical errors."""
    ALERTS.append(message)


def is_critical_error(error: Exception) -> bool:
    """Determine if an error is critical.

    This default implementation treats errors with attribute ``critical=True`` as critical.
    """
    return getattr(error, "critical", False)


def should_retry(error: Exception) -> bool:
    """Determine if an operation should be retried.

    Errors with attribute ``retry=True`` trigger retry logic by default.
    """
    return getattr(error, "retry", False)


async def retry_operation(agent_name: str, error: Exception) -> None:
    """Record that a retry was attempted for testing purposes."""
    RETRY_COUNTS[agent_name] = RETRY_COUNTS.get(agent_name, 0) + 1


async def handle_agent_error(agent_name: str, error: Exception) -> None:
    """Standard error handling used across agents."""
    await log_error(agent_name, error)

    if is_critical_error(error):
        await send_alert(f"Critical error in {agent_name}: {error}")

    if should_retry(error):
        await retry_operation(agent_name, error)
