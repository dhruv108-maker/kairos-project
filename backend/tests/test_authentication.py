from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.core.security import (
    TokenError,
    create_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_password_hash_and_verification():
    password = "correct horse battery staple 92"
    encoded = hash_password(password)
    assert encoded != password
    assert verify_password(password, encoded)
    assert not verify_password("not the password", encoded)


def test_password_hash_is_salted():
    password = "correct horse battery staple 92"
    assert hash_password(password) != hash_password(password)


def test_access_token_has_expected_purpose():
    token = create_token("account-123", "access", timedelta(minutes=5))
    claims = decode_token(token, "access")
    assert claims["sub"] == "account-123"
    with pytest.raises(TokenError):
        decode_token(token, "email_verification")


def test_expired_token_is_rejected():
    token = create_token("account-123", "access", timedelta(seconds=-1))
    with pytest.raises(TokenError):
        decode_token(token, "access")


def test_token_hash_is_one_way_and_deterministic():
    token = "secret-verification-token"
    assert hash_token(token) == hash_token(token)
    assert hash_token(token) != token


def test_login_request_does_not_allow_short_password():
    from pydantic import ValidationError
    from app.api.schemas import LoginRequest

    with pytest.raises(ValidationError):
        LoginRequest(email="user@example.com", password="")


def test_registration_normalizes_email_and_rejects_short_password():
    from pydantic import ValidationError
    from app.api.schemas import StudentRegistration

    valid = StudentRegistration(
        email="  STUDENT@Example.com ",
        password="long enough password 123",
        full_name="Student One",
        enrollment_number="ENR-001",
        cohort_id="cohort-1",
    )
    assert valid.email == "student@example.com"
    with pytest.raises(ValidationError):
        StudentRegistration(
            email="student@example.com",
            password="short",
            full_name="Student One",
            enrollment_number="ENR-001",
            cohort_id="cohort-1",
        )
