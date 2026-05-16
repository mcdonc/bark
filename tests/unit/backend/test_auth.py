"""Tests for auth module: password hashing, JWT tokens, login/register."""

import pytest
from fastapi import HTTPException

from backend import auth, user_store


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = auth._hash_password("mypassword")
        assert auth._verify_password("mypassword", hashed)

    def test_wrong_password_fails(self):
        hashed = auth._hash_password("mypassword")
        assert not auth._verify_password("wrongpassword", hashed)

    def test_different_hashes_for_same_password(self):
        h1 = auth._hash_password("same")
        h2 = auth._hash_password("same")
        assert h1 != h2  # bcrypt uses random salt


class TestJWT:
    def test_create_and_decode_token(self):
        token = auth._create_token("user-123", "alice")
        payload = auth._decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["username"] == "alice"
        assert "jti" in payload
        assert "exp" in payload

    def test_invalid_token_raises(self):
        from jose import JWTError
        with pytest.raises(JWTError):
            auth._decode_token("garbage.token.value")


class TestRegister:
    async def test_register_success(self, db):
        result = await auth.register(auth.RegisterRequest(username="newuser", password="pass1234"))
        assert result.access_token
        assert result.token_type == "bearer"

    async def test_register_duplicate_username(self, db):
        await auth.register(auth.RegisterRequest(username="dupuser", password="pass1234"))
        with pytest.raises(HTTPException) as exc_info:
            await auth.register(auth.RegisterRequest(username="dupuser", password="pass5678"))
        assert exc_info.value.status_code == 400

    async def test_register_short_username(self, db):
        with pytest.raises(HTTPException) as exc_info:
            await auth.register(auth.RegisterRequest(username="ab", password="pass1234"))
        assert exc_info.value.status_code == 400

    async def test_register_short_password(self, db):
        with pytest.raises(HTTPException) as exc_info:
            await auth.register(auth.RegisterRequest(username="validuser", password="abc"))
        assert exc_info.value.status_code == 400


class TestLogin:
    async def test_login_success(self, user):
        result = await auth.login(auth.LoginRequest(username="testuser", password="testpass"))
        assert result.access_token
        assert result.token_type == "bearer"

    async def test_login_wrong_password(self, user):
        with pytest.raises(HTTPException) as exc_info:
            await auth.login(auth.LoginRequest(username="testuser", password="wrong"))
        assert exc_info.value.status_code == 401

    async def test_login_nonexistent_user(self, db):
        with pytest.raises(HTTPException) as exc_info:
            await auth.login(auth.LoginRequest(username="noone", password="pass"))
        assert exc_info.value.status_code == 401


class TestTokenValidation:
    async def test_get_user_from_valid_token(self, user):
        token = auth._create_token(user["id"], user["username"])
        result = await auth.get_user_from_token(token)
        assert result is not None
        assert result["id"] == user["id"]

    async def test_get_user_from_invalid_token(self, db):
        result = await auth.get_user_from_token("invalid.token.here")
        assert result is None

    async def test_blocklisted_token_rejected(self, user):
        token = auth._create_token(user["id"], user["username"])
        # Token should work before blocklisting
        assert await auth.get_user_from_token(token) is not None
        # Blocklist it
        await auth.logout(token)
        # Now it should fail
        assert await auth.get_user_from_token(token) is None
