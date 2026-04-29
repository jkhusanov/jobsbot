import pytest
from pydantic import ValidationError

from jobsbot.config import Settings


def _env(**kwargs: str) -> dict[str, str]:
    base = {
        "BOT_TOKEN": "1234567890:" + "A" * 35,
        "JOBS_API_URL": "https://api.example.com/jobs",
    }
    base.update(kwargs)
    return base


def test_minimal_valid_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in _env().items():
        monkeypatch.setenv(k, v)
    s = Settings()
    assert s.bot_token.startswith("1234567890:")
    assert s.jobs_api_url == "https://api.example.com/jobs"


def test_rejects_jobs_api_url_without_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in _env(JOBS_API_URL="api.example.com/jobs").items():
        monkeypatch.setenv(k, v)
    with pytest.raises(ValidationError):
        Settings()


def test_rejects_jobs_api_url_with_wrong_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in _env(JOBS_API_URL="ftp://api.example.com/jobs").items():
        monkeypatch.setenv(k, v)
    with pytest.raises(ValidationError):
        Settings()


def test_accepts_http_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in _env(JOBS_API_URL="http://api.example.com/jobs").items():
        monkeypatch.setenv(k, v)
    Settings()  # no exception


def test_rejects_obviously_malformed_bot_token(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in _env(BOT_TOKEN="paste_your_token_here").items():
        monkeypatch.setenv(k, v)
    with pytest.raises(ValidationError):
        Settings()


def test_rejects_bearer_prefix_in_bot_token(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in _env(BOT_TOKEN="Bearer 1234567890:" + "A" * 35).items():
        monkeypatch.setenv(k, v)
    with pytest.raises(ValidationError):
        Settings()


def test_strips_whitespace_in_bot_token(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = "  1234567890:" + "A" * 35 + "  "
    for k, v in _env(BOT_TOKEN=raw).items():
        monkeypatch.setenv(k, v)
    s = Settings()
    assert not s.bot_token.startswith(" ")
    assert not s.bot_token.endswith(" ")
