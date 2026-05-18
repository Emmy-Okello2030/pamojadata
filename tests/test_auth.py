import os
import sqlite3

import pytest

from src.auth import auth


def test_hash_and_verify_password():
    password = "Str0ngPass123"
    hashed = auth.hash_password(password)

    assert hashed.startswith("pbkdf2_sha256$")
    assert auth.verify_password(password, hashed)
    assert not auth.verify_password("WrongPass123", hashed)


def test_validate_password_strength():
    valid, _ = auth.validate_password_strength("StrongPass1!")
    assert valid

    invalid, message = auth.validate_password_strength("short")
    assert not invalid
    assert "at least 10 characters" in message

    invalid, message = auth.validate_password_strength("alllowercase1")
    assert not invalid
    assert "upper and lower case" in message


def test_login_and_logout_session(tmp_path, monkeypatch):
    db_file = tmp_path / "auth_test.db"
    monkeypatch.setattr(auth, "DB_PATH", str(db_file))
    monkeypatch.setenv("PAMOJADATA_ADMIN_USER", "test_admin")
    monkeypatch.setenv("PAMOJADATA_ADMIN_PASSWORD", "TestPass123")

    auth.initialise_auth_tables()
    success, result = auth.login("test_admin", "TestPass123")

    assert success
    assert isinstance(result, dict)
    assert result["username"] == "test_admin"
    assert "token" in result

    user = auth.get_user_by_session_token(result["token"])
    assert user is not None
    assert user["username"] == "test_admin"

    assert auth.logout(result["token"])
    assert auth.get_user_by_session_token(result["token"]) is None
