# -*- coding: utf-8 -*-
"""独立虚拟文档系统：文档提交、查询、版本更新与状态重试。"""

from __future__ import annotations

import argparse

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from drg_agent.virtual_docs import VirtualDocumentStore

app = FastAPI(title="虚拟文档系统", version="0.2.0")
store = VirtualDocumentStore()


class SubmitRequest(BaseModel):
    doc_type: str = Field(default="other")
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    change_note: str = Field(default="")
    source_agent: str = Field(default="unknown")
    doc_id: str | None = Field(default=None)
    version: str | None = Field(default=None)


@app.post("/submit")
async def submit(
    file: UploadFile | None = File(default=None),
    source_agent: str = Form(default="unknown"),
    note: str = Form(default=""),
    doc_type: str = Form(default="other"),
    title: str = Form(default=""),
    doc_id: str | None = Form(default=None),
    version: str | None = Form(default=None),
):
    """兼容课件里的 multipart 文档提交接口。"""
    if file is None:
        raise HTTPException(status_code=400, detail="缺少上传文件")
    content = await file.read()
    doc = store.submit(
        content=content,
        doc_type=doc_type,
        title=title or file.filename or "未命名文档",
        change_note=note,
        source_agent=source_agent,
        doc_id=doc_id,
        version=version,
    )
    return JSONResponse({"ok": doc.get("status") == "success", "document": doc})


@app.post("/documents")
def submit_json(req: SubmitRequest):
    """JSON REST 提交接口：创建新文档或更新已有文档版本。"""
    doc = store.submit(
        content=req.content,
        doc_type=req.doc_type,
        title=req.title,
        change_note=req.change_note,
        source_agent=req.source_agent,
        doc_id=req.doc_id,
        version=req.version,
    )
    return {"ok": doc.get("status") == "success", "document": doc}


@app.get("/documents")
def list_documents(
    doc_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    return {"ok": True, "documents": store.list(doc_type=doc_type, status=status)}


@app.get("/documents/{doc_id}")
def get_document(doc_id: str, version: str | None = Query(default=None)):
    doc = store.get(doc_id, version=version, include_content=True)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"文档 '{doc_id}' 不存在")
    return {"ok": True, "document": doc}


@app.put("/documents/{doc_id}")
def update_document(doc_id: str, req: SubmitRequest):
    doc = store.submit(
        content=req.content,
        doc_type=req.doc_type,
        title=req.title,
        change_note=req.change_note,
        source_agent=req.source_agent,
        doc_id=doc_id,
        version=req.version,
    )
    return {"ok": doc.get("status") == "success", "document": doc}


@app.post("/documents/retry")
def retry_documents(doc_id: str | None = Query(default=None)):
    return store.retry_failed(doc_id)


@app.get("/health")
def health():
    store.ensure()
    return {"status": "ok", "storage": str(store.root.resolve())}


def main():
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
