from typing import Any

import pytest

from jobsbot.middlewares import ThrottlingMiddleware


class _FakeUser:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


@pytest.fixture
def call_counter() -> dict[str, int]:
    return {"calls": 0}


@pytest.fixture
def handler(call_counter: dict[str, int]):
    async def _handler(event: object, data: dict[str, Any]) -> str:
        call_counter["calls"] += 1
        return "ok"

    return _handler


async def test_passes_under_limit(handler, call_counter) -> None:
    mw = ThrottlingMiddleware(max_events=5, window_seconds=60.0)
    user = _FakeUser(42)
    for _ in range(5):
        result = await mw(handler, object(), {"event_from_user": user})
        assert result == "ok"
    assert call_counter["calls"] == 5


async def test_drops_over_limit(handler, call_counter) -> None:
    mw = ThrottlingMiddleware(max_events=3, window_seconds=60.0)
    user = _FakeUser(42)
    for _ in range(3):
        await mw(handler, object(), {"event_from_user": user})
    result = await mw(handler, object(), {"event_from_user": user})
    assert result is None
    assert call_counter["calls"] == 3


async def test_isolates_users(handler, call_counter) -> None:
    mw = ThrottlingMiddleware(max_events=2, window_seconds=60.0)
    a = _FakeUser(1)
    b = _FakeUser(2)
    await mw(handler, object(), {"event_from_user": a})
    await mw(handler, object(), {"event_from_user": a})
    # a is now at limit; b should still go through.
    result = await mw(handler, object(), {"event_from_user": b})
    assert result == "ok"
    assert call_counter["calls"] == 3


async def test_no_user_passes_through(handler, call_counter) -> None:
    mw = ThrottlingMiddleware(max_events=1, window_seconds=60.0)
    # Pretend there's no user (e.g. an edited service message).
    for _ in range(5):
        result = await mw(handler, object(), {"event_from_user": None})
        assert result == "ok"
    assert call_counter["calls"] == 5
