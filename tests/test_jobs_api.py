
import pytest
from aioresponses import aioresponses

from jobsbot.services.jobs_api import JobsApi, JobsApiError

URL = "https://api.example.com/jobs"


@pytest.fixture
def mock_http() -> aioresponses:
    with aioresponses() as m:
        yield m


async def test_fetch_parses_full_payload(mock_http: aioresponses) -> None:
    mock_http.get(
        URL,
        payload=[
            {
                "id": "j1",
                "title": "Backend Developer",
                "company": "Acme",
                "location": "Tashkent",
                "employment_type": "Full-time",
                "salary": "15-25 mln",
                "description": "Build things.",
                "posted_at": "2026-04-20T10:00:00Z",
            }
        ],
    )
    api = JobsApi(URL, cache_ttl_seconds=0)
    jobs = await api.fetch()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.id == "j1"
    assert job.title == "Backend Developer"
    assert job.company == "Acme"
    assert job.salary == "15-25 mln"


async def test_fetch_skips_items_missing_id_or_title(mock_http: aioresponses) -> None:
    mock_http.get(
        URL,
        payload=[
            {"id": "ok", "title": "Good"},
            {"id": "no-title"},
            {"title": "no-id"},
            "not a dict",
            {"id": "", "title": "empty id"},
        ],
    )
    api = JobsApi(URL, cache_ttl_seconds=0)
    jobs = await api.fetch()
    assert [j.id for j in jobs] == ["ok"]


async def test_fetch_raises_on_non_2xx(mock_http: aioresponses) -> None:
    mock_http.get(URL, status=500, body="oops")
    api = JobsApi(URL, cache_ttl_seconds=0)
    with pytest.raises(JobsApiError):
        await api.fetch()


async def test_fetch_raises_on_non_array_payload(mock_http: aioresponses) -> None:
    mock_http.get(URL, payload={"not": "an array"})
    api = JobsApi(URL, cache_ttl_seconds=0)
    with pytest.raises(JobsApiError):
        await api.fetch()


async def test_fetch_uses_cache(mock_http: aioresponses) -> None:
    mock_http.get(URL, payload=[{"id": "a", "title": "A"}])
    api = JobsApi(URL, cache_ttl_seconds=60)
    first = await api.fetch()
    second = await api.fetch()  # would 500 if it actually requested again
    assert first == second


async def test_force_refresh_bypasses_cache(mock_http: aioresponses) -> None:
    mock_http.get(URL, payload=[{"id": "a", "title": "A"}])
    mock_http.get(URL, payload=[{"id": "b", "title": "B"}])
    api = JobsApi(URL, cache_ttl_seconds=60)
    first = await api.fetch()
    second = await api.fetch(force_refresh=True)
    assert [j.id for j in first] == ["a"]
    assert [j.id for j in second] == ["b"]


async def test_find_in_cache(mock_http: aioresponses) -> None:
    mock_http.get(URL, payload=[{"id": "a", "title": "A"}, {"id": "b", "title": "B"}])
    api = JobsApi(URL, cache_ttl_seconds=60)
    assert api.find_in_cache("a") is None  # nothing cached yet
    await api.fetch()
    assert api.find_in_cache("a") is not None
    assert api.find_in_cache("missing") is None


async def test_auth_header_is_sent(mock_http: aioresponses) -> None:
    sent_headers: dict[str, str] = {}

    def callback(url, **kwargs):  # type: ignore[no-untyped-def]
        sent_headers.update(kwargs.get("headers") or {})
        from aioresponses.core import CallbackResult

        return CallbackResult(status=200, payload=[])

    mock_http.get(URL, callback=callback)
    api = JobsApi(URL, auth_header="Bearer secret", cache_ttl_seconds=0)
    await api.fetch()
    assert sent_headers.get("Authorization") == "Bearer secret"


async def test_timeout_raises_jobs_api_error(mock_http: aioresponses) -> None:
    mock_http.get(URL, exception=TimeoutError())
    api = JobsApi(URL, cache_ttl_seconds=0, timeout_seconds=1)
    with pytest.raises(JobsApiError):
        await api.fetch()


async def test_fetch_rejects_oversize_response(mock_http: aioresponses) -> None:
    from jobsbot.services.jobs_api import MAX_PAYLOAD_BYTES

    huge = b"x" * (MAX_PAYLOAD_BYTES + 100)
    mock_http.get(URL, body=huge)
    api = JobsApi(URL, cache_ttl_seconds=0)
    with pytest.raises(JobsApiError):
        await api.fetch()


async def test_fetch_rejects_invalid_json(mock_http: aioresponses) -> None:
    mock_http.get(URL, body=b"not json at all")
    api = JobsApi(URL, cache_ttl_seconds=0)
    with pytest.raises(JobsApiError):
        await api.fetch()
