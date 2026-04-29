from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass

import aiohttp

log = logging.getLogger(__name__)

# Hard cap on the jobs API response so a misbehaving upstream can't OOM the
# bot. 5 MB fits ~1k typical job postings — well above any realistic load.
MAX_PAYLOAD_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class Job:
    id: str
    title: str
    company: str | None = None
    location: str | None = None
    employment_type: str | None = None
    salary: str | None = None
    description: str | None = None
    posted_at: str | None = None


class JobsApiError(Exception):
    """Raised on any failure to fetch / parse the jobs endpoint."""


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


class JobsApi:
    def __init__(
        self,
        url: str,
        *,
        auth_header: str | None = None,
        timeout_seconds: int = 10,
        cache_ttl_seconds: int = 60,
    ) -> None:
        self._url = url
        self._auth_header = auth_header
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._cache_ttl = cache_ttl_seconds
        self._cache: tuple[float, list[Job]] | None = None
        self._lock = asyncio.Lock()

    async def fetch(self, *, force_refresh: bool = False) -> list[Job]:
        async with self._lock:
            now = time.monotonic()
            if (
                not force_refresh
                and self._cache
                and (now - self._cache[0]) < self._cache_ttl
            ):
                return self._cache[1]
            jobs = await self._do_fetch()
            self._cache = (now, jobs)
            return jobs

    def find_in_cache(self, job_id: str) -> Job | None:
        if not self._cache:
            return None
        for job in self._cache[1]:
            if job.id == job_id:
                return job
        return None

    async def _do_fetch(self) -> list[Job]:
        headers = {"Accept": "application/json"}
        if self._auth_header:
            headers["Authorization"] = self._auth_header
        try:
            async with (
                aiohttp.ClientSession(timeout=self._timeout) as session,
                session.get(self._url, headers=headers) as response,
            ):
                if response.status != 200:
                    raise JobsApiError(
                        f"jobs API returned status {response.status}"
                    )
                cl = response.headers.get("Content-Length")
                if cl is not None and cl.isdigit() and int(cl) > MAX_PAYLOAD_BYTES:
                    raise JobsApiError(
                        f"jobs API response too large: {cl} bytes"
                    )
                # Read up to one byte past the limit so we can detect overage
                # for responses without a Content-Length header.
                body = await response.content.read(MAX_PAYLOAD_BYTES + 1)
                if len(body) > MAX_PAYLOAD_BYTES:
                    raise JobsApiError("jobs API response too large")
        except (TimeoutError, aiohttp.ClientError) as e:
            raise JobsApiError(f"jobs API request failed: {e}") from e
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise JobsApiError(f"jobs API returned invalid JSON: {e}") from e
        if not isinstance(payload, list):
            raise JobsApiError("jobs API response is not a JSON array")

        jobs: list[Job] = []
        for item in payload:
            if not isinstance(item, dict):
                log.warning("skipping non-dict item in jobs payload")
                continue
            jid = item.get("id")
            title = item.get("title")
            if jid in (None, "") or title in (None, ""):
                log.warning("skipping job with missing id/title", extra={"item": item})
                continue
            jobs.append(
                Job(
                    id=str(jid),
                    title=str(title),
                    company=_str_or_none(item.get("company")),
                    location=_str_or_none(item.get("location")),
                    employment_type=_str_or_none(item.get("employment_type")),
                    salary=_str_or_none(item.get("salary")),
                    description=_str_or_none(item.get("description")),
                    posted_at=_str_or_none(item.get("posted_at")),
                )
            )
        return jobs
