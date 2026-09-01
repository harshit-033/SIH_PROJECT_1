from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
from typing import Dict, Optional

from .models import AuthToken, UserCredentials, UserModel, UserRole
from .user_store import UserStore

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"

DEFAULT_SEED_USERS = {
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
    def __init__(
        self,
        user_store: Optional[UserStore] = None,
        token_ttl_seconds: int = 86400,
    ):
        self.token_ttl_seconds = token_ttl_seconds
        self.user_store = user_store if user_store is not None else UserStore()
        self._tokens: Dict[str, AuthToken] = {}

        # If user store has no users, bootstrap initial admin and seed users
        self._ensure_initial_users()

    def _ensure_initial_users(self) -> None:
        if not self.user_store.list_users():
            # Bootstrap first admin
            admin_hash = hash_password(DEFAULT_ADMIN_PASSWORD)
            self.user_store.bootstrap_admin(DEFAULT_ADMIN_USERNAME, admin_hash)

            # Create default seed users
            for username, plain_pw in DEFAULT_SEED_USERS.items():
                u_hash = hash_password(plain_pw)
                try:
                    self.user_store.create_user(username, u_hash, role=UserRole.USER)
                except ValueError:
                    pass

    def authenticate(self, credentials: UserCredentials) -> Optional[AuthToken]:
        user = self.user_store.get_user_by_username(credentials.username)
        if not user:
            logger.warning("Authentication failed: User '%s' not found", credentials.username)
            return None

        if not user.is_active:
            logger.warning("Authentication rejected: User '%s' is inactive/deactivated", credentials.username)
            return None

        if not verify_password(credentials.password, user.password_hash):
            logger.warning("Authentication failed: Invalid password for user '%s'", credentials.username)
            return None

        self.user_store.update_last_login(user.id)

        token_str = secrets.token_urlsafe(32)
        token = AuthToken(
            token=token_str,
            user_id=user.id,
            username=user.username,
            role=user.role,
            expires_at=time.time() + self.token_ttl_seconds,
        )
        self._tokens[token_str] = token
        logger.info("Authentication successful: User '%s' (Role: %s)", user.username, user.role.value)
        return token

    def validate_token(self, token_str: str) -> Optional[AuthToken]:
        token = self._tokens.get(token_str)
        if not token:
            return None

        if time.time() > token.expires_at:
            del self._tokens[token_str]
            return None

        # Verify user is still active in user_store
        user = self.user_store.get_user_by_id(token.user_id)
        if not user or not user.is_active:
            del self._tokens[token_str]
            return None

        # Sync role in case it was updated
        token.role = user.role
        return token

    def revoke_token(self, token_str: str) -> bool:
        if token_str in self._tokens:
            del self._tokens[token_str]
            return True
        return False

    def revoke_user_tokens(self, user_id: str) -> int:
        revoked = 0
        for token_str, tok in list(self._tokens.items()):
            if tok.user_id == user_id:
                del self._tokens[token_str]
                revoked += 1
        return revoked
