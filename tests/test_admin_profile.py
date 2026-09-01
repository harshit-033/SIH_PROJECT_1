import concurrent.futures
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.auth import AuthService, hash_password
from core.models import UserCredentials, UserRole
from core.user_store import UserStore
from server.main import app, auth_service, user_store


def get_auth_token(client: TestClient, username: str, password: str) -> str:
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return res.json()["token"]


def test_admin_changes_username_valid():
    """1. Admin changes username with valid input -> PASS"""
    client = TestClient(app)
    # Login as admin
    token = get_auth_token(client, "admin", "admin123")
    res = client.patch(
        "/api/admin/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "superadmin"},
    )
    assert res.status_code == 200
    assert res.json()["user"]["username"] == "superadmin"

    # Verify /api/auth/me reflects new username
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "superadmin"
    assert me_res.json()["role"] == "admin"

    # Reset back to admin
    client.patch(
        "/api/admin/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "admin"},
    )
    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    print("  - test_admin_changes_username_valid: PASS")


def test_admin_changes_username_duplicate():
    """2. Admin changes username to duplicate -> REJECT (409)"""
    client = TestClient(app)
    token = get_auth_token(client, "admin", "admin123")
    res = client.patch(
        "/api/admin/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "user1"},  # Already exists
    )
    assert res.status_code == 409
    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    print("  - test_admin_changes_username_duplicate: PASS")


def test_admin_changes_username_invalid():
    """3. Admin changes username to invalid value -> REJECT (400)"""
    client = TestClient(app)
    token = get_auth_token(client, "admin", "admin123")
    res = client.patch(
        "/api/admin/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "   "},  # Empty / whitespace
    )
    assert res.status_code in (400, 422)
    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    print("  - test_admin_changes_username_invalid: PASS")


def test_user_calls_admin_username_endpoint():
    """4. User calls admin username endpoint -> 403"""
    client = TestClient(app)
    user_token = get_auth_token(client, "user1", "pass123")
    res = client.patch(
        "/api/admin/me",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"username": "new_user1_name"},
    )
    assert res.status_code == 403
    print("  - test_user_calls_admin_username_endpoint: PASS")


def test_admin_changes_password_correct_and_flow():
    """5, 6, 7, 8, 9, 10: Password change lifecycle and validation"""
    client = TestClient(app)
    token = get_auth_token(client, "admin", "admin123")

    # 6. Wrong old password -> REJECT (400)
    res = client.post(
        "/api/admin/me/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "wrongpassword",
            "new_password": "new_admin_pass_456",
            "confirm_password": "new_admin_pass_456",
        },
    )
    assert res.status_code == 400

    # 7. Mismatched confirmation -> REJECT (400)
    res = client.post(
        "/api/admin/me/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "admin123",
            "new_password": "new_admin_pass_456",
            "confirm_password": "different_pass",
        },
    )
    assert res.status_code == 400

    # 8. Invalid password (<4 chars) -> REJECT (400)
    res = client.post(
        "/api/admin/me/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "admin123",
            "new_password": "12",
            "confirm_password": "12",
        },
    )
    assert res.status_code in (400, 422)

    # 5. Correct old password -> PASS
    res = client.post(
        "/api/admin/me/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "admin123",
            "new_password": "new_admin_pass_456",
            "confirm_password": "new_admin_pass_456",
        },
    )
    assert res.status_code == 200

    # Logout active session
    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

    # 9. Old password after successful change -> REJECT (401)
    res_old = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res_old.status_code == 401

    # 10. New password after successful change -> PASS
    new_token = get_auth_token(client, "admin", "new_admin_pass_456")
    assert new_token is not None

    # Revert password back to admin123 for other tests
    client.post(
        "/api/admin/me/change-password",
        headers={"Authorization": f"Bearer {new_token}"},
        json={
            "current_password": "new_admin_pass_456",
            "new_password": "admin123",
            "confirm_password": "admin123",
        },
    )
    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {new_token}"})
    print("  - test_admin_changes_password_lifecycle: PASS")


def test_single_active_admin_session():
    """11, 12, 13, 14: System A login, System B reject, System A logout, System B login"""
    client_a = TestClient(app)
    client_b = TestClient(app)

    # 11. Admin login on System A -> PASS
    res_a = client_a.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res_a.status_code == 200
    token_a = res_a.json()["token"]

    # 12. Same admin login on System B while A active -> REJECT (409)
    res_b = client_b.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res_b.status_code == 409
    assert "already logged in" in res_b.json()["detail"].lower()

    # 13. Admin logout on System A -> PASS
    res_logout_a = client_a.post("/api/auth/logout", headers={"Authorization": f"Bearer {token_a}"})
    assert res_logout_a.status_code == 200

    # 14. Same admin login on System B after A logout -> PASS
    res_b2 = client_b.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res_b2.status_code == 200
    token_b = res_b2.json()["token"]

    # Clean up System B session
    client_b.post("/api/auth/logout", headers={"Authorization": f"Bearer {token_b}"})
    print("  - test_single_active_admin_session: PASS")


def test_admin_session_expiration_recovery():
    """15. Admin session expires -> New login allowed"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = UserStore(storage_path=Path(tmpdir) / "users.json")
        auth = AuthService(user_store=store, token_ttl_seconds=1)  # 1 second TTL

        # Login admin
        token1 = auth.authenticate(UserCredentials(username="admin", password="admin123"))
        assert hasattr(token1, "token")

        # Immediate second login -> Sentinel ADMIN_ALREADY_ACTIVE
        token2 = auth.authenticate(UserCredentials(username="admin", password="admin123"))
        assert token2 == "ADMIN_ALREADY_ACTIVE"

        # Wait for token to expire
        time.sleep(1.2)

        # Login after expiration -> PASS
        token3 = auth.authenticate(UserCredentials(username="admin", password="admin123"))
        assert hasattr(token3, "token")
        print("  - test_admin_session_expiration_recovery: PASS")


def test_user_login_multiple_clients():
    """16. Normal users can login on multiple clients simultaneously (UNCHANGED)"""
    client_1 = TestClient(app)
    client_2 = TestClient(app)

    res_1 = client_1.post("/api/auth/login", json={"username": "user1", "password": "pass123"})
    assert res_1.status_code == 200

    res_2 = client_2.post("/api/auth/login", json={"username": "user1", "password": "pass123"})
    assert res_2.status_code == 200  # Normal users NOT blocked by single-session rule
    print("  - test_user_login_multiple_clients: PASS")


def test_admin_ai_and_dashboard_access():
    """17, 18, 19, 20: Admin can use AI, Dashboard, User Management, but normal users cannot access admin profile APIs"""
    client = TestClient(app)
    admin_token = get_auth_token(client, "admin", "admin123")

    # 17. Admin can access chat/AI endpoint
    with patch("core.ai_service.AIService.generate_chat_stream") as mock_stream:
        mock_stream.return_value = iter(["Hello admin!"])
        chat_res = client.post(
            "/api/chat",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"message": "Hi AI", "stream": False},
        )
        assert chat_res.status_code == 200

    # 18. Admin dashboard / user list works
    users_res = client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert users_res.status_code == 200
    assert "users" in users_res.json()

    # 19. Admin can create a new user
    create_res = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"username": "temp_test_user", "password": "testpassword123"},
    )
    assert create_res.status_code == 200
    created_id = create_res.json()["user"]["id"]

    # Clean up created user
    client.delete(f"/api/admin/users/{created_id}", headers={"Authorization": f"Bearer {admin_token}"})

    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {admin_token}"})

    # 20. Normal user cannot access My Account admin APIs (password change)
    user_token = get_auth_token(client, "user2", "pass123")
    forbidden_res = client.post(
        "/api/admin/me/change-password",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "current_password": "pass123",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
    )
    assert forbidden_res.status_code == 403
    print("  - test_admin_ai_and_dashboard_access: PASS")


def test_concurrent_admin_login_race_condition():
    """21. Concurrency / Race condition: 5 simultaneous logins yield exactly 1 valid session"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = UserStore(storage_path=Path(tmpdir) / "users.json")
        auth = AuthService(user_store=store)

        results = []

        def attempt_login():
            return auth.authenticate(UserCredentials(username="admin", password="admin123"))

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(attempt_login) for _ in range(5)]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        # Count successful token creations vs rejected logins
        successful_tokens = [r for r in results if hasattr(r, "token")]
        conflicts = [r for r in results if r == "ADMIN_ALREADY_ACTIVE"]

        assert len(successful_tokens) == 1, f"Expected exactly 1 successful login, got {len(successful_tokens)}"
        assert len(conflicts) == 4, f"Expected 4 conflicts, got {len(conflicts)}"
        print("  - test_concurrent_admin_login_race_condition: PASS")


if __name__ == "__main__":
    print("\n--- Running Admin Profile & Single Active Admin Session Test Suite ---")
    test_admin_changes_username_valid()
    test_admin_changes_username_duplicate()
    test_admin_changes_username_invalid()
    test_user_calls_admin_username_endpoint()
    test_admin_changes_password_correct_and_flow()
    test_single_active_admin_session()
    test_admin_session_expiration_recovery()
    test_user_login_multiple_clients()
    test_admin_ai_and_dashboard_access()
    test_concurrent_admin_login_race_condition()
    print("\n=== ALL ADMIN PROFILE & SINGLE SESSION TESTS PASSED! ===")
