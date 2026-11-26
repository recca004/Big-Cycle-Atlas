import pytest

from app.services.rate_limiter import AsyncRequestBudget


@pytest.mark.asyncio
async def test_request_budget_enforces_rolling_window():
    now = 0.0
    slept: list[float] = []

    def clock() -> float:
        return now

    async def sleeper(seconds: float) -> None:
        nonlocal now
        slept.append(seconds)
        now += seconds

    budget = AsyncRequestBudget(
        max_requests=2,
        window_seconds=10.0,
        now=clock,
        sleep=sleeper,
    )

    await budget.acquire()
    await budget.acquire()
    await budget.acquire()

    assert slept == [5.0, 5.0]
    assert now == 10.0


@pytest.mark.asyncio
async def test_request_budget_uses_minimum_spacing_before_window_limit():
    now = 0.0
    slept: list[float] = []

    def clock() -> float:
        return now

    async def sleeper(seconds: float) -> None:
        nonlocal now
        slept.append(seconds)
        now += seconds

    budget = AsyncRequestBudget(
        max_requests=4,
        window_seconds=20.0,
        now=clock,
        sleep=sleeper,
    )

    await budget.acquire()
    await budget.acquire()

    assert slept == [5.0]
