from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    job_title TEXT NOT NULL,
    tg_user_id INTEGER NOT NULL,
    tg_username TEXT,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    cv_file_id TEXT NOT NULL,
    cv_file_unique_id TEXT NOT NULL,
    cv_file_name TEXT,
    cv_mime_type TEXT,
    cv_size_bytes INTEGER,
    status TEXT NOT NULL CHECK (status IN ('pending_admin_send','sent','failed')),
    delivery_attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TEXT NOT NULL,
    sent_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_user ON applications(tg_user_id);
"""


@dataclass(frozen=True)
class NewApplication:
    job_id: str
    job_title: str
    tg_user_id: int
    tg_username: str | None
    full_name: str
    phone: str
    email: str
    cv_file_id: str
    cv_file_unique_id: str
    cv_file_name: str | None
    cv_mime_type: str | None
    cv_size_bytes: int | None


@dataclass(frozen=True)
class Application:
    id: int
    job_id: str
    job_title: str
    tg_user_id: int
    tg_username: str | None
    full_name: str
    phone: str
    email: str
    cv_file_id: str
    cv_file_unique_id: str
    cv_file_name: str | None
    cv_mime_type: str | None
    cv_size_bytes: int | None
    status: str
    delivery_attempts: int
    last_error: str | None
    created_at: str
    sent_at: str | None


def _now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


class Storage:
    def __init__(self, path: Path) -> None:
        self._path = path

    async def init(self) -> None:
        if str(self._path) not in (":memory:", ""):
            self._path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._path) as db:
            # WAL gives us concurrent readers and a non-blocking writer,
            # which matters once the bot has more than one user submitting
            # at the same time. NORMAL synchronous is fine for an audit log.
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")
            await db.execute("PRAGMA foreign_keys=ON")
            await db.executescript(SCHEMA)
            await db.commit()

    async def insert_application(self, app: NewApplication) -> int:
        async with aiosqlite.connect(self._path) as db:
            cursor = await db.execute(
                """
                INSERT INTO applications (
                    job_id, job_title, tg_user_id, tg_username, full_name, phone,
                    email, cv_file_id, cv_file_unique_id, cv_file_name, cv_mime_type,
                    cv_size_bytes, status, delivery_attempts, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    app.job_id, app.job_title, app.tg_user_id, app.tg_username,
                    app.full_name, app.phone, app.email, app.cv_file_id,
                    app.cv_file_unique_id, app.cv_file_name, app.cv_mime_type,
                    app.cv_size_bytes, "pending_admin_send", 0, _now_iso(),
                ),
            )
            await db.commit()
            return int(cursor.lastrowid or 0)

    async def get(self, application_id: int) -> Application | None:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM applications WHERE id=?", (application_id,)
            )
            row = await cursor.fetchone()
            return Application(**dict(row)) if row else None

    async def mark_sent(self, application_id: int) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "UPDATE applications SET status='sent', sent_at=?,"
                " delivery_attempts = delivery_attempts + 1, last_error=NULL"
                " WHERE id=?",
                (_now_iso(), application_id),
            )
            await db.commit()

    async def record_delivery_failure(
        self, application_id: int, error: str, *, terminal: bool
    ) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """
                UPDATE applications
                SET delivery_attempts = delivery_attempts + 1,
                    last_error = ?,
                    status = CASE WHEN ? THEN 'failed' ELSE status END
                WHERE id = ?
                """,
                (error, 1 if terminal else 0, application_id),
            )
            await db.commit()

    async def list_pending(self) -> list[Application]:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM applications WHERE status='pending_admin_send'"
                " ORDER BY id ASC"
            )
            rows = await cursor.fetchall()
            return [Application(**dict(r)) for r in rows]

    async def count_recent_for_user_and_job(
        self, tg_user_id: int, job_id: str, since: dt.datetime
    ) -> int:
        async with aiosqlite.connect(self._path) as db:
            cursor = await db.execute(
                """
                SELECT COUNT(*) FROM applications
                WHERE tg_user_id = ? AND job_id = ? AND created_at >= ?
                """,
                (tg_user_id, job_id, since.astimezone(dt.UTC).isoformat(timespec="seconds")),
            )
            row = await cursor.fetchone()
            return int(row[0]) if row else 0
