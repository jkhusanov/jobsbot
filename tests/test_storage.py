import datetime as dt
from pathlib import Path

import pytest

from jobsbot.services.storage import NewApplication, Storage


@pytest.fixture
async def storage(tmp_path: Path) -> Storage:
    s = Storage(tmp_path / "test.db")
    await s.init()
    return s


def _new_app(**overrides: object) -> NewApplication:
    base = dict(
        job_id="j1",
        job_title="Backend",
        tg_user_id=42,
        tg_username="alice",
        full_name="Alice A.",
        phone="+998901234567",
        email="alice@example.com",
        cv_file_id="file_id_1",
        cv_file_unique_id="unique_1",
        cv_file_name="cv.pdf",
        cv_mime_type="application/pdf",
        cv_size_bytes=1234,
    )
    base.update(overrides)
    return NewApplication(**base)  # type: ignore[arg-type]


async def test_insert_and_get_round_trip(storage: Storage) -> None:
    app_id = await storage.insert_application(_new_app())
    assert app_id > 0
    app = await storage.get(app_id)
    assert app is not None
    assert app.full_name == "Alice A."
    assert app.status == "pending_admin_send"
    assert app.delivery_attempts == 0


async def test_mark_sent(storage: Storage) -> None:
    app_id = await storage.insert_application(_new_app())
    await storage.mark_sent(app_id)
    app = await storage.get(app_id)
    assert app is not None
    assert app.status == "sent"
    assert app.sent_at is not None


async def test_record_failure_non_terminal(storage: Storage) -> None:
    app_id = await storage.insert_application(_new_app())
    await storage.record_delivery_failure(app_id, "boom", terminal=False)
    app = await storage.get(app_id)
    assert app is not None
    assert app.status == "pending_admin_send"
    assert app.delivery_attempts == 1
    assert app.last_error == "boom"


async def test_record_failure_terminal(storage: Storage) -> None:
    app_id = await storage.insert_application(_new_app())
    await storage.record_delivery_failure(app_id, "gave up", terminal=True)
    app = await storage.get(app_id)
    assert app is not None
    assert app.status == "failed"


async def test_list_pending_only_includes_pending(storage: Storage) -> None:
    a = await storage.insert_application(_new_app(job_id="a"))
    await storage.insert_application(_new_app(job_id="b"))
    await storage.mark_sent(a)
    pending = await storage.list_pending()
    assert {p.job_id for p in pending} == {"b"}


async def test_count_recent_for_user_and_job(storage: Storage) -> None:
    await storage.insert_application(_new_app(job_id="x", tg_user_id=1))
    await storage.insert_application(_new_app(job_id="x", tg_user_id=1))
    await storage.insert_application(_new_app(job_id="y", tg_user_id=1))
    await storage.insert_application(_new_app(job_id="x", tg_user_id=2))

    since = dt.datetime.now(dt.UTC) - dt.timedelta(days=1)
    assert await storage.count_recent_for_user_and_job(1, "x", since) == 2
    assert await storage.count_recent_for_user_and_job(1, "y", since) == 1
    assert await storage.count_recent_for_user_and_job(2, "x", since) == 1
    assert await storage.count_recent_for_user_and_job(99, "x", since) == 0

    future = dt.datetime.now(dt.UTC) + dt.timedelta(days=1)
    assert await storage.count_recent_for_user_and_job(1, "x", future) == 0
