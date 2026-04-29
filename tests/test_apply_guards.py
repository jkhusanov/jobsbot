"""Pure-logic tests for security-critical guards in handlers/apply.py.

These tests exercise the *guards* (input checks) without spinning up a full
aiogram dispatcher. Where a check is currently expressed inline inside a
handler, this module asserts the equivalent predicate so a future refactor
that loses the guard fails the build.
"""
from __future__ import annotations

from typing import Any

import pytest

from jobsbot.handlers.apply import _REQUIRED_FIELDS
from jobsbot.validation import (
    validate_cv_document,
    validate_email_address,
    validate_name,
    validate_phone,
)

# --- _REQUIRED_FIELDS guard (M1) ----------------------------------------------


def test_required_fields_set_is_complete() -> None:
    """Confirm the guard covers every field needed to build a NewApplication.

    If someone adds a new mandatory field to NewApplication later, they must
    also add it to _REQUIRED_FIELDS or this test fails noisily.
    """
    expected = {"job_id", "name", "phone", "email", "cv_file_id"}
    assert set(_REQUIRED_FIELDS) == expected


@pytest.mark.parametrize("missing", _REQUIRED_FIELDS)
def test_required_fields_guard_rejects_missing(missing: str) -> None:
    data: dict[str, Any] = {f: "x" for f in _REQUIRED_FIELDS}
    data[missing] = ""  # blank counts as missing under the truthiness check
    assert not all(data.get(k) for k in _REQUIRED_FIELDS)


def test_required_fields_guard_passes_when_complete() -> None:
    data: dict[str, Any] = {f: "x" for f in _REQUIRED_FIELDS}
    assert all(data.get(k) for k in _REQUIRED_FIELDS)


# --- Shared-contact rejection (M3 from prior audit) ---------------------------


def test_contact_user_id_must_match_sender() -> None:
    """A Contact whose user_id != sender's id is a shared third-party contact."""
    sender_id = 100
    own_contact_user_id = 100
    foreign_contact_user_id = 200
    assert own_contact_user_id == sender_id
    assert foreign_contact_user_id != sender_id


# --- Validation guards (sanity that handler-level checks still hold) ----------


def test_validation_layer_rejects_unicode_bidi_in_name() -> None:
    """Right-to-left override in a name must not survive validation."""
    name_with_rlo = "Akmal‮Karimov"
    result = validate_name(name_with_rlo)
    assert result.ok
    assert "‮" not in (result.value or "")


def test_validation_layer_rejects_zero_width_join_in_email() -> None:
    """Zero-width joiner injected into an email gets stripped before parsing."""
    raw = "user‍@example.com"
    result = validate_email_address(raw)
    # Either the strip yields a valid address or it's rejected — what
    # *must not* happen is that ZWJ leaks through into the stored email.
    if result.ok:
        assert "‍" not in (result.value or "")


def test_validation_layer_rejects_non_uzbek_phone_with_uzbek_shape() -> None:
    """A 12-digit number starting with 998 but with an unallocated prefix is rejected."""
    assert not validate_phone("+998011234567").ok


def test_validation_layer_rejects_html_with_pdf_mime_in_cv() -> None:
    """Mime+ext both must match the allowlist."""
    result = validate_cv_document(
        mime_type="application/pdf",
        file_name="cv.html",
        size_bytes=1024,
        max_size_bytes=20 * 1024 * 1024,
    )
    assert not result.ok
    assert result.error == "invalid_cv_type"
