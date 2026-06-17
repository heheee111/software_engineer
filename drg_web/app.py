# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any

# 确保项目根目录在 sys.path 中，兼容 python drg_web/app.py 和 python -m drg_web 两种启动方式
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# 自动加载项目根目录的 .env 文件
try:
    from dotenv import load_dotenv
    _env_path = _project_root / ".env"
    if _env_path.is_file():
        load_dotenv(_env_path)
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from drg_agent.agent import DRGAgent, AgentReport
from drg_agent.docgen import (
    AI_DesignDocGenerator,
    AI_SRSGenerator,
    AI_TestReportGenerator,
    DesignDocGenerator,
    DocumentTemplate,
    LLMDocEnhancer,
    SRSGenerator,
    TemplateManager,
    TestReportGenerator,
    preview_document,
    revise_document,
)
from drg_agent.engine import GroupingResult
from drg_agent.testgen import (
    AITestCaseGenerator,
    TestCase,
    TestCaseClassifier,
    TestCaseExporter,
    TestCaseGenerator,
    TestCaseRunner,
    TestResult,
)
from drg_agent.virtual_docs import VirtualDocumentStore

_ROOT = Path(__file__).resolve().parent
_STATIC = _ROOT / "static"
_EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "slide6_emr.txt"

app = FastAPI(title="医保 DRG 入组（教学演示）", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 单例 ────────────────────────────────────────────────────────
_tm = TemplateManager()
_tm.ensure_buildin()
_vdocs = VirtualDocumentStore()

# 测试用例缓存（生成后在会话内复用）
_test_cases_cache: list[TestCase] = []
_test_results_cache: list[TestResult] = []


# ═══════════════════════════════════════════════════════════════════
# 请求/响应模型
# ═══════════════════════════════════════════════════════════════════

class GroupRequest(BaseModel):
    emr_text: str = Field(..., min_length=1, description="电子病历文本")
    use_llm: bool = Field(default=True, description="是否在已配置 API 时调用大模型润色")


class DocGenerateRequest(BaseModel):
    project_name: str = Field(default="医保 DRG 入组智能体", description="项目名称")
    use_llm: bool = Field(default=False, description="是否使用 AI 大模型增强文档质量")
    auto_submit: bool = Field(default=False, description="生成后是否自动提交到虚拟文档系统")
    change_note: str = Field(default="文档生成智能体自动提交", description="提交变更说明")


class TemplateSaveRequest(BaseModel):
    name: str = Field(..., min_length=1)
    doc_type: str = Field(..., description="srs | design | test_report")
    content: str = Field(..., min_length=1)
    description: str = Field(default="")
    version: str = Field(default="1.0")


class ReviseRequest(BaseModel):
    content: str = Field(..., min_length=1)
    edits: list[dict] = Field(default_factory=list, description='[{"line": N, "new_text": "..."}]')


class TestExecuteRequest(BaseModel):
    case_ids: list[str] | None = Field(default=None, description="指定用例 ID 列表，为空则执行全部")


class TestGenerateRequest(BaseModel):
    use_llm: bool = Field(default=False, description="是否使用 AI 大模型生成额外测试用例并做覆盖分析")


class VirtualDocSubmitRequest(BaseModel):
    doc_type: str = Field(default="other", description="srs | design | test_report | ai_custom | other")
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    change_note: str = Field(default="")
    source_agent: str = Field(default="web")
    doc_id: str | None = Field(default=None, description="为空则创建新文档；有值则更新该文档版本")
    version: str | None = Field(default=None, description="可手动指定语义化版本号")


# ═══════════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════════

def _serialize_result(g: GroupingResult) -> dict:
    return {
        "mdc_code": g.mdc_code,
        "mdc_name": g.mdc_name,
        "adrg_code": g.adrg_code,
        "adrg_name": g.adrg_name,
        "drg_code": g.drg_code,
        "drg_name": g.drg_name,
        "mcc_hits": g.mcc_hits,
        "cc_hits": g.cc_hits,
        "reason_steps": g.reason_steps,
    }


def _run_agent(emr_text: str, use_llm: bool) -> AgentReport:
    agent = DRGAgent(llm_enabled=use_llm)
    return agent.run(emr_text)


def _submit_generated_doc(req: DocGenerateRequest, doc_type: str, content: str) -> dict | None:
    if not req.auto_submit:
        return None
    title_map = {
        "srs": "软件需求规格说明书",
        "design": "概要设计说明书",
        "test_report": "测试报告",
    }
    return _vdocs.submit(
        content=content,
        doc_type=doc_type,
        title=f"{req.project_name}-{title_map.get(doc_type, '文档')}",
        change_note=req.change_note,
        source_agent="docgen_ai" if req.use_llm else "docgen",
    )


# ═══════════════════════════════════════════════════════════════════
# 原有 API — DRG 入组
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/example-emr")
def example_emr():
    if not _EXAMPLE.is_file():
        raise HTTPException(status_code=404, detail="示例文件不存在")
    return {"emr_text": _EXAMPLE.read_text(encoding="utf-8")}


@app.post("/api/group")
def group(req: GroupRequest):
    try:
        report = _run_agent(req.emr_text.strip(), use_llm=req.use_llm)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(e), "detail": None},
        )
    except Exception:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": "服务器内部错误",
                "detail": traceback.format_exc(),
            },
        )

    return {
        "ok": True,
        "error": None,
        "grouping": _serialize_result(report.grouping),
        "narrative": report.narrative,
    }


# ═══════════════════════════════════════════════════════════════════
# FR-012/013/014: 文档生成 API
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/docs/srs")
def api_generate_srs(req: DocGenerateRequest):
    """生成符合 IEEE 830 标准的 SRS 文档（可选 AI 增强）。"""
    try:
        if req.use_llm:
            gen = AI_SRSGenerator()
            content = gen.generate(req.project_name, use_llm=True)
            enhanced = True
        else:
            gen = SRSGenerator()
            content = gen.generate(req.project_name)
            enhanced = False
        preview = preview_document(content)
        submission = _submit_generated_doc(req, "srs", content)
        return {"ok": True, "content": content, "preview": preview, "ai_enhanced": enhanced, "submission": submission}
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": traceback.format_exc()},
        )


@app.post("/api/docs/design")
def api_generate_design(req: DocGenerateRequest):
    """生成概要设计文档（可选 AI 增强）。"""
    try:
        if req.use_llm:
            gen = AI_DesignDocGenerator()
            content = gen.generate(req.project_name, use_llm=True)
            enhanced = True
        else:
            gen = DesignDocGenerator()
            content = gen.generate(req.project_name)
            enhanced = False
        preview = preview_document(content)
        submission = _submit_generated_doc(req, "design", content)
        return {"ok": True, "content": content, "preview": preview, "ai_enhanced": enhanced, "submission": submission}
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": traceback.format_exc()},
        )


@app.post("/api/docs/test-report")
def api_generate_test_report(req: DocGenerateRequest):
    """基于测试执行结果生成测试报告（可选 AI 增强）。"""
    try:
        results_dicts = [r.to_dict() for r in _test_results_cache]
        if req.use_llm:
            gen = AI_TestReportGenerator()
            content = gen.generate(results_dicts, req.project_name, use_llm=True)
            enhanced = True
        else:
            gen = TestReportGenerator()
            content = gen.generate(results_dicts, req.project_name)
            enhanced = False
        preview = preview_document(content)
        submission = _submit_generated_doc(req, "test_report", content)
        return {"ok": True, "content": content, "preview": preview, "ai_enhanced": enhanced, "submission": submission}
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": traceback.format_exc()},
        )


# ═══════════════════════════════════════════════════════════════════
# FR-015: 文档模板管理 API
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/docs/templates")
def api_list_templates(doc_type: str | None = Query(default=None)):
    """列出所有模板，可按 doc_type 过滤。"""
    templates = _tm.list_templates(doc_type)
    return {"ok": True, "templates": templates}


@app.get("/api/docs/templates/{name}")
def api_get_template(name: str):
    """获取指定模板。"""
    t = _tm.get_template(name)
    if t is None:
        raise HTTPException(status_code=404, detail=f"模板 '{name}' 不存在")
    return {"ok": True, "template": t.to_dict()}


@app.post("/api/docs/templates")
def api_save_template(req: TemplateSaveRequest):
    """保存或更新模板。"""
    try:
        t = DocumentTemplate(
            name=req.name,
            doc_type=req.doc_type,
            content=req.content,
            description=req.description,
            version=req.version,
        )
        path = _tm.save_template(t)
        return {"ok": True, "saved": str(path)}
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": traceback.format_exc()},
        )


@app.delete("/api/docs/templates/{name}")
def api_delete_template(name: str):
    """删除模板。"""
    deleted = _tm.delete_template(name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"模板 '{name}' 不存在")
    return {"ok": True, "deleted": name}


# ═══════════════════════════════════════════════════════════════════
# FR-016: 文档预览与手动修订 API
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/docs/preview")
def api_preview(req: ReviseRequest):
    """预览文档内容并支持行级修订。"""
    if req.edits:
        revised = revise_document(req.content, req.edits)
        preview = preview_document(revised)
        return {"ok": True, "revised": True, "content": revised, "preview": preview}
    else:
        preview = preview_document(req.content)
        return {"ok": True, "revised": False, "content": req.content, "preview": preview}


# ═══════════════════════════════════════════════════════════════════
# FR-021~025: 虚拟文档系统与文档提交 API
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/virtual-docs/submit")
def api_submit_virtual_doc(req: VirtualDocSubmitRequest):
    """提交新文档或更新已有文档版本。"""
    doc = _vdocs.submit(
        content=req.content,
        doc_type=req.doc_type,
        title=req.title,
        change_note=req.change_note,
        source_agent=req.source_agent,
        doc_id=req.doc_id,
        version=req.version,
    )
    return {"ok": doc.get("status") == "success", "document": doc}


@app.get("/api/virtual-docs")
def api_list_virtual_docs(
    doc_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    """按文档类型或提交状态查询虚拟文档。"""
    return {"ok": True, "documents": _vdocs.list(doc_type=doc_type, status=status)}


@app.get("/api/virtual-docs/{doc_id}")
def api_get_virtual_doc(doc_id: str, version: str | None = Query(default=None)):
    """按文档 ID 与版本号查询文档内容。"""
    doc = _vdocs.get(doc_id, version=version, include_content=True)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"文档 '{doc_id}' 不存在")
    return {"ok": True, "document": doc}


@app.put("/api/virtual-docs/{doc_id}")
def api_update_virtual_doc(doc_id: str, req: VirtualDocSubmitRequest):
    """更新已有文档，自动递增 patch 版本号，或使用请求中的指定版本号。"""
    doc = _vdocs.submit(
        content=req.content,
        doc_type=req.doc_type,
        title=req.title,
        change_note=req.change_note,
        source_agent=req.source_agent,
        doc_id=doc_id,
        version=req.version,
    )
    return {"ok": doc.get("status") == "success", "document": doc}


@app.post("/api/virtual-docs/retry")
def api_retry_virtual_docs(doc_id: str | None = Query(default=None)):
    """重试待重试/失败状态的文档提交记录。"""
    return _vdocs.retry_failed(doc_id)


# ═══════════════════════════════════════════════════════════════════
# FR-017: 测试用例自动生成 API
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/tests/generate")
def api_generate_tests(req: TestGenerateRequest = TestGenerateRequest()):
    """基于规则文件自动生成测试用例集（可选 AI 增强）。"""
    global _test_cases_cache
    try:
        if req.use_llm:
            gen = AITestCaseGenerator()
            _test_cases_cache = gen.generate(use_llm=True)
            coverage = gen.coverage_analysis(_test_cases_cache)
            enhanced = True
        else:
            gen = TestCaseGenerator()
            _test_cases_cache = gen.generate()
            coverage = None
            enhanced = False
        summary = TestCaseClassifier.summary(_test_cases_cache)
        by_cat = TestCaseClassifier.by_category(_test_cases_cache)
        result = {
            "ok": True,
            "summary": summary,
            "ai_enhanced": enhanced,
            "cases": {
                cat: [c.to_dict() for c in cases]
                for cat, cases in by_cat.items()
            },
        }
        if coverage:
            result["coverage_analysis"] = coverage
        return result
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": traceback.format_exc()},
        )


# ═══════════════════════════════════════════════════════════════════
# FR-018: 测试用例分类查询 API
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/tests/list")
def api_list_tests(
    category: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    module: str | None = Query(default=None),
):
    """按条件筛选测试用例。"""
    if not _test_cases_cache:
        return {"ok": True, "summary": {"total": 0}, "cases": []}

    filtered = _test_cases_cache
    if category:
        filtered = [c for c in filtered if c.category == category]
    if priority:
        filtered = [c for c in filtered if c.priority == priority]
    if module:
        filtered = [c for c in filtered if c.module == module]

    return {
        "ok": True,
        "summary": TestCaseClassifier.summary(filtered),
        "cases": [c.to_dict() for c in filtered],
    }


# ═══════════════════════════════════════════════════════════════════
# FR-019: 测试用例执行 API
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/tests/execute")
def api_execute_tests(req: TestExecuteRequest):
    """执行测试用例并与预期结果比对。"""
    global _test_results_cache
    if not _test_cases_cache:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "请先生成测试用例（POST /api/tests/generate）"},
        )

    # 筛选要执行的用例
    if req.case_ids:
        id_set = set(req.case_ids)
        cases = [c for c in _test_cases_cache if c.id in id_set]
    else:
        cases = _test_cases_cache

    runner = TestCaseRunner()
    _test_results_cache = runner.run(cases)

    total = len(_test_results_cache)
    passed = sum(1 for r in _test_results_cache if r.passed)
    return {
        "ok": True,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": f"{passed / total * 100:.1f}%" if total > 0 else "N/A",
        },
        "results": [r.to_dict() for r in _test_results_cache],
    }


# ═══════════════════════════════════════════════════════════════════
# FR-020: 测试用例导出 API
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/tests/export")
def api_export_tests(fmt: str = Query(default="json", description="导出格式: json")):
    """导出测试用例为 JSON 格式（也可导出最新执行结果）。"""
    if fmt not in ("json",):
        raise HTTPException(status_code=400, detail=f"不支持的格式: {fmt}")

    if _test_results_cache:
        data = TestCaseExporter.results_to_json(_test_results_cache)
    elif _test_cases_cache:
        data = TestCaseExporter.cases_to_json(_test_cases_cache)
    else:
        data = json.dumps({"error": "没有测试数据可供导出"}, ensure_ascii=False)

    return Response(
        content=data,
        media_type="application/json; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=drg_test_export.json"
        },
    )


# ═══════════════════════════════════════════════════════════════════
# AI 自由内容生成
# ═══════════════════════════════════════════════════════════════════

class AIGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="用户输入的生成要求")
    context: str = Field(default="", description="可选的上下文信息")


@app.post("/api/docs/ai-generate")
def api_ai_generate(req: AIGenerateRequest):
    """使用 AI 自由生成文档片段。"""
    try:
        content = LLMDocEnhancer.generate_custom_section(req.prompt, req.context)
        if content is None:
            return JSONResponse(
                status_code=503,
                content={"ok": False, "error": "LLM 服务不可用，请检查 API Key 配置。"},
            )
        preview = preview_document(content)
        return {"ok": True, "content": content, "preview": preview}
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": traceback.format_exc()},
        )


# ═══════════════════════════════════════════════════════════════════
# 前端静态文件
# ═══════════════════════════════════════════════════════════════════

app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@app.get("/")
def index_page():
    index = _STATIC / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=500, detail="前端文件缺失")
    return FileResponse(index, media_type="text/html; charset=utf-8")
