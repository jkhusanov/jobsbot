from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

log = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """Drop updates from a user that exceed `max_events` in a `window_seconds` window.

    Generous defaults: a real human filling the apply FSM produces ~10 events
    in a few minutes, well under the limit. Anything faster than 30/min is
    automated and we silently drop it — no error message, no log spam past
    the first sample per user.
    """

    def __init__(
        self,
        max_events: int = 30,
        window_seconds: float = 60.0,
        max_tracked_users: int = 50_000,
    ) -> None:
        self._max = max_events
        self._window = window_seconds
        self._max_tracked = max_tracked_users
        self._events: dict[int, deque[float]] = defaultdict(deque)
        self._warned: set[int] = set()
        self._last_gc: float = 0.0

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        now = time.monotonic()
        cutoff = now - self._window

        # Periodically drop empty deques so an ever-growing user base
        # doesn't leak memory. Cheap: O(tracked) once per window at most.
        if now - self._last_gc > self._window:
            self._gc(cutoff)
            self._last_gc = now

        events = self._events[user.id]
        while events and events[0] < cutoff:
            events.popleft()
        if len(events) >= self._max:
            if user.id not in self._warned:
                log.warning(
                    "throttling user",
                    extra={"user_id": user.id, "events_in_window": len(events)},
                )
                self._warned.add(user.id)
            return None
        events.append(now)
        # Reset the warn flag once they're back under the limit.
        if user.id in self._warned and len(events) < self._max // 2:
            self._warned.discard(user.id)
        return await handler(event, data)

    def _gc(self, cutoff: float) -> None:
        # Drop any user whose entire window has expired.
        stale = [uid for uid, ev in self._events.items() if not ev or ev[-1] < cutoff]
        for uid in stale:
            self._events.pop(uid, None)
            self._warned.discard(uid)
        # Hard cap as a final safeguard against pathological growth.
        if len(self._events) > self._max_tracked:
            # Drop the oldest half (deterministic by insertion order in py3.7+).
            to_drop = list(self._events.keys())[: len(self._events) // 2]
            for uid in to_drop:
                self._events.pop(uid, None)
                self._warned.discard(uid)
