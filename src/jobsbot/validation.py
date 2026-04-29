import re
from dataclasses import dataclass

from email_validator import EmailNotValidError, validate_email

UZ_OPERATOR_PREFIXES: tuple[str, ...] = (
    "33", "50", "55",
    "61", "62", "63", "65", "66", "67", "69",
    "70", "71", "72", "73", "74", "75", "77", "78", "79",
    "88",
    "90", "91", "93", "94", "95", "97", "98", "99",
)
_UZ_PHONE_RE = re.compile(r"^\+998(" + "|".join(UZ_OPERATOR_PREFIXES) + r")\d{7}$")
_NON_DIGITS_RE = re.compile(r"\D+")
# Any Unicode letter — \w minus digits/underscore.
_NAME_LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)

ALLOWED_CV_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
)
ALLOWED_CV_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".doc", ".docx"})


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    value: str | None = None
    error: str | None = None


def normalise_phone(raw: str) -> str:
    """Best-effort canonicalisation to +998XXXXXXXXX. Caller still validates."""
    s = raw.strip().replace(" ", "")
    if s.startswith("+"):
        return "+" + _NON_DIGITS_RE.sub("", s[1:])
    digits = _NON_DIGITS_RE.sub("", s)
    if digits.startswith("998"):
        return "+" + digits
    if digits.startswith("8") and len(digits) == 12:
        # e.g. 8998901234567 — uncommon but harmless to normalise
        return "+" + digits[1:]
    if digits.startswith("0") and len(digits) == 10:
        return "+998" + digits[1:]
    if len(digits) == 9:
        return "+998" + digits
    return ""


def validate_phone(raw: str) -> ValidationResult:
    normalised = normalise_phone(raw)
    if normalised and _UZ_PHONE_RE.match(normalised):
        return ValidationResult(ok=True, value=normalised)
    return ValidationResult(ok=False, error="invalid_phone")


def validate_name(raw: str) -> ValidationResult:
    cleaned = " ".join(raw.split())
    if not (2 <= len(cleaned) <= 100):
        return ValidationResult(ok=False, error="invalid_name_length")
    if not _NAME_LETTER_RE.search(cleaned):
        return ValidationResult(ok=False, error="invalid_name_letters")
    return ValidationResult(ok=True, value=cleaned)


def validate_email_address(raw: str) -> ValidationResult:
    try:
        result = validate_email(raw.strip(), check_deliverability=False)
    except EmailNotValidError:
        return ValidationResult(ok=False, error="invalid_email")
    return ValidationResult(ok=True, value=result.normalized)


def validate_cv_document(
    *,
    mime_type: str | None,
    file_name: str | None,
    size_bytes: int | None,
    max_size_bytes: int,
) -> ValidationResult:
    # Both extension and mime must be in the allowlist. Accepting either-or
    # would let a user upload e.g. cv.html with mime application/pdf, then
    # the admin's file manager opens an HTML payload thinking it's a PDF.
    ext_ok = False
    if file_name:
        lower = file_name.lower()
        ext_ok = any(lower.endswith(ext) for ext in ALLOWED_CV_EXTENSIONS)
    mime_ok = bool(mime_type) and mime_type in ALLOWED_CV_MIME_TYPES
    if not (ext_ok and mime_ok):
        return ValidationResult(ok=False, error="invalid_cv_type")
    if size_bytes is None or size_bytes <= 0 or size_bytes > max_size_bytes:
        return ValidationResult(ok=False, error="invalid_cv_size")
    return ValidationResult(ok=True)
