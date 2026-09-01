import io
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.file_handler import FileHandler
from create_synthetic_pdfs import create_corrupted_pdf
from server.main import app


def test_security_and_file_handling():
    client = TestClient(app)

    # Login
    login_res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Non-PDF upload rejection
    txt_file = io.BytesIO(b"Hello plain text")
    res_txt = client.post(
        "/api/documents",
        headers=headers,
        files={"file": ("malicious.txt", txt_file, "text/plain")},
    )
    assert res_txt.status_code == 400
    assert "Only PDF files are supported" in res_txt.json()["detail"]

    # 2. Empty file upload rejection
    empty_file = io.BytesIO(b"")
    res_empty = client.post(
        "/api/documents",
        headers=headers,
        files={"file": ("empty.pdf", empty_file, "application/pdf")},
    )
    assert res_empty.status_code == 400
    assert "empty" in res_empty.json()["detail"].lower()

    # 3. Corrupted PDF handling
    corrupt_pdf_path = create_corrupted_pdf()
    with open(corrupt_pdf_path, "rb") as f:
        res_corrupt = client.post(
            "/api/documents",
            headers=headers,
            files={"file": ("corrupted_input.pdf", f, "application/pdf")},
        )
    assert res_corrupt.status_code == 400

    # 4. Path traversal sanitization check
    handler = FileHandler(base_upload_dir=str(PROJECT_ROOT / "uploads"))
    sanitized = handler.sanitize_filename("../../../etc/passwd.pdf")
    assert ".." not in sanitized
    assert "/" not in sanitized
    assert "\\" not in sanitized

    # 5. Invalid session path check
    try:
        handler.get_session_dir("../outside_dir")
        assert False, "Should raise ValueError on path traversal session ID"
    except ValueError:
        pass

    print("Security and file handling checks PASSED!")


if __name__ == "__main__":
    test_security_and_file_handling()
