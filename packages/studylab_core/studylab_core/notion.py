from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from uuid import uuid4

from .models import Artifact, NotionExportResult


class NotionExporter:
    def __init__(self, token: str | None = None, mock: bool | None = None) -> None:
        self.token = token or os.getenv("NOTION_API_KEY")
        self.mock = bool(mock) if mock is not None else os.getenv("NOTION_MOCK_EXPORT", "").lower() == "true"

    def export_artifact(
        self,
        artifact: Artifact,
        parent_page_id: str | None = None,
        data_source_id: str | None = None,
    ) -> NotionExportResult:
        if self.mock:
            page_id = uuid4().hex
            return NotionExportResult(
                connected=True,
                message="Created a mock Notion page for local development.",
                page_id=page_id,
                page_url=f"https://notion.local/{page_id}",
            )
        if not self.token:
            return NotionExportResult(
                connected=False,
                message="Connect Notion by setting NOTION_API_KEY, or enable NOTION_MOCK_EXPORT=true for local demos.",
            )

        payload = self._build_payload(artifact, parent_page_id=parent_page_id, data_source_id=data_source_id)
        request = urllib.request.Request(
            "https://api.notion.com/v1/pages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            return NotionExportResult(connected=False, message=f"Notion export failed: {exc}")
        return NotionExportResult(
            connected=True,
            message="Created Notion page.",
            page_id=data.get("id"),
            page_url=data.get("url"),
        )

    def _build_payload(
        self,
        artifact: Artifact,
        parent_page_id: str | None,
        data_source_id: str | None,
    ) -> dict:
        if data_source_id:
            parent = {"data_source_id": data_source_id}
            properties = {"Name": {"title": [{"text": {"content": artifact.title}}]}}
        elif parent_page_id:
            parent = {"page_id": parent_page_id}
            properties = {"title": [{"text": {"content": artifact.title}}]}
        else:
            parent = {"type": "workspace", "workspace": True}
            properties = {"title": [{"text": {"content": artifact.title}}]}

        return {
            "parent": parent,
            "properties": properties,
            "children": self._markdown_to_blocks(artifact.content_markdown),
        }

    def _markdown_to_blocks(self, markdown: str) -> list[dict]:
        blocks = []
        for raw_line in markdown.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("# "):
                blocks.append({"object": "block", "type": "heading_1", "heading_1": self._rich(line[2:])})
            elif line.startswith("## "):
                blocks.append({"object": "block", "type": "heading_2", "heading_2": self._rich(line[3:])})
            elif line.startswith("- "):
                blocks.append({"object": "block", "type": "bulleted_list_item", "bulleted_list_item": self._rich(line[2:])})
            else:
                blocks.append({"object": "block", "type": "paragraph", "paragraph": self._rich(line)})
        return blocks[:100]

    def _rich(self, content: str) -> dict:
        return {"rich_text": [{"type": "text", "text": {"content": content[:1800]}}]}
