from __future__ import annotations

import hashlib
import hmac
import logging
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
        if not any(u.role == UserRole.ADMIN for u in self.user_store.list_users()):
            admin_hash = hash_password(DEFAULT_ADMIN_PASSWORD)
            self.user_store.bootstrap_admin(DEFAULT_ADMIN_USERNAME, admin_hash)

        for username, plain_pw in DEFAULT_SEED_USERS.items():
            if not self.user_store.get_user_by_username(username):
                u_hash = hash_password(plain_pw)
                try:
                    self.user_store.create_user(username, u_hash, role=UserRole.USER)
                except ValueError:
                    pass

    def authenticate(self, credentials: UserCredentials) -> Optional[AuthToken]:
        """
        Authenticate a user. For admin accounts, enforces single-active-session:
        if an existing valid session token is recorded for the admin, rejects
        the new login with a clear message. Uses the same RLock for atomicity.
        """
        user = self.user_store.get_user_by_username(credentials.username)
        if not user:
            logger.warning("Authentication failed: User '%s' not found", credentials.username)
            return None

        if not user.is_active:
            logger.warning("Authentication rejected: User '%s' is inactive", credentials.username)
            return None

        if not verify_password(credentials.password, user.password_hash):
            logger.warning("Authentication failed: Invalid password for user '%s'", credentials.username)
            return None

        # ----------------------------------------------------------------
        # Single-active-session enforcement for admin accounts
        # ----------------------------------------------------------------
        if user.role == UserRole.ADMIN:
            stored_token = self.user_store.get_admin_active_session_token(user.id)
            if stored_token is not None:
                # Validate whether the stored token is still live
                existing_auth_token = self._tokens.get(stored_token)
                if existing_auth_token and time.time() <= existing_auth_token.expires_at:
                    # Live session exists — reject this new login
                    logger.warning(
                        "Admin single-session: login rejected for '%s'; active session already exists.",
                        user.username,
                    )
                    return "ADMIN_ALREADY_ACTIVE"  # sentinel; caller must handle
                else:
                    # Stored session has expired or was evicted — clean up
                    if stored_token in self._tokens:
                        del self._tokens[stored_token]
                    self.user_store.clear_active_session(user.id, stored_token)

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

        # Record the active session for admin accounts
        if user.role == UserRole.ADMIN:
            self.user_store.set_active_session(user.id, token_str)

        logger.info("Authentication successful: User '%s' (Role: %s)", user.username, user.role.value)
        return token

    def validate_token(self, token_str: str) -> Optional[AuthToken]:
        token = self._tokens.get(token_str)
        if not token:
            return None

        if time.time() > token.expires_at:
            # Expired — clean up
            del self._tokens[token_str]
            user = self.user_store.get_user_by_id(token.user_id)
            if user and user.role == UserRole.ADMIN:
                self.user_store.clear_active_session(user.id, token_str)
            return None

        # Verify user is still active in user_store
        user = self.user_store.get_user_by_id(token.user_id)
        if not user or not user.is_active:
            del self._tokens[token_str]
            if user and user.role == UserRole.ADMIN:
                self.user_store.clear_active_session(user.id, token_str)
            return None

        # Sync username & role in case they were updated (profile change)
        token.username = user.username
        token.role = user.role
        return token

    def revoke_token(self, token_str: str) -> bool:
        token = self._tokens.pop(token_str, None)
        if token:
            user = self.user_store.get_user_by_id(token.user_id)
            if user and user.role == UserRole.ADMIN:
                self.user_store.clear_active_session(user.id, token_str)
            return True
        return False

    def revoke_user_tokens(self, user_id: str) -> int:
        """Revoke all tokens for a user, clearing admin session if applicable."""
        revoked = 0
        user = self.user_store.get_user_by_id(user_id)
        for token_str, tok in list(self._tokens.items()):
            if tok.user_id == user_id:
                del self._tokens[token_str]
                revoked += 1
        if user and user.role == UserRole.ADMIN and user.active_session_token:
            self.user_store.clear_active_session(user_id, user.active_session_token)
        return revoked
