import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from create_synthetic_pdfs import create_inspection_report, create_scanned_inspection_report
from server.main import app


def run_e2e_cycle(run_num: int):
    client = TestClient(app)

    # 1. Health check
    h = client.get("/health")
    assert h.status_code == 200

    # 2. Client 1 login & workflow
    res1 = client.post("/api/auth/login", json={"username": "user1", "password": "pass123"})
    assert res1.status_code == 200
    token1 = res1.json()["token"]
    h1 = {"Authorization": f"Bearer {token1}"}

    # 3. Client 2 login & workflow
    res2 = client.post("/api/auth/login", json={"username": "user2", "password": "pass123"})
    assert res2.status_code == 200
    token2 = res2.json()["token"]
    h2 = {"Authorization": f"Bearer {token2}"}

    # 4. Client 1 uploads Digital PDF
    pdf1 = create_inspection_report()
    with open(pdf1, "rb") as f:
        up1 = client.post("/api/documents", headers=h1, files={"file": ("insp.pdf", f, "application/pdf")})
    assert up1.status_code == 200
    doc1_id = up1.json()["document"]["document_id"]

    # 5. Client 2 uploads Scanned PDF
    pdf2 = create_scanned_inspection_report()
    with open(pdf2, "rb") as f:
        up2 = client.post("/api/documents", headers=h2, files={"file": ("scan.pdf", f, "application/pdf")})
    assert up2.status_code == 200
    doc2_id = up2.json()["document"]["document_id"]

    # 6. Verify distinct extraction methods
    assert "native" in up1.json()["document"]["method_summary"]
    assert "OCR" in up2.json()["document"]["method_summary"]

    # 7. Mocked Q&A checks
    with patch("core.ai_service.ollama.chat") as mock_chat:
        mock_chat.return_value = {"message": {"content": "Equipment is PUMP-A17"}}
        q1 = client.post(f"/api/documents/{doc1_id}/chat", headers=h1, json={"message": "Equipment ID?", "stream": False})
        assert "PUMP-A17" in q1.json()["content"]

        mock_chat.return_value = {"message": {"content": "Scanned equipment is SCAN-A01"}}
        q2 = client.post(f"/api/documents/{doc2_id}/chat", headers=h2, json={"message": "Equipment ID?", "stream": False})
        assert "SCAN-A01" in q2.json()["content"]

    # 8. Clean up
    client.post("/api/chat/clear", headers=h1)
    client.post("/api/chat/clear", headers=h2)
    client.post("/api/auth/logout", headers=h1)
    client.post("/api/auth/logout", headers=h2)
    print(f"E2E Demonstration Run {run_num}: PASS")


def main():
    for i in range(1, 4):
        run_e2e_cycle(i)
    print("Three full multi-client E2E demonstration cycles PASSED!")


if __name__ == "__main__":
    main()
