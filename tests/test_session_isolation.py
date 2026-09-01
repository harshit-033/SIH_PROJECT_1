import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from create_synthetic_pdfs import create_inspection_report, create_scanned_inspection_report
from server.main import app


def test_session_isolation():
    client = TestClient(app)

    # 1. Login Client 1 (User 1)
    res1 = client.post("/api/auth/login", json={"username": "user1", "password": "pass123"})
    assert res1.status_code == 200
    token1 = res1.json()["token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # 2. Login Client 2 (User 2)
    res2 = client.post("/api/auth/login", json={"username": "user2", "password": "pass123"})
    assert res2.status_code == 200
    token2 = res2.json()["token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # 3. Client 1 uploads Digital PDF (Doc A)
    doc_a_path = create_inspection_report()
    with open(doc_a_path, "rb") as f:
        up1 = client.post(
            "/api/documents",
            headers=headers1,
            files={"file": ("doc_a.pdf", f, "application/pdf")},
        )
    assert up1.status_code == 200
    doc_a_id = up1.json()["document"]["document_id"]

    # 4. Client 2 uploads Scanned PDF (Doc B)
    doc_b_path = create_scanned_inspection_report()
    with open(doc_b_path, "rb") as f:
        up2 = client.post(
            "/api/documents",
            headers=headers2,
            files={"file": ("doc_b.pdf", f, "application/pdf")},
        )
    assert up2.status_code == 200
    doc_b_id = up2.json()["document"]["document_id"]

    # 5. Isolation Check: Client 2 tries to access Client 1's Doc A -> REJECT (403)
    hijack_attempt = client.post(
        f"/api/documents/{doc_a_id}/chat",
        headers=headers2,
        json={"message": "What is in this doc?", "stream": False},
    )
    assert hijack_attempt.status_code == 403, f"Expected 403, got {hijack_attempt.status_code}"

    # 6. Isolation Check: Client 1 tries to access Client 2's Doc B -> REJECT (403)
    hijack_attempt_2 = client.post(
        f"/api/documents/{doc_b_id}/chat",
        headers=headers1,
        json={"message": "What is in this doc?", "stream": False},
    )
    assert hijack_attempt_2.status_code == 403, f"Expected 403, got {hijack_attempt_2.status_code}"

    # 7. Document Listing Isolation
    docs_user1 = client.get("/api/documents", headers=headers1).json()["documents"]
    docs_user2 = client.get("/api/documents", headers=headers2).json()["documents"]

    assert len(docs_user1) == 1
    assert docs_user1[0]["document_id"] == doc_a_id
    assert len(docs_user2) == 1
    assert docs_user2[0]["document_id"] == doc_b_id

    # 8. Chat message isolation
    with patch("core.ai_service.ollama.chat") as mock_chat:
        mock_chat.return_value = {"message": {"content": "Answer for user 1"}}
        client.post(
            f"/api/documents/{doc_a_id}/chat",
            headers=headers1,
            json={"message": "Question 1", "stream": False},
        )

    sess1_info = client.get("/api/session", headers=headers1).json()
    sess2_info = client.get("/api/session", headers=headers2).json()

    assert len(sess1_info["document_messages"]) > 0
    assert len(sess2_info["document_messages"]) == 0  # User 2 has not chatted yet

    # 9. Clear Client 1 does not affect Client 2
    client.post("/api/chat/clear", headers=headers1)
    sess1_after_clear = client.get("/api/session", headers=headers1).json()
    sess2_after_clear = client.get("/api/session", headers=headers2).json()

    assert sess1_after_clear["mode"] == "General Chat"
    assert sess2_after_clear["mode"] == "Document Analysis"
    assert sess2_after_clear["current_document_id"] == doc_b_id

    print("Session isolation & multi-client state verification PASSED!")


if __name__ == "__main__":
    test_session_isolation()
