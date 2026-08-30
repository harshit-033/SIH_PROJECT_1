import re
import sys
from pathlib import Path

import ollama

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app import MODEL_NAME, build_document_context, build_document_prompt, extract_pdf  # noqa: E402
from create_synthetic_pdfs import create_inspection_report  # noqa: E402


def ask_document(question: str) -> str:
    extraction = extract_pdf(str(create_inspection_report()))
    context = build_document_context(extraction.pages)
    prompt = build_document_prompt(question, context.text)
    answer_parts = []

    stream = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )

    for chunk in stream:
        piece = chunk.get("message", {}).get("content", "")
        if piece:
            answer_parts.append(piece)

    return "".join(answer_parts)


def require_match(answer: str, pattern: str, label: str) -> None:
    if not re.search(pattern, answer, re.IGNORECASE):
        raise AssertionError(f"Missing {label}. Answer was:\n{answer}")


def main() -> None:
    equipment = ask_document("What is the equipment ID?")
    require_match(equipment, r"PUMP[- ]?A17", "equipment ID PUMP-A17")

    temperature = ask_document("What was the bearing temperature?")
    require_match(temperature, r"86\s*(?:c|.c)?", "bearing temperature 86 C")

    findings = ask_document("What are the main findings?")
    require_match(findings, r"bearing temperature|temperature exceeded|elevated", "bearing temperature finding")
    require_match(findings, r"vibration", "increased vibration trend")

    missing = ask_document("What is the warranty expiration date?")
    require_match(
        missing,
        r"not available|not provided|does not provide|no information|not mentioned",
        "missing-information abstention",
    )

    print("Local model document QA checks passed")
    print(f"Model: {MODEL_NAME}")


if __name__ == "__main__":
    main()
