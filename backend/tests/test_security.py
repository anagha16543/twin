"""
tests/test_security.py

Tests for core security functions:
- Password hashing and verification (bcrypt)
- JWT access token generation, expiration, and signature validation (PyJWT)
"""

from __future__ import annotations

from datetime import timedelta
import pytest
import jwt

from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


class TestPasswordHashing:
    """Tests for bcrypt password hashing and verification."""

    def test_hash_creates_non_empty_string(self) -> None:
        raw = "SecurePassword123!"
        hashed = get_password_hash(raw)
        assert isinstance(hashed, str)
        assert len(hashed) > 20
        assert hashed != raw

    def test_verify_password_success(self) -> None:
        raw = "CorrectPassword123!"
        hashed = get_password_hash(raw)
        assert verify_password(raw, hashed) is True

    def test_verify_password_failure(self) -> None:
        raw = "CorrectPassword123!"
        hashed = get_password_hash(raw)
        assert verify_password("WrongPassword!", hashed) is False

    def test_verify_password_empty_values(self) -> None:
        assert verify_password("", "somehash") is False
        assert verify_password("password", "") is False
        assert verify_password("", "") is False

    def test_password_hashes_are_salted_uniquely(self) -> None:
        raw = "SamePassword123!"
        hash1 = get_password_hash(raw)
        hash2 = get_password_hash(raw)
        assert hash1 != hash2
        assert verify_password(raw, hash1) is True
        assert verify_password(raw, hash2) is True


class TestJWTTokens:
    """Tests for JWT access token encoding and decoding."""

    def test_create_and_decode_valid_token(self) -> None:
        subject = "user-12345"
        roles = ["HOD", "FACULTY"]
        token = create_access_token(subject=subject, roles=roles)

        payload = decode_access_token(token)
        assert payload["sub"] == subject
        assert payload["roles"] == roles
        assert "exp" in payload
        assert "iat" in payload

    def test_expired_token_raises_error(self) -> None:
        subject = "user-12345"
        roles = ["FACULTY"]
        # Expired 10 seconds ago
        token = create_access_token(
            subject=subject,
            roles=roles,
            expires_delta=timedelta(seconds=-10),
        )

        with pytest.raises(jwt.ExpiredSignatureError):
            decode_access_token(token)

    def test_tampered_token_raises_error(self) -> None:
        token = create_access_token(subject="user-12345", roles=["FACULTY"])
        tampered_token = token[:-5] + "XXXXX"

        with pytest.raises(jwt.PyJWTError):
            decode_access_token(tampered_token)

    def test_token_with_extra_claims(self) -> None:
        token = create_access_token(
            subject="user-12345",
            roles=["ADMIN"],
            extra_claims={"dept": "CSE"},
        )
        payload = decode_access_token(token)
        assert payload["dept"] == "CSE"
