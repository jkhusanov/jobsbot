import pytest

from jobsbot.validation import (
    UZ_OPERATOR_PREFIXES,
    normalise_phone,
    validate_cv_document,
    validate_email_address,
    validate_name,
    validate_phone,
)

# --- Phone --------------------------------------------------------------------


@pytest.mark.parametrize("prefix", UZ_OPERATOR_PREFIXES)
def test_phone_accepts_every_uzbek_operator_prefix(prefix: str) -> None:
    raw = f"+998{prefix}1234567"
    result = validate_phone(raw)
    assert result.ok, f"prefix {prefix} should be valid"
    assert result.value == raw


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("+998 90 123 45 67", "+998901234567"),
        ("+998-90-123-45-67", "+998901234567"),
        ("998901234567", "+998901234567"),
        ("0901234567", "+998901234567"),
        ("901234567", "+998901234567"),
        ("+998901234567", "+998901234567"),
    ],
)
def test_phone_normalises_common_uzbek_formats(raw: str, expected: str) -> None:
    assert normalise_phone(raw) == expected
    result = validate_phone(raw)
    assert result.ok
    assert result.value == expected


@pytest.mark.parametrize(
    "raw",
    [
        "+79161234567",          # Russian
        "+12025551234",          # US
        "+998011234567",         # invalid prefix 01
        "+998841234567",         # 84 is not allocated
        "+998901234",            # too short
        "+99890123456789",       # too long
        "abcdefg",
        "",
        "+",
        "998",
        "+998 90 123 45",        # too few digits even after stripping
    ],
)
def test_phone_rejects_invalid(raw: str) -> None:
    assert not validate_phone(raw).ok


# --- Email --------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "user@example.com",
        "first.last@sub.example.co",
        "u+tag@example.org",
        "  user@example.com  ",
    ],
)
def test_email_accepts_valid(raw: str) -> None:
    result = validate_email_address(raw)
    assert result.ok
    assert result.value is not None
    assert "@" in result.value


@pytest.mark.parametrize(
    "raw",
    [
        "no-at-sign",
        "user@",
        "@example.com",
        "user@@example.com",
        "user@example",
        "user @example.com",
        "",
    ],
)
def test_email_rejects_invalid(raw: str) -> None:
    assert not validate_email_address(raw).ok


# --- Name ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Akmal Karimov", "Akmal Karimov"),
        ("  Akmal   Karimov  ", "Akmal Karimov"),
        ("Olim", "Olim"),
        ("Said-Akbar O'g'li", "Said-Akbar O'g'li"),
        ("Ёқуб Кенжаев", "Ёқуб Кенжаев"),
    ],
)
def test_name_accepts_valid(raw: str, expected: str) -> None:
    result = validate_name(raw)
    assert result.ok
    assert result.value == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "A",            # too short after trim
        "12345",        # no letters
        "------",       # no letters
        "x" * 101,      # too long
    ],
)
def test_name_rejects_invalid(raw: str) -> None:
    assert not validate_name(raw).ok


# --- CV document --------------------------------------------------------------


def test_cv_accepts_pdf() -> None:
    result = validate_cv_document(
        mime_type="application/pdf",
        file_name="cv.pdf",
        size_bytes=1024,
        max_size_bytes=20 * 1024 * 1024,
    )
    assert result.ok


def test_cv_accepts_docx() -> None:
    result = validate_cv_document(
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        file_name="my-cv.DOCX",
        size_bytes=1024,
        max_size_bytes=20 * 1024 * 1024,
    )
    assert result.ok


def test_cv_accepts_doc() -> None:
    result = validate_cv_document(
        mime_type="application/msword",
        file_name="cv.doc",
        size_bytes=1024,
        max_size_bytes=20 * 1024 * 1024,
    )
    assert result.ok


def test_cv_rejects_extension_only_when_mime_missing() -> None:
    result = validate_cv_document(
        mime_type=None,
        file_name="cv.pdf",
        size_bytes=1024,
        max_size_bytes=20 * 1024 * 1024,
    )
    assert not result.ok
    assert result.error == "invalid_cv_type"


def test_cv_rejects_html_with_pdf_mime() -> None:
    """Catch the spoof: cv.html with mime application/pdf must not be accepted."""
    result = validate_cv_document(
        mime_type="application/pdf",
        file_name="cv.html",
        size_bytes=1024,
        max_size_bytes=20 * 1024 * 1024,
    )
    assert not result.ok
    assert result.error == "invalid_cv_type"


def test_cv_rejects_pdf_extension_with_executable_mime() -> None:
    result = validate_cv_document(
        mime_type="application/x-msdownload",
        file_name="cv.pdf",
        size_bytes=1024,
        max_size_bytes=20 * 1024 * 1024,
    )
    assert not result.ok
    assert result.error == "invalid_cv_type"


def test_cv_rejects_image() -> None:
    result = validate_cv_document(
        mime_type="image/png",
        file_name="cv.png",
        size_bytes=1024,
        max_size_bytes=20 * 1024 * 1024,
    )
    assert not result.ok
    assert result.error == "invalid_cv_type"


def test_cv_rejects_oversize() -> None:
    result = validate_cv_document(
        mime_type="application/pdf",
        file_name="cv.pdf",
        size_bytes=21 * 1024 * 1024,
        max_size_bytes=20 * 1024 * 1024,
    )
    assert not result.ok
    assert result.error == "invalid_cv_size"


def test_name_strips_bidi_override() -> None:
    """U+202E (Right-to-Left Override) must not survive in a stored name."""
    result = validate_name("Akmal‮Karimov")
    assert result.ok
    assert "‮" not in (result.value or "")
    assert result.value == "AkmalKarimov"


def test_name_strips_zero_width_chars() -> None:
    result = validate_name("Akmal​Karimov‌‍")
    assert result.ok
    assert all(ch not in (result.value or "") for ch in ("​", "‌", "‍"))


def test_name_strips_c0_controls() -> None:
    result = validate_name("Akmal\x00Karimov\x07")
    assert result.ok
    assert "\x00" not in (result.value or "")
    assert "\x07" not in (result.value or "")


def test_phone_normalises_through_unicode_bidi() -> None:
    result = validate_phone("‮+998901234567‬")
    assert result.ok
    assert result.value == "+998901234567"


def test_cv_rejects_zero_size() -> None:
    result = validate_cv_document(
        mime_type="application/pdf",
        file_name="cv.pdf",
        size_bytes=0,
        max_size_bytes=20 * 1024 * 1024,
    )
    assert not result.ok
    assert result.error == "invalid_cv_size"
