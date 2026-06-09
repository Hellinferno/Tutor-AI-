from __future__ import annotations

import base64


def extract_text_from_image_payload(content: str) -> str:
    """Small local OCR adapter placeholder.

    During Phase 1 local development, tests can pass base64-encoded text. Production
    swaps this for a real OCR service while preserving the solver contract.
    """

    try:
        decoded = base64.b64decode(content, validate=True).decode("utf-8")
    except Exception:
        return "OCR extraction is not connected in this local build."
    return decoded.strip() or "OCR extraction returned no text."
