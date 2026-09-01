from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from .models import UserModel, UserRole

logger = logging.getLogger(__name__)


class UserStore:
    def __init__(self, storage_path: str | Path = "data/users.json"):
        self.storage_path = Path(storage_path).resolve()
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._users: Dict[str, UserModel] = {}  # keyed by user_id
        self._load()

    def _load(self) -> None:
        with self._lock:
            if not self.storage_path.exists():
                self._users = {}
                return

            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                users_map = {}
                for item in data.get("users", []):
                    role_val = item.get("role", "user")
                    role = UserRole.ADMIN if role_val == "admin" else UserRole.USER
                    user = UserModel(
                        id=item["id"],
                        username=item["username"],
                        password_hash=item["password_hash"],
                        role=role,
                        is_active=item.get("is_active", True),
                        created_at=item.get("created_at", time.time()),
                        last_login=item.get("last_login"),
                        active_session_token=item.get("active_session_token"),
                    )
                    users_map[user.id] = user
                self._users = users_map
                logger.info("Loaded %d users from %s", len(self._users), self.storage_path)
            except Exception as exc:
                logger.error("Failed to load users from %s: %s", self.storage_path, exc)
                self._users = {}

    def _save(self) -> None:
        with self._lock:
            temp_path = self.storage_path.with_suffix(".tmp")
            data = {
                "users": [
                    {
                        "id": u.id,
                        "username": u.username,
                        "password_hash": u.password_hash,
                        "role": u.role.value if isinstance(u.role, UserRole) else str(u.role),
                        "is_active": u.is_active,
                        "created_at": u.created_at,
                        "last_login": u.last_login,
                        "active_session_token": u.active_session_token,
                    }
                    for u in self._users.values()
                ]
            }
            temp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            try:
                temp_path.replace(self.storage_path)
            except PermissionError:
                if self.storage_path.exists():
                    self.storage_path.unlink(missing_ok=True)
                temp_path.replace(self.storage_path)

    def bootstrap_admin(self, username: str, password_hash: str) -> tuple[bool, Optional[UserModel], str]:
        with self._lock:
            if any(u.role == UserRole.ADMIN and u.is_active for u in self._users.values()):
                return False, None, "An active admin account already exists. Bootstrap refused."

            existing = self.get_user_by_username(username)
            if existing:
                existing.role = UserRole.ADMIN
                existing.password_hash = password_hash
                existing.is_active = True
                self._save()
                return True, existing, "Existing user promoted to admin."

            user_id = f"usr_{uuid.uuid4().hex[:12]}"
            admin_user = UserModel(
                id=user_id,
                username=username,
                password_hash=password_hash,
                role=UserRole.ADMIN,
                is_active=True,
                created_at=time.time(),
            )
            self._users[user_id] = admin_user
            self._save()
            logger.info("Created first bootstrap admin: %s (ID: %s)", username, user_id)
            return True, admin_user, "First admin created successfully."

    def get_user_by_username(self, username: str) -> Optional[UserModel]:
        with self._lock:
            clean = username.strip().lower()
            for user in self._users.values():
                if user.username.strip().lower() == clean:
                    return user
            return None

    def get_user_by_id(self, user_id: str) -> Optional[UserModel]:
        with self._lock:
            return self._users.get(user_id)

    def list_users(self) -> List[UserModel]:
        with self._lock:
            return sorted(
                list(self._users.values()),
                key=lambda u: (u.created_at, u.username.lower()),
            )

    def create_user(
        self, username: str, password_hash: str, role: UserRole = UserRole.USER
    ) -> UserModel:
        with self._lock:
            clean_username = username.strip()
            if not clean_username:
                raise ValueError("Username cannot be empty.")
            if self.get_user_by_username(clean_username):
                raise ValueError(f"Username '{clean_username}' already exists.")

            user_id = f"usr_{uuid.uuid4().hex[:12]}"
            user = UserModel(
                id=user_id,
                username=clean_username,
                password_hash=password_hash,
                role=role,
                is_active=True,
                created_at=time.time(),
            )
            self._users[user_id] = user
            self._save()
            logger.info("Created user %s with role %s (ID: %s)", clean_username, role.value, user_id)
            return user

    def update_username(self, user_id: str, new_username: str) -> UserModel:
        """Change a user's username. Validates uniqueness. Raises ValueError on conflict."""
        with self._lock:
            user = self.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found.")

            clean = new_username.strip()
            if not clean:
                raise ValueError("Username cannot be empty.")
            if len(clean) > 50:
                raise ValueError("Username too long (max 50 characters).")

            existing = self.get_user_by_username(clean)
            if existing and existing.id != user_id:
                raise ValueError(f"Username '{clean}' is already taken.")

            old_username = user.username
            user.username = clean
            self._save()
            logger.info("Updated username for user ID %s: '%s' -> '%s'", user_id, old_username, clean)
            return user

    def update_password_hash(self, user_id: str, new_password_hash: str) -> UserModel:
        """Replace the stored password hash. Caller must pre-verify old password."""
        with self._lock:
            user = self.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found.")
            user.password_hash = new_password_hash
            self._save()
            logger.info("Password hash updated for user ID %s", user_id)
            return user

    # -----------------------------------------------------------------
    # Single Active Admin Session helpers
    # -----------------------------------------------------------------
    def set_active_session(self, user_id: str, token: str) -> None:
        """Record the single active session token for an admin user."""
        with self._lock:
            user = self.get_user_by_id(user_id)
            if user:
                user.active_session_token = token
                self._save()

    def clear_active_session(self, user_id: str, token: str) -> None:
        """Clear the active session token — only if it matches the supplied token."""
        with self._lock:
            user = self.get_user_by_id(user_id)
            if user and user.active_session_token == token:
                user.active_session_token = None
                self._save()

    def get_admin_active_session_token(self, user_id: str) -> Optional[str]:
        """Return the stored active session token for a user, or None."""
        with self._lock:
            user = self.get_user_by_id(user_id)
            return user.active_session_token if user else None

    def remove_user(self, user_id: str) -> bool:
        with self._lock:
            user = self.get_user_by_id(user_id)
            if not user:
                return False

            if user.role == UserRole.ADMIN and self.count_active_admins() <= 1:
                raise ValueError("Cannot remove the last remaining active admin.")

            del self._users[user_id]
            self._save()
            logger.info("Removed user %s (ID: %s)", user.username, user_id)
            return True

    def deactivate_user(self, user_id: str) -> bool:
        with self._lock:
            user = self.get_user_by_id(user_id)
            if not user:
                return False

            if user.role == UserRole.ADMIN and self.count_active_admins() <= 1:
                raise ValueError("Cannot deactivate the last remaining active admin.")

            user.is_active = False
            self._save()
            logger.info("Deactivated user %s (ID: %s)", user.username, user_id)
            return True

    def count_active_admins(self) -> int:
        with self._lock:
            return sum(1 for u in self._users.values() if u.role == UserRole.ADMIN and u.is_active)

    def update_last_login(self, user_id: str) -> None:
        with self._lock:
            user = self.get_user_by_id(user_id)
            if user:
                user.last_login = time.time()
                self._save()
