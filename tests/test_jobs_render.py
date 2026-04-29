from jobsbot.handlers.jobs import MAX_MESSAGE_CHARS, render_job_card
from jobsbot.services.jobs_api import Job


def test_render_short_card_unchanged() -> None:
    job = Job(
        id="j1", title="Backend", company="Acme",
        location="Tashkent", description="Build stuff.",
    )
    rendered = render_job_card(job)
    assert "Backend" in rendered
    assert "Acme" in rendered
    assert "Build stuff." in rendered


def test_render_caps_huge_description() -> None:
    huge = "x" * 50_000
    job = Job(id="j1", title="T", description=huge)
    rendered = render_job_card(job)
    assert len(rendered) <= MAX_MESSAGE_CHARS
    assert rendered.endswith("...")


def test_render_escapes_html() -> None:
    job = Job(
        id="j1",
        title="<script>alert(1)</script>",
        company="A & B",
        description="<b>bold</b>",
    )
    rendered = render_job_card(job)
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "A &amp; B" in rendered
    assert "&lt;b&gt;bold" in rendered
