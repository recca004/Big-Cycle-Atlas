"""Provider-aware asynchronous request budgets.

Budgets are deliberately enforced before a request is sent. A rolling window
prevents bursts from exceeding a provider's published ceiling, and a minimum
spacing prevents a sequence of otherwise-valid requests from arriving too
quickly. The clock and sleeper are injectable so behavior can be tested
without sleeping for real seconds.
"""
from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field


@dataclass
class AsyncRequestBudget:
    """Enforce a rolling request budget for one provider."""

    max_requests: int
    window_seconds: float
    now: Callable[[], float] = time.monotonic
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
    _request_times: deque[float] = field(default_factory=deque, init=False)
    _next_allowed_at: float = field(default=0.0, init=False)

    @property
    def minimum_interval(self) -> float:
        return self.window_seconds / self.max_requests

    async def acquire(self) -> None:
        """Wait until one request may be sent, then reserve that slot."""
        while True:
            current = self.now()
            while self._request_times and (
                current - self._request_times[0] >= self.window_seconds
            ):
                self._request_times.popleft()

            rolling_available_at = (
                self._request_times[0] + self.window_seconds
                if len(self._request_times) >= self.max_requests
                else current
            )
            allowed_at = max(
                current, self._next_allowed_at, rolling_available_at
            )
            delay = allowed_at - current
            if delay <= 0:
                self._request_times.append(current)
                self._next_allowed_at = max(
                    self._next_allowed_at, current
                ) + self.minimum_interval
                return
            await self.sleep(delay)


# OECD documents an approximate ceiling of 60 requests/hour. Keep a safety
# margin so clock drift and provider-side accounting do not push us over it.
OECD_REQUEST_BUDGET = AsyncRequestBudget(
    max_requests=55,
    window_seconds=3600.0,
)
