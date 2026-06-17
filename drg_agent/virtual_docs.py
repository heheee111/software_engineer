# -*- coding: utf-8 -*-
"""虚拟文档系统：文档提交、持久化查询、版本管理与状态追踪。"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


DOC_TYPES = {"srs", "design", "test_report", "ai_custom", "other"}
STATUS_SUCCESS = "success"
STATUS_PENDING_RETRY = "pending_retry"
STATUS_FAILED = "failed"


def default_storage_root() -> Path:
    return Path(__file__).resolve().parent.parent / "virtual_docs" / "storage"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _safe_name(value: str) -> str:
    name = re.sub(r"[^0-9A-Za-z_.\-\u4e00-\u9fff]+", "_", value).strip("_")
    return name or "document"


def _parse_semver(version: str | None) -> tuple[int, int, int]:
    parts = (version or "0.0.0").split(".")
    nums = []
    for part in parts[:3]:
        nums.append(int(part) if part.isdigit() else 0)
    while len(nums) < 3:
        nums.append(0)
    return nums[0], nums[1], nums[2]


def next_patch_version(version: str | None) -> str:
    major, minor, patch = _parse_semver(version)
    return f"{major}.{minor}.{patch + 1}"


@dataclass
class DocumentVersion:
    version: str
    content_path: str
    change_note: str
    source_agent: str
    created_at: str
    bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "content_path": self.content_path,
            "change_note": self.change_note,
            "source_agent": self.source_agent,
            "created_at": self.created_at,
            "bytes": self.bytes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocumentVersion":
        return cls(
            version=data["version"],
            content_path=data["content_path"],
            change_note=data.get("change_note", ""),
            source_agent=data.get("source_agent", "unknown"),
            created_at=data.get("created_at", _now()),
            bytes=int(data.get("bytes", 0)),
        )


@dataclass
class StoredDocument:
    doc_id: str
    doc_type: str
    title: str
    current_version: str
    status: str
    created_at: str
    updated_at: str
    last_error: str = ""
    retry_count: int = 0
    versions: list[DocumentVersion] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "doc_type": self.doc_type,
            "title": self.title,
            "current_version": self.current_version,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_error": self.last_error,
            "retry_count": self.retry_count,
            "versions": [item.to_dict() for item in self.versions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StoredDocument":
        return cls(
            doc_id=data["doc_id"],
            doc_type=data.get("doc_type", "other"),
            title=data.get("title", "未命名文档"),
            current_version=data.get("current_version", "1.0.0"),
            status=data.get("status", STATUS_SUCCESS),
            created_at=data.get("created_at", _now()),
            updated_at=data.get("updated_at", _now()),
            last_error=data.get("last_error", ""),
            retry_count=int(data.get("retry_count", 0)),
            versions=[DocumentVersion.from_dict(v) for v in data.get("versions", [])],
        )


class VirtualDocumentStore:
    """轻量文件型虚拟文档仓库。"""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else default_storage_root()
        self.docs_dir = self.root / "documents"
        self.meta_dir = self.root / "metadata"

    def ensure(self) -> None:
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.meta_dir.mkdir(parents=True, exist_ok=True)

    def submit(
        self,
        *,
        content: str | bytes,
        doc_type: str,
        title: str,
        change_note: str = "",
        source_agent: str = "unknown",
        doc_id: str | None = None,
        version: str | None = None,
    ) -> dict[str, Any]:
        self.ensure()
        now = _now()
        normalized_type = doc_type if doc_type in DOC_TYPES else "other"

        if isinstance(content, bytes):
            content_text = content.decode("utf-8", errors="replace")
            content_bytes = content
        else:
            content_text = content
            content_bytes = content.encode("utf-8")

        if not content_text.strip():
            return self._failed_doc(doc_id, normalized_type, title, "文档内容为空")

        created = False
        if doc_id:
            existing = self.get(doc_id, include_content=False)
            if existing is None:
                return self._failed_doc(doc_id, normalized_type, title, f"文档 {doc_id} 不存在")
            stored = StoredDocument.from_dict(existing)
        else:
            created = True
            doc_id = uuid.uuid4().hex
            stored = StoredDocument(
                doc_id=doc_id,
                doc_type=normalized_type,
                title=title,
                current_version="0.0.0",
                status=STATUS_PENDING_RETRY,
                created_at=now,
                updated_at=now,
            )

        next_version = version or ("1.0.0" if created else next_patch_version(stored.current_version))
        version_dir = self.docs_dir / stored.doc_id
        version_dir.mkdir(parents=True, exist_ok=True)
        content_path = version_dir / f"{_safe_name(title)}_{next_version}.md"

        try:
            content_path.write_text(content_text, encoding="utf-8")
            stored.doc_type = normalized_type
            stored.title = title
            stored.current_version = next_version
            stored.status = STATUS_SUCCESS
            stored.updated_at = now
            stored.last_error = ""
            stored.versions.append(
                DocumentVersion(
                    version=next_version,
                    content_path=str(content_path.resolve()),
                    change_note=change_note or ("首次提交" if created else "版本更新"),
                    source_agent=source_agent,
                    created_at=now,
                    bytes=len(content_bytes),
                )
            )
            self._save_meta(stored)
        except Exception as exc:
            stored.status = STATUS_PENDING_RETRY
            stored.updated_at = now
            stored.last_error = str(exc)
            stored.retry_count += 1
            self._save_meta(stored)

        return stored.to_dict()

    def list(
        self,
        *,
        doc_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        self.ensure()
        docs: list[dict[str, Any]] = []
        for path in sorted(self.meta_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if doc_type and data.get("doc_type") != doc_type:
                continue
            if status and data.get("status") != status:
                continue
            docs.append(data)
        docs.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
        return docs

    def get(
        self,
        doc_id: str,
        *,
        version: str | None = None,
        include_content: bool = True,
    ) -> dict[str, Any] | None:
        self.ensure()
        path = self.meta_dir / f"{doc_id}.json"
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if include_content:
            selected = None
            target_version = version or data.get("current_version")
            for item in data.get("versions", []):
                if item.get("version") == target_version:
                    selected = item
                    break
            if selected:
                content_path = Path(selected["content_path"])
                data["content"] = content_path.read_text(encoding="utf-8") if content_path.is_file() else ""
                data["selected_version"] = selected["version"]
        return data

    def retry_failed(self, doc_id: str | None = None) -> dict[str, Any]:
        candidates = [self.get(doc_id, include_content=False)] if doc_id else self.list()
        retried: list[dict[str, Any]] = []
        for data in candidates:
            if not data or data.get("status") not in {STATUS_PENDING_RETRY, STATUS_FAILED}:
                continue
            stored = StoredDocument.from_dict(data)
            stored.retry_count += 1
            stored.updated_at = _now()
            if stored.versions:
                stored.status = STATUS_SUCCESS
                stored.last_error = ""
            else:
                stored.status = STATUS_FAILED
                stored.last_error = stored.last_error or "没有可重试的文档内容"
            self._save_meta(stored)
            retried.append(stored.to_dict())
        return {"ok": True, "retried": len(retried), "documents": retried}

    def _save_meta(self, doc: StoredDocument) -> None:
        self.ensure()
        path = self.meta_dir / f"{doc.doc_id}.json"
        path.write_text(json.dumps(doc.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def _failed_doc(self, doc_id: str | None, doc_type: str, title: str, error: str) -> dict[str, Any]:
        now = _now()
        return StoredDocument(
            doc_id=doc_id or uuid.uuid4().hex,
            doc_type=doc_type,
            title=title or "未命名文档",
            current_version="0.0.0",
            status=STATUS_FAILED,
            created_at=now,
            updated_at=now,
            last_error=error,
        ).to_dict()
