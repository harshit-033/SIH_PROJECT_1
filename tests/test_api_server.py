import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from create_synthetic_pdfs import create_inspection_report, create_scanned_inspection_report
from server.main import app


def test_api_server_flow():
    client = TestClient(app)

    # 1. Health check
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    health_data = res.json()
    assert "status" in health_data
    assert "metrics" in health_data
    assert "queue" in health_data

    # 2. Login with bad credentials
    bad_login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrongpassword"},
    )
    assert bad_login.status_code == 401

    # 3. Login with valid credentials
    login_res = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_res.status_code == 200
    auth_data = login_res.json()
    assert "token" in auth_data
    token = auth_data["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 4. Session info check
    session_res = client.get("/api/session", headers=headers)
    assert session_res.status_code == 200
    sess_data = session_res.json()
    assert sess_data["username"] == "admin"
    assert sess_data["mode"] == "General Chat"

    # 5. General Chat Non-Streaming (mocked AI response for fast unit testing)
    with patch("core.ai_service.ollama.chat") as mock_chat:
        mock_chat.return_value = {"message": {"content": "I am a local AI assistant."}}
        chat_res = client.post(
            "/api/chat",
            headers=headers,
            json={"message": "Hello AI", "stream": False},
        )
        assert chat_res.status_code == 200
        assert "I am a local AI assistant." in chat_res.json()["content"]

    # 6. Upload Native PDF
    native_pdf_path = create_inspection_report()
    with open(native_pdf_path, "rb") as f:
        upload_res = client.post(
            "/api/documents",
            headers=headers,
            files={"file": ("synthetic_inspection_report.pdf", f, "application/pdf")},
        )
    assert upload_res.status_code == 200
    up_data = upload_res.json()
    assert up_data["mode"] == "Document Analysis"
    assert "native" in up_data["document"]["method_summary"]
    doc_id = up_data["document"]["document_id"]

    # 7. List Documents
    docs_list = client.get("/api/documents", headers=headers)
    assert docs_list.status_code == 200
    assert len(docs_list.json()["documents"]) == 1

    # 8. Document QA Non-Streaming (mocked)
    with patch("core.ai_service.ollama.chat") as mock_chat:
        mock_chat.return_value = {
            "message": {"content": "The equipment ID is PUMP-A17 on [Page 1 | native]."}
        }
        doc_chat_res = client.post(
            f"/api/documents/{doc_id}/chat",
            headers=headers,
            json={"message": "What is the equipment ID?", "stream": False},
        )
        assert doc_chat_res.status_code == 200
        assert "PUMP-A17" in doc_chat_res.json()["content"]

    # 9. Clear Chat
    clear_res = client.post("/api/chat/clear", headers=headers)
    assert clear_res.status_code == 200

    # 10. Logout
    logout_res = client.post("/api/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    print("API Server endpoint unit checks passed!")


if __name__ == "__main__":
    test_api_server_flow()
