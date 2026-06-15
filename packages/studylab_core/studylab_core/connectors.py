from __future__ import annotations

import html
import os
import re
from typing import Any
from urllib.parse import urlparse

from .models import ConnectorType, SourceGuide, SourceImport
from .rag import RagEngine
from .store import InMemoryStudyLabStore


def _max_source_chars() -> int:
    raw = os.getenv("STUDYLAB_MAX_SOURCE_CHARS")
    try:
        return int(raw) if raw else 1_000_000
    except ValueError:
        return 1_000_000


class SourceConnectorEngine:
    """Validated Phase 4 source connector import path.

    The local core does not fetch remote content directly. Production connector
    workers should fetch, authorize, transcribe, or export content and pass the
    extracted text here so chunking, guides, citations, and notebook scoping stay
    identical to normal uploads.
    """

    supported_types: set[str] = {"website", "youtube", "audio", "google_doc", "google_slides"}

    def __init__(self, store: InMemoryStudyLabStore, rag: RagEngine) -> None:
        self.store = store
        self.rag = rag

    def import_source(
        self,
        notebook_id: str,
        connector_type: ConnectorType,
        title: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], SourceGuide, SourceImport]:
        if connector_type not in self.supported_types:
            raise ValueError(f"Unsupported connector_type: {connector_type}")

        text, metadata, warnings = self._normalize_payload(connector_type, payload)
        source, guide = self.rag.ingest_source(
            notebook_id=notebook_id,
            title=title.strip() or self._default_title(connector_type, metadata),
            text=text,
            kind=connector_type,
        )
        record = SourceImport(
            id=self.store.next_id("import"),
            notebook_id=notebook_id,
            source_id=source.id,
            connector_type=connector_type,
            title=source.title,
            status="ready",
            metadata=metadata,
            warnings=warnings,
        )
        if hasattr(self.store, "add_source_import"):
            record = self.store.add_source_import(record)
        return self.store.to_plain(source), guide, record

    def _normalize_payload(self, connector_type: ConnectorType, payload: dict[str, Any]) -> tuple[str, dict[str, Any], list[str]]:
        metadata = self._metadata(connector_type, payload)
        warnings = [
            "Remote fetching is disabled in the local core; import uses extracted text supplied by the connector worker."
        ]

        if connector_type == "website":
            text = str(payload.get("extracted_text") or payload.get("text") or "")
            if not text and payload.get("html"):
                text = self._strip_html(str(payload["html"]))
                warnings.append("HTML was stripped before chunking.")
        elif connector_type == "youtube":
            text = self._transcript_text(payload)
        elif connector_type == "audio":
            text = str(payload.get("transcript") or payload.get("extracted_text") or payload.get("text") or "")
        elif connector_type in {"google_doc", "google_slides"}:
            text = str(payload.get("exported_text") or payload.get("text") or "")
        else:
            text = ""

        text = self._clean_text(text)
        if not text:
            raise ValueError(f"{connector_type} import requires extracted text, transcript, exported_text, or html content")
        cap = _max_source_chars()
        if len(text) > cap:
            raise ValueError(f"imported content exceeds the maximum of {cap} characters")
        return text, metadata, warnings

    def _metadata(self, connector_type: ConnectorType, payload: dict[str, Any]) -> dict[str, Any]:
        metadata: dict[str, Any] = {"connector_type": connector_type}
        url = payload.get("url")
        if url is not None:
            metadata["url"] = self._validate_url(str(url))

        for key in ("external_id", "video_id", "document_id", "presentation_id", "language", "duration_seconds"):
            if payload.get(key) is not None:
                metadata[key] = payload[key]

        if connector_type == "website" and "url" not in metadata:
            raise ValueError("website import requires a url")
        if connector_type == "youtube" and not (metadata.get("url") or metadata.get("video_id")):
            raise ValueError("youtube import requires a url or video_id")
        if connector_type == "google_doc" and not (metadata.get("url") or metadata.get("document_id")):
            raise ValueError("google_doc import requires a url or document_id")
        if connector_type == "google_slides" and not (metadata.get("url") or metadata.get("presentation_id")):
            raise ValueError("google_slides import requires a url or presentation_id")
        return metadata

    def _validate_url(self, raw_url: str) -> str:
        parsed = urlparse(raw_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("connector url must be an absolute http or https URL")
        return raw_url

    def _transcript_text(self, payload: dict[str, Any]) -> str:
        transcript = payload.get("transcript") or payload.get("captions") or payload.get("text")
        if isinstance(transcript, list):
            parts: list[str] = []
            for item in transcript:
                if isinstance(item, dict):
                    parts.append(str(item.get("text", "")))
                else:
                    parts.append(str(item))
            return " ".join(parts)
        return str(transcript or "")

    def _strip_html(self, raw_html: str) -> str:
        without_blocks = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", raw_html)
        without_tags = re.sub(r"(?s)<[^>]+>", " ", without_blocks)
        return html.unescape(without_tags)

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _default_title(self, connector_type: ConnectorType, metadata: dict[str, Any]) -> str:
        label = connector_type.replace("_", " ").title()
        return f"{label} import {metadata.get('external_id') or metadata.get('video_id') or metadata.get('document_id') or ''}".strip()
