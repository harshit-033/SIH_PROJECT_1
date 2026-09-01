import sys
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.auth import AuthService, hash_password
from core.models import UserRole
from core.user_store import UserStore
from create_synthetic_pdfs import create_inspection_report
from server.main import app, user_store as server_user_store


def test_bootstrap_creates_first_admin():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = UserStore(storage_path=Path(tmpdir) / "users.json")
        pw_hash = hash_password("admin_pass_123")
        ok, admin_user, msg = store.bootstrap_admin("superadmin", pw_hash)
        assert ok is True
        assert admin_user is not None
        assert admin_user.username == "superadmin"
        assert admin_user.role == UserRole.ADMIN
        assert admin_user.is_active is True
        print("  - test_bootstrap_creates_first_admin: PASS")


def test_bootstrap_refuses_second_admin():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = UserStore(storage_path=Path(tmpdir) / "users.json")
        pw_hash = hash_password("admin1_pass")
        ok1, _, _ = store.bootstrap_admin("admin1", pw_hash)
        assert ok1 is True

        pw_hash2 = hash_password("admin2_pass")
        ok2, admin2, msg2 = store.bootstrap_admin("admin2", pw_hash2)
        assert ok2 is False
        assert admin2 is None
        assert "already exists" in msg2.lower()
        print("  - test_bootstrap_refuses_second_admin: PASS")


def test_rbac_matrix_flow():
    client = TestClient(app)

    # 1. Admin login success
    admin_login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert admin_login.status_code == 200
    admin_data = admin_login.json()
    assert admin_data["role"] == "admin"
    admin_token = admin_data["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("  - test_admin_login_success: PASS")

    # 2. User login success
    user_login = client.post("/api/auth/login", json={"username": "user1", "password": "pass123"})
    assert user_login.status_code == 200
    user_data = user_login.json()
    assert user_data["role"] == "user"
    user_token = user_data["token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    print("  - test_user_login_success: PASS")

    # 3. Invalid password rejected
    bad_pw = client.post("/api/auth/login", json={"username": "admin", "password": "incorrect_password"})
    assert bad_pw.status_code == 401
    print("  - test_invalid_login_rejected: PASS")

    # 4. Admin creates new user
    new_username = f"testuser_{uuid.uuid4().hex[:6]}"
    create_res = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={"username": new_username, "password": "userpass123"},
    )
    assert create_res.status_code == 200
    created_user = create_res.json()["user"]
    assert created_user["username"] == new_username
    assert created_user["role"] == "user"
    assert created_user["is_active"] is True
    created_user_id = created_user["id"]
    print("  - test_admin_can_create_user: PASS")

    # 5. User cannot create user (403)
    user_create_attempt = client.post(
        "/api/admin/users",
        headers=user_headers,
        json={"username": "unauthorized_user", "password": "pass"},
    )
    assert user_create_attempt.status_code == 403
    print("  - test_user_cannot_create_user: PASS")

    # 6. Admin can list users
    admin_list = client.get("/api/admin/users", headers=admin_headers)
    assert admin_list.status_code == 200
    list_data = admin_list.json()
    assert "users" in list_data
    assert "summary" in list_data
    assert list_data["summary"]["total_users"] >= 2
    print("  - test_admin_can_list_users: PASS")

    # 7. User cannot list users (403)
    user_list_attempt = client.get("/api/admin/users", headers=user_headers)
    assert user_list_attempt.status_code == 403
    print("  - test_user_cannot_list_users: PASS")

    # 8. User created by admin can log in
    new_user_login = client.post(
        "/api/auth/login",
        json={"username": new_username, "password": "userpass123"},
    )
    assert new_user_login.status_code == 200
    new_user_token = new_user_login.json()["token"]
    new_user_headers = {"Authorization": f"Bearer {new_user_token}"}

    # 9. User cannot remove user (403)
    user_remove_attempt = client.delete(
        f"/api/admin/users/{created_user_id}",
        headers=user_headers,
    )
    assert user_remove_attempt.status_code == 403
    print("  - test_user_cannot_remove_user: PASS")

    # 10. Admin cannot remove self (400)
    admin_profile = client.get("/api/auth/me", headers=admin_headers).json()
    admin_remove_self = client.delete(
        f"/api/admin/users/{admin_profile['id']}",
        headers=admin_headers,
    )
    assert admin_remove_self.status_code == 400
    print("  - test_admin_cannot_remove_self: PASS")

    # 11. Admin cannot remove the last active admin (400)
    # Target admin is the only admin
    admin_remove_last = client.delete(
        f"/api/admin/users/{admin_profile['id']}",
        headers=admin_headers,
    )
    assert admin_remove_last.status_code == 400
    print("  - test_last_admin_cannot_be_removed: PASS")

    # 12. Admin can remove user
    admin_remove_res = client.delete(
        f"/api/admin/users/{created_user_id}",
        headers=admin_headers,
    )
    assert admin_remove_res.status_code == 200
    print("  - test_admin_can_remove_user: PASS")

    # 13. Removed user cannot log in
    removed_login = client.post(
        "/api/auth/login",
        json={"username": new_username, "password": "userpass123"},
    )
    assert removed_login.status_code == 401
    print("  - test_removed_user_cannot_login: PASS")

    # 14. Inactive user rejected
    # Create another user and manually deactivate in store
    inactive_uname = f"inactive_{uuid.uuid4().hex[:6]}"
    temp_u = server_user_store.create_user(inactive_uname, hash_password("pass123"))
    server_user_store.deactivate_user(temp_u.id)
    inactive_login = client.post(
        "/api/auth/login",
        json={"username": inactive_uname, "password": "pass123"},
    )
    assert inactive_login.status_code == 401
    print("  - test_inactive_user_rejected: PASS")

    # 15. Unauthenticated AI request rejected (401)
    unauth_chat = client.post("/api/chat", json={"message": "hello", "stream": False})
    assert unauth_chat.status_code == 401
    print("  - test_unauthenticated_ai_request_rejected: PASS")

    # 16. Admin can use AI
    with patch("core.ai_service.ollama.chat") as mock_chat:
        mock_chat.return_value = {"message": {"content": "Admin response"}}
        admin_ai = client.post("/api/chat", headers=admin_headers, json={"message": "Hi", "stream": False})
        assert admin_ai.status_code == 200
        assert "Admin response" in admin_ai.json()["content"]
    print("  - test_admin_can_use_ai: PASS")

    # 17. User can use AI
    with patch("core.ai_service.ollama.chat") as mock_chat:
        mock_chat.return_value = {"message": {"content": "User response"}}
        user_ai = client.post("/api/chat", headers=user_headers, json={"message": "Hi", "stream": False})
        assert user_ai.status_code == 200
        assert "User response" in user_ai.json()["content"]
    print("  - test_user_can_use_ai: PASS")

    # 18. User cannot access other user's data
    # Admin uploads doc
    pdf_path = create_inspection_report()
    with open(pdf_path, "rb") as f:
        up_res = client.post("/api/documents", headers=admin_headers, files={"file": ("admin_doc.pdf", f, "application/pdf")})
    assert up_res.status_code == 200
    admin_doc_id = up_res.json()["document"]["document_id"]

    # User attempts to query admin's doc -> 403 Forbidden
    user_access_attempt = client.post(
        f"/api/documents/{admin_doc_id}/chat",
        headers=user_headers,
        json={"message": "What is in admin doc?", "stream": False},
    )
    assert user_access_attempt.status_code == 403
    print("  - test_user_cannot_access_other_user_data: PASS")


def main():
    print("Running Admin + User RBAC Test Suite:")
    test_bootstrap_creates_first_admin()
    test_bootstrap_refuses_second_admin()
    test_rbac_matrix_flow()
    print("All RBAC and User Management tests PASSED successfully!")


if __name__ == "__main__":
    main()
