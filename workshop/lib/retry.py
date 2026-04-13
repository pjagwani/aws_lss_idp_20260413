"""Retry with exponential backoff for LLM calls.

Max 3 attempts, base delay 1s, max delay 10s.
Handles rate limiting by queuing.
"""

import time
import logging
from typing import Callable, TypeVar

from . import config_loader

T = TypeVar("T")
logger = logging.getLogger(__name__)


class RetryExhausted(Exception):
    """All retry attempts failed."""

    def __init__(self, attempts: int, last_error: Exception):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Failed after {attempts} attempts: {last_error}")


def with_retry(fn: Callable[[], T], context: str = "LLM call") -> T:
    """Execute fn with exponential backoff retry.

    Returns the result of fn on success.
    Raises RetryExhausted after all attempts fail.
    """
    cfg = config_loader.get("retry", {})
    max_attempts = cfg.get("max_attempts", 3)
    base_delay = cfg.get("base_delay_seconds", 1.0)
    max_delay = cfg.get("max_delay_seconds", 10.0)

    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as e:
            last_error = e
            error_str = str(e)

            # Don't retry on access denied or validation errors
            if "AccessDeniedException" in error_str or "ValidationException" in error_str:
                raise

            if attempt < max_attempts:
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                logger.warning(
                    "%s attempt %d/%d failed: %s. Retrying in %.1fs",
                    context, attempt, max_attempts, e, delay,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "%s failed after %d attempts: %s",
                    context, max_attempts, e,
                )

    raise RetryExhausted(max_attempts, last_error)
