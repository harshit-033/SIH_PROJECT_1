from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from typing import Dict, Optional

from .models import AuthToken, UserCredentials

DEFAULT_USERS = {
    "admin": "admin123",
    "user1": "pass123",
    "user2": "pass123",
    "inspector": "sih2026",
}


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}:{key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return hmac.compare_digest(key, expected_key)
    except Exception:
        return False


class AuthService:
    def __init__(self, token_ttl_seconds: int = 86400):
        self.token_ttl_seconds = token_ttl_seconds
        self._user_db: Dict[str, str] = {}
        self._tokens: Dict[str, AuthToken] = {}
        
        # Initialize default users with hashed passwords
        for username, plain_pw in DEFAULT_USERS.items():
            self._user_db[username] = hash_password(plain_pw)

    def register_user(self, username: str, password: str) -> bool:
        if username in self._user_db:
            return False
        self._user_db[username] = hash_password(password)
        return True

    def authenticate(self, credentials: UserCredentials) -> Optional[AuthToken]:
        stored_hash = self._user_db.get(credentials.username)
        if not stored_hash or not verify_password(credentials.password, stored_hash):
            return None

        token_str = secrets.token_urlsafe(32)
        token = AuthToken(
            token=token_str,
            user_id=f"usr_{credentials.username}",
            username=credentials.username,
            expires_at=time.time() + self.token_ttl_seconds,
        )
        self._tokens[token_str] = token
        return token

    def validate_token(self, token_str: str) -> Optional[AuthToken]:
        token = self._tokens.get(token_str)
        if not token:
            return None
        if time.time() > token.expires_at:
            del self._tokens[token_str]
            return None
        return token

    def revoke_token(self, token_str: str) -> bool:
        if token_str in self._tokens:
            del self._tokens[token_str]
            return True
        return False
