# -*- coding: utf-8 -*-
"""文档自动生成智能体：SRS / 设计文档 / 测试报告 / 模板管理。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Any

# ─── 模板存储目录 ───────────────────────────────────────────────
_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def _ensure_template_dir() -> Path:
    _TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    return _TEMPLATE_DIR


# ═══════════════════════════════════════════════════════════════════
# 文档模板模型
# ═══════════════════════════════════════════════════════════════════

@dataclass
class DocumentTemplate:
    name: str
    doc_type: str  # "srs" | "design" | "test_report"
    content: str
    description: str = ""
    version: str = "1.0"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "doc_type": self.doc_type,
            "content": self.content,
            "description": self.description,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DocumentTemplate":
        return cls(
            name=d["name"],
            doc_type=d["doc_type"],
            content=d["content"],
            description=d.get("description", ""),
            version=d.get("version", "1.0"),
        )


# ═══════════════════════════════════════════════════════════════════
# FR-015: 模板管理
# ═══════════════════════════════════════════════════════════════════

class TemplateManager:
    """文档模板的 CRUD 操作，模板以 JSON 文件存储在 templates/ 目录下。"""

    def __init__(self) -> None:
        self._dir = _ensure_template_dir()

    def list_templates(self, doc_type: str | None = None) -> list[dict]:
        """列出所有模板，可按 doc_type 过滤。"""
        result: list[dict] = []
        for f in sorted(self._dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if doc_type and data.get("doc_type") != doc_type:
                    continue
                result.append(data)
            except (json.JSONDecodeError, KeyError):
                continue
        return result

    def get_template(self, name: str) -> DocumentTemplate | None:
        """按名称获取模板。"""
        path = self._dir / f"{name}.json"
        if not path.is_file():
            return None
        return DocumentTemplate.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save_template(self, template: DocumentTemplate) -> Path:
        """保存或更新模板。"""
        path = self._dir / f"{template.name}.json"
        path.write_text(
            json.dumps(template.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def delete_template(self, name: str) -> bool:
        """删除模板，返回是否成功。"""
        path = self._dir / f"{name}.json"
        if path.is_file():
            path.unlink()
            return True
        return False

    def buildin_templates(self) -> list[DocumentTemplate]:
        """返回内置默认模板。"""
        return [
            DocumentTemplate(
                name="srs_default",
                doc_type="srs",
                description="IEEE 830 SRS 默认模板",
                content=_DEFAULT_SRS_TEMPLATE,
            ),
            DocumentTemplate(
                name="design_default",
                doc_type="design",
                description="概要设计默认模板",
                content=_DEFAULT_DESIGN_TEMPLATE,
            ),
            DocumentTemplate(
                name="test_report_default",
                doc_type="test_report",
                description="测试报告默认模板",
                content=_DEFAULT_TEST_REPORT_TEMPLATE,
            ),
        ]

    def ensure_buildin(self) -> None:
        """确保内置模板已存入磁盘。"""
        for t in self.buildin_templates():
            path = self._dir / f"{t.name}.json"
            if not path.is_file():
                self.save_template(t)


# ═══════════════════════════════════════════════════════════════════
# 默认模板内容
# ═══════════════════════════════════════════════════════════════════

_DEFAULT_SRS_TEMPLATE = dedent("""\
# 软件需求规格说明书（SRS）

**遵循 IEEE 830 标准**

| 项目 | 内容 |
|------|------|
| 文档版本 | {doc_version} |
| 生成时间 | {timestamp} |
| 项目名称 | {project_name} |
| 作者 | {author} |

---

## 1. 引言

### 1.1 目的
{introduction_purpose}

### 1.2 范围
{introduction_scope}

### 1.3 定义、缩写词与术语
{introduction_terms}

### 1.4 参考文献
{introduction_references}

### 1.5 文档概述
{introduction_overview}

---

## 2. 综合描述

### 2.1 产品视角
{overall_product_perspective}

### 2.2 产品功能
{overall_product_functions}

### 2.3 用户特征
{overall_user_characteristics}

### 2.4 约束条件
{overall_constraints}

### 2.5 假设与依赖
{overall_assumptions}

---

## 3. 分析模型

### 3.1 用例图描述
{analysis_use_cases}

### 3.2 数据流图
{analysis_data_flow}

### 3.3 状态转换图
{analysis_state_transition}

---

## 4. 功能需求

{functional_requirements}

---

## 5. 非功能需求

### 5.1 性能需求
{nonfunctional_performance}

### 5.2 安全性需求
{nonfunctional_security}

### 5.3 可用性需求
{nonfunctional_usability}

### 5.4 可维护性需求
{nonfunctional_maintainability}

### 5.5 可移植性需求
{nonfunctional_portability}

---

## 附录

{appendix}
""")

_DEFAULT_DESIGN_TEMPLATE = dedent("""\
# 概要设计说明书

| 项目 | 内容 |
|------|------|
| 文档版本 | {doc_version} |
| 生成时间 | {timestamp} |
| 项目名称 | {project_name} |

---

## 1. 架构设计

### 1.1 总体架构
{architecture_overview}

### 1.2 架构图（文字描述）
{architecture_diagram}

### 1.3 技术选型
{architecture_tech_stack}

---

## 2. 模块设计

### 2.1 模块划分
{module_decomposition}

### 2.2 模块间依赖关系
{module_dependencies}

---

## 3. 接口设计

### 3.1 外部接口
{interfaces_external}

### 3.2 内部 API 接口
{interfaces_internal}

### 3.3 数据接口
{interfaces_data}

---

## 4. 数据库设计

### 4.1 数据模型
{database_model}

### 4.2 表结构设计
{database_tables}

### 4.3 索引与优化
{database_indexes}

---

## 5. 类设计

### 5.1 核心类图
{class_diagram}

### 5.2 关键类说明
{class_descriptions}

---

## 6. 部署设计

{deployment}

---

## 附录

{appendix}
""")

_DEFAULT_TEST_REPORT_TEMPLATE = dedent("""\
# 测试报告

| 项目 | 内容 |
|------|------|
| 报告版本 | {doc_version} |
| 生成时间 | {timestamp} |
| 项目名称 | {project_name} |
| 测试执行人 | {tester} |

---

## 1. 测试概述

### 1.1 测试目标
{test_objective}

### 1.2 测试范围
{test_scope}

### 1.3 测试环境
{test_environment}

---

## 2. 测试执行摘要

| 指标 | 数值 |
|------|------|
| 用例总数 | {total_cases} |
| 通过 | {passed} |
| 失败 | {failed} |
| 跳过 | {skipped} |
| 通过率 | {pass_rate} |

---

## 3. 测试结果详情

{test_details}

---

## 4. 缺陷汇总

{defects}

---

## 5. 结论与建议

{conclusion}
""")


# ═══════════════════════════════════════════════════════════════════
# 项目上下文（用于填充模板）
# ═══════════════════════════════════════════════════════════════════

def _build_project_context(project_name: str = "医保 DRG 入组智能体") -> dict:
    """收集项目运行上下文，用于填充文档模板占位符。"""
    import drg_agent

    pkg_dir = Path(drg_agent.__file__).resolve().parent
    rules_path = pkg_dir / "rules" / "sample_rules.json"
    rules_info: dict = {}
    if rules_path.is_file():
        try:
            rules = json.loads(rules_path.read_text(encoding="utf-8"))
            rules_info = {
                "rules_version": rules.get("version", "N/A"),
                "rules_desc": rules.get("description", "N/A"),
                "mdc_count": len(rules.get("mdc_rules", [])),
                "adrg_count": len(rules.get("adrg_rules", [])),
                "mcc_count": len(rules.get("mcc_list", [])),
                "cc_count": len(rules.get("cc_list", [])),
            }
        except Exception:
            rules_info = {"rules_version": "N/A"}

    # 收集引擎模块信息
    modules = [
        "drg_agent.agent (DRGAgent — 编排层)",
        "drg_agent.engine (GroupingEngine — 规则分组引擎)",
        "drg_agent.emr_parser (parse_emr_text — 病历解析)",
        "drg_agent.docgen (文档自动生成)",
        "drg_agent.testgen (测试用例生成)",
        "drg_web.app (FastAPI Web 服务)",
        "virtual_docs.server (虚拟文档存储)",
    ]

    return {
        "project_name": project_name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "author": os.environ.get("USER", os.environ.get("USERNAME", "开发团队")),
        "doc_version": "1.0",
        # 规则信息
        "rules_summary": json.dumps(rules_info, ensure_ascii=False, indent=2),
        "rules_version": rules_info.get("rules_version", "N/A"),
        "mdc_count": str(rules_info.get("mdc_count", "N/A")),
        "adrg_count": str(rules_info.get("adrg_count", "N/A")),
        "modules_list": "\n".join(f"- {m}" for m in modules),
    }


# ═══════════════════════════════════════════════════════════════════
# FR-012: SRS 文档生成器（IEEE 830）
# ═══════════════════════════════════════════════════════════════════

class SRSGenerator:
    """基于项目配置和运行数据，生成符合 IEEE 830 标准的 SRS 文档。"""

    def __init__(self, template: DocumentTemplate | None = None) -> None:
        self._tm = TemplateManager()
        self._tm.ensure_buildin()
        self._template = template or self._tm.get_template("srs_default")
        if self._template is None:
            self._template = self._tm.buildin_templates()[0]

    def generate(self, project_name: str = "医保 DRG 入组智能体") -> str:
        ctx = _build_project_context(project_name)

        # 动态填充功能需求部分
        functional_reqs = self._build_functional_requirements()
        nonfunctional = self._build_nonfunctional_requirements()
        analysis = self._build_analysis_model(ctx)

        placeholders = {
            "doc_version": "1.0",
            "timestamp": ctx["timestamp"],
            "project_name": ctx["project_name"],
            "author": ctx["author"],
            # 引言
            "introduction_purpose": (
                "本文档旨在完整描述医保 DRG 入组智能体系统的功能和非功能需求，"
                "作为后续设计、实现和测试的依据。该系统通过解析电子病历文本，"
                "基于 DRG 分组规则（教学样本）自动完成 MDC → ADRG → DRG 的入组推理，"
                "并支持大模型润色入组说明，为教学演示和 DRG 分组流程理解提供支撑。"
            ),
            "introduction_scope": (
                "系统范围涵盖：电子病历字段解析、规则驱动的 DRG 分组引擎、"
                "可选的大模型（通义千问 / OpenAI 兼容）说明润色、Web 交互界面、"
                "以及配套的文档自动生成与测试用例生成功能。"
                "当前规则文件为教学样本，非国家医保局正式发布的全量分组方案。"
            ),
            "introduction_terms": (
                "- **DRG**: Diagnosis Related Groups，疾病诊断相关分组\n"
                "- **MDC**: Major Diagnostic Category，主要诊断大类\n"
                "- **ADRG**: Adjacent Diagnosis Related Groups，核心疾病诊断相关组\n"
                "- **MCC**: Major Complication or Comorbidity，严重合并症或并发症\n"
                "- **CC**: Complication or Comorbidity，一般合并症或并发症\n"
                "- **ICD-10**: 国际疾病分类第10版\n"
                "- **EMR**: Electronic Medical Record，电子病历"
            ),
            "introduction_references": (
                "- 《按病组（DRG）付费分组方案（2.0版）》\n"
                "- IEEE Std 830-1998, Recommended Practice for Software Requirements Specifications\n"
                "- OpenAI API 文档 / 阿里云百炼 DashScope API 文档"
            ),
            "introduction_overview": (
                "本文档第2章给出系统综合描述，第3章阐述分析模型，"
                "第4章详列功能需求，第5章说明非功能需求。"
            ),
            # 综合描述
            "overall_product_perspective": (
                "本系统为独立运作的 Web 应用，由 Python FastAPI 后端 + 静态 HTML/CSS/JS 前端构成。"
                "后端通过 RESTful API 对外暴露服务，前端通过 AJAX 调用。"
                "可选依赖 OpenAI 兼容 API（阿里云百炼 DashScope 或 OpenAI）进行大模型增强。"
            ),
            "overall_product_functions": (
                "1. 电子病历解析：从中文病历文本中提取主要诊断、次要诊断、主要手术的 ICD 编码\n"
                "2. DRG 规则入组：依据规则 JSON 进行 MDC → ADRG → DRG 分组推理\n"
                "3. 大模型增强：调用 LLM 对入组推理结果进行自然语言润色说明\n"
                "4. 文档生成：自动生成 SRS、概要设计、测试报告\n"
                "5. 测试用例生成：基于规则文件自动生成测试场景"
            ),
            "overall_user_characteristics": (
                "目标用户为教学场景下的教师和学生，以及医保 DRG 分组方案的学习者。"
                "用户需具备基本的 ICD-10 编码知识和 DRG 分组概念。"
            ),
            "overall_constraints": (
                "- 规则文件为教学样本，不可用于实际医保结算\n"
                "- 大模型增强需要有效的 API Key（DashScope 或 OpenAI）\n"
                "- 系统运行在 Python 3.10+ 环境"
            ),
            "overall_assumptions": (
                "- 输入病历文本遵循约定格式（「主要诊断：」「主要手术：」等字段标记）\n"
                "- ICD 编码格式为字母开头（诊断）或数字开头（手术操作）\n"
                "- 规则 JSON 结构与 sample_rules.json 保持一致"
            ),
            # 分析模型
            "analysis_use_cases": analysis["use_cases"],
            "analysis_data_flow": analysis["data_flow"],
            "analysis_state_transition": analysis["state_transition"],
            # 功能需求
            "functional_requirements": functional_reqs,
            # 非功能需求
            "nonfunctional_performance": nonfunctional["performance"],
            "nonfunctional_security": nonfunctional["security"],
            "nonfunctional_usability": nonfunctional["usability"],
            "nonfunctional_maintainability": nonfunctional["maintainability"],
            "nonfunctional_portability": nonfunctional["portability"],
            "appendix": (
                f"### A. 规则文件摘要\n{ctx['rules_summary']}\n\n"
                f"### B. 项目模块清单\n{ctx['modules_list']}\n"
            ),
        }

        return self._template.content.format(**placeholders)

    def _build_functional_requirements(self) -> str:
        """动态生成功能需求章节。"""
        return dedent("""\
        ### FR-001: 电子病历解析
        **优先级**: P0
        **描述**: 系统应能从中文电子病历文本中解析出主要诊断编码、次要诊断编码列表和主要手术操作编码。
        **输入**: 中文病历文本（含「主要诊断：」「次要诊断：」「主要手术：」等标记）
        **输出**: ParsedEMR 数据结构

        ### FR-002: MDC 分组
        **优先级**: P0
        **描述**: 系统应基于主要诊断 ICD-10 编码，按规则文件中 mdc_rules 的 match_principal_icd 匹配 MDC 大类。
        **输入**: 主要诊断 ICD 编码
        **输出**: MDC 编码与名称

        ### FR-003: ADRG 分组
        **优先级**: P0
        **描述**: 在确定 MDC 后，根据主要手术编码（或内科路径）匹配 adrg_rules / adrg_medical_rules / adrg_medical_fallback。
        **输入**: MDC 编码 + 主要诊断 + 主要手术
        **输出**: ADRG 编码与名称

        ### FR-004: MCC/CC 判定
        **优先级**: P1
        **描述**: 遍历次要诊断列表，匹配 mcc_list 和 cc_list，同时应用主诊断排除表，判定 MCC/CC 命中情况。

        ### FR-005: DRG 细分
        **优先级**: P1
        **描述**: 结合 MCC/CC 命中情况，将 ADRG 细分为最终 DRG（如 BB11 / BB13 / BB15）。

        ### FR-006: 大模型润色（可选）
        **优先级**: P2
        **描述**: 当配置了 API Key 时，调用 LLM 对入组推理结果进行自然语言润色，生成更可读的说明文本。

        ### FR-012: SRS 文档自动生成
        **优先级**: P2
        **描述**: 系统应基于项目配置和运行数据，自动生成符合 IEEE 830 标准的软件需求规格说明书。

        ### FR-013: 设计文档自动生成
        **优先级**: P2
        **描述**: 系统应自动生成概要设计文档，包含架构设计、接口设计、数据库设计、类设计等内容。

        ### FR-014: 测试报告自动生成
        **优先级**: P2
        **描述**: 系统应基于测试用例执行结果，自动生成测试报告。

        ### FR-015: 文档模板管理
        **优先级**: P3
        **描述**: 系统应支持用户自定义或修改文档生成模板（JSON 格式存储，支持 CRUD）。

        ### FR-016: 文档预览与手动修订
        **优先级**: P2
        **描述**: 文档生成后，用户应能够预览内容并进行手动修订，修订完成后重新生成最终版本。

        ### FR-017: 测试用例自动生成
        **优先级**: P2
        **描述**: 系统应基于 DRG 入组规则文件，自动生成覆盖正常入组、边界情况和异常处理的测试用例集。

        ### FR-018: 测试用例分类
        **优先级**: P2
        **描述**: 系统应按功能模块和优先级对测试用例进行分类组织。

        ### FR-019: 测试用例执行
        **优先级**: P2
        **描述**: 系统应支持自动执行测试用例，并与预期结果进行比对。

        ### FR-020: 测试用例导出
        **优先级**: P3
        **描述**: 系统应支持将测试用例导出为 JSON 格式，便于外部测试工具集成。
        """)

    def _build_nonfunctional_requirements(self) -> dict:
        return {
            "performance": (
                "- 单次 DRG 入组请求响应时间应在 2 秒以内（不含 LLM 调用）\n"
                "- LLM 增强请求额外超时设置为 30 秒\n"
                "- Web 界面应支持至少 10 个并发用户"
            ),
            "security": (
                "- LLM API Key 通过环境变量注入，不硬编码在代码中\n"
                "- 输入病历文本不持久化存储（会话级别处理）\n"
                "- CORS 配置在演示环境允许所有来源"
            ),
            "usability": (
                "- Web 界面提供中文本地化\n"
                "- 示例病历一键加载\n"
                "- 错误信息清晰可读，包含具体原因和解决建议"
            ),
            "maintainability": (
                "- 模块化设计：emr_parser / engine / agent 解耦\n"
                "- 规则 JSON 独立于代码，支持热替换\n"
                "- 完整单元测试覆盖核心入组路径"
            ),
            "portability": (
                "- 纯 Python 实现，跨平台（Windows / Linux / macOS）\n"
                "- 依赖通过在 requirements.txt 中声明\n"
                "- 前端仅使用标准 HTML/CSS/JS，无框架依赖"
            ),
        }

    def _build_analysis_model(self, ctx: dict) -> dict:
        return {
            "use_cases": (
                "**UC-1**: 课件实例入组 —— 用户粘贴 slide6 病历，系统输出 BB11 DRG 分组\n"
                "**UC-2**: 无 MCC 入组 —— 相同主诊断+手术，但无次要诊断 → BB15\n"
                "**UC-3**: 大模型润色 —— 用户勾选「允许大模型」，系统调用 LLM 生成自然语言说明\n"
                "**UC-4**: 文档生成 —— 用户在 Web 界面点击生成 SRS / 设计文档 / 测试报告\n"
                "**UC-5**: 测试用例管理 —— 生成、执行、导出测试用例"
            ),
            "data_flow": (
                "```\n"
                "病历文本 → EMR 解析 (emr_parser) → GroupingInput\n"
                "  → GroupingEngine.group() → GroupingResult\n"
                "  → (可选) LLM 润色 → 最终说明文本\n"
                "  → JSON 响应 → Web 前端渲染\n"
                "```"
            ),
            "state_transition": (
                "DRG 入组状态流转：\n"
                "INPUT_RECEIVED → PARSING → MDC_MATCHED → ADRG_MATCHED\n"
                "  → CC_MCC_EVALUATED → DRG_FINALIZED → NARRATIVE_GENERATED\n"
                "异常路径：PARSING_FAILED / MDC_UNKNOWN / ADRG_UNKNOWN → ERROR_RESPONSE"
            ),
        }


# ═══════════════════════════════════════════════════════════════════
# FR-013: 设计文档生成器
# ═══════════════════════════════════════════════════════════════════

class DesignDocGenerator:
    """生成概要设计文档：架构、接口、数据库、类设计。"""

    def __init__(self, template: DocumentTemplate | None = None) -> None:
        self._tm = TemplateManager()
        self._tm.ensure_buildin()
        self._template = template or self._tm.get_template("design_default")
        if self._template is None:
            self._template = self._tm.buildin_templates()[1]

    def generate(self, project_name: str = "医保 DRG 入组智能体") -> str:
        ctx = _build_project_context(project_name)

        placeholders = {
            "doc_version": "1.0",
            "timestamp": ctx["timestamp"],
            "project_name": ctx["project_name"],
            "architecture_overview": (
                "系统采用分层架构：\n\n"
                "- **表示层**: 静态 HTML/CSS/JS 单页应用，通过 AJAX 与后端通信\n"
                "- **应用层**: FastAPI Web 服务，提供 RESTful API，编排 DRG 入组流程\n"
                "- **领域层**: DRG 分组引擎（engine.py）+ 病历解析（emr_parser.py）+ 智能体编排（agent.py）\n"
                "- **基础设施层**: 规则 JSON 文件存储、LLM API 适配器、虚拟文档存储系统\n\n"
                "跨层关注点：日志、异常处理、CORS 中间件。"
            ),
            "architecture_diagram": (
                "```\n"
                "┌─────────────────────────────────┐\n"
                "│   index.html (浏览器)           │\n"
                "│   AJAX fetch → REST API         │\n"
                "└─────────────┬───────────────────┘\n"
                "              │ HTTP\n"
                "┌─────────────▼───────────────────┐\n"
                "│   FastAPI (drg_web/app.py)      │\n"
                "│   /api/group, /api/docs/*,      │\n"
                "│   /api/tests/*, /api/health     │\n"
                "└─────────────┬───────────────────┘\n"
                "              │\n"
                "┌─────────────▼───────────────────┐\n"
                "│   DRGAgent (drg_agent/agent.py) │\n"
                "│   ├─ parse_emr_text()           │\n"
                "│   ├─ GroupingEngine.group()     │\n"
                "│   └─ LLM enhance (optional)     │\n"
                "└─────────────┬───────────────────┘\n"
                "              │\n"
                "┌─────────────▼───────────────────┐\n"
                "│   规则 JSON + 大模型 API        │\n"
                "└─────────────────────────────────┘\n"
                "```"
            ),
            "architecture_tech_stack": (
                "- **后端**: Python 3.10+, FastAPI, Uvicorn, Pydantic\n"
                "- **前端**: 原生 HTML5/CSS3/JavaScript (ES5, 零框架依赖)\n"
                "- **规则存储**: JSON 文件\n"
                "- **LLM SDK**: openai >= 1.40.0（OpenAI 兼容接口）\n"
                "- **测试框架**: pytest >= 7.0\n"
                "- **文档格式**: Markdown / Plain Text"
            ),
            "module_decomposition": (
                "| 模块 | 文件 | 职责 |\n"
                "|------|------|------|\n"
                "| EMR 解析 | emr_parser.py | 从中文病历提取 ICD 编码 |\n"
                "| 规则引擎 | engine.py | MDC→ADRG→DRG 分组编排 |\n"
                "| 智能体编排 | agent.py | 串联解析+分组+LLM 增强 |\n"
                "| 文档生成 | docgen.py | SRS/设计/测试报告自动生成 |\n"
                "| 测试生成 | testgen.py | 测试用例生成/执行/导出 |\n"
                "| Web 服务 | app.py | FastAPI RESTful API |\n"
                "| CLI 工具 | cli.py | 命令行交互入口 |\n"
                "| 虚拟文档 | server.py | 文档落盘与存储 |"
            ),
            "module_dependencies": (
                "```\n"
                "drg_web/app.py\n"
                "  → drg_agent.agent.DRGAgent\n"
                "    → drg_agent.emr_parser.parse_emr_text\n"
                "    → drg_agent.engine.GroupingEngine\n"
                "      → drg_agent/rules/sample_rules.json\n"
                "    → openai (可选)\n"
                "  → drg_agent.docgen.*\n"
                "  → drg_agent.testgen.*\n"
                "```"
            ),
            "interfaces_external": (
                "- **OpenAI 兼容 API**: POST {base_url}/chat/completions，用于 LLM 润色\n"
                "  - base_url 默认 https://dashscope.aliyuncs.com/compatible-mode/v1\n"
                "  - 认证：Bearer Token (API Key)\n"
                "- **虚拟文档系统**: POST /submit，用于文档持久化存储\n"
                "  - 参数：file (multipart), source_agent, note"
            ),
            "interfaces_internal": (
                "| 接口 | 方法 | 路径 | 说明 |\n"
                "|------|------|------|------|\n"
                "| 入组分析 | POST | /api/group | 提交病历，返回 DRG 入组结果 |\n"
                "| 示例病历 | GET | /api/example-emr | 获取课件示例病历 |\n"
                "| SRS 生成 | POST | /api/docs/srs | 生成 SRS 文档 |\n"
                "| 设计文档 | POST | /api/docs/design | 生成设计文档 |\n"
                "| 测试报告 | POST | /api/docs/test-report | 生成测试报告 |\n"
                "| 模板列表 | GET | /api/docs/templates | 列出文档模板 |\n"
                "| 模板保存 | POST | /api/docs/templates | 保存/更新模板 |\n"
                "| 模板删除 | DELETE | /api/docs/templates/{name} | 删除模板 |\n"
                "| 测试生成 | POST | /api/tests/generate | 生成测试用例 |\n"
                "| 测试执行 | POST | /api/tests/execute | 执行测试用例 |\n"
                "| 测试导出 | GET | /api/tests/export | 导出测试用例 JSON |\n"
                "| 健康检查 | GET | /api/health | 服务健康检查 |"
            ),
            "interfaces_data": (
                "**GroupRequest** (入组请求):\n"
                "- emr_text: str (必填) — 病历文本\n"
                "- use_llm: bool (默认 true) — 是否启用大模型\n\n"
                "**GroupResponse** (入组响应):\n"
                "- ok: bool\n"
                "- grouping: { mdc_code, mdc_name, adrg_code, adrg_name, drg_code, drg_name, mcc_hits, cc_hits, reason_steps }\n"
                "- narrative: str"
            ),
            "database_model": (
                "本系统当前不依赖关系数据库。数据存储方案：\n"
                "- **规则数据**: JSON 文件（drg_agent/rules/）\n"
                "- **文档模板**: JSON 文件（drg_agent/templates/）\n"
                "- **生成文档**: 虚拟文档系统（virtual_docs/storage/）\n"
                "- **环境配置**: 环境变量（API Key 等）"
            ),
            "database_tables": (
                "不适用（无数据库）。若未来需要持久化入组历史，建议 SQLite 表设计：\n\n"
                "```sql\n"
                "CREATE TABLE grouping_history (\n"
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
                "  emr_text TEXT NOT NULL,\n"
                "  drg_code TEXT,\n"
                "  mdc_code TEXT,\n"
                "  adrg_code TEXT,\n"
                "  narrative TEXT,\n"
                "  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
                ");\n"
                "```"
            ),
            "database_indexes": (
                "若引入 SQLite：\n"
                "- idx_drg_code ON grouping_history(drg_code)\n"
                "- idx_created_at ON grouping_history(created_at)"
            ),
            "class_diagram": (
                "```\n"
                "ParsedEMR (dataclass)\n"
                "  + principal_diagnosis_code: str\n"
                "  + secondary_diagnosis_codes: list[str]\n"
                "  + principal_procedure_code: str\n\n"
                "GroupingInput (dataclass)\n"
                "  + principal_icd: str\n"
                "  + secondary_icds: list[str]\n"
                "  + principal_procedure_icd: str\n\n"
                "GroupingResult (dataclass)\n"
                "  + mdc_code, adrg_code, drg_code\n"
                "  + mcc_hits, cc_hits, reason_steps\n\n"
                "GroupingEngine\n"
                "  + group(GroupingInput) → GroupingResult\n"
                "  - _resolve_mdc / _resolve_adrg / _resolve_cc_mcc / _resolve_fine_drg\n\n"
                "DRGAgent\n"
                "  + run(emr_text) → AgentReport\n"
                "  - _default_narrative / _llm_enhance\n\n"
                "SRSGenerator / DesignDocGenerator / TestReportGenerator\n"
                "  + generate(project_name) → str\n\n"
                "TestCaseGenerator / TestCaseRunner / TestCaseExporter\n"
                "```"
            ),
            "class_descriptions": (
                "**GroupingEngine**: 核心规则引擎，接收 GroupingInput，按规则 JSON 分层匹配，输出 GroupingResult。\n\n"
                "**DRGAgent**: 编排层，串联 解析 → 分组 →（可选）LLM 润色，统一返回 AgentReport。\n\n"
                "**SRSGenerator / DesignDocGenerator / TestReportGenerator**: 文档生成器，基于模板和项目上下文填充生成 Markdown 文档。\n\n"
                "**TestCaseGenerator / TestCaseRunner / TestCaseExporter**: 测试用例全生命周期管理。"
            ),
            "deployment": (
                "### 本地开发部署\n"
                "```bash\n"
                "pip install -r requirements.txt\n"
                "python -m drg_web\n"
                "# 访问 http://127.0.0.1:8765\n"
                "```\n\n"
                "### 环境变量\n"
                "- `DASHSCOPE_API_KEY`: 阿里云百炼 API Key\n"
                "- `OPENAI_API_KEY` / `OPENAI_BASE_URL`: OpenAI 兼容配置\n"
                "- `OPENAI_MODEL`: 模型名称（默认 qwen3-max / gpt-4o-mini）"
            ),
            "appendix": ctx["modules_list"],
        }

        return self._template.content.format(**placeholders)


# ═══════════════════════════════════════════════════════════════════
# FR-014: 测试报告生成器
# ═══════════════════════════════════════════════════════════════════

class TestReportGenerator:
    """基于测试执行结果生成测试报告。"""

    def __init__(self, template: DocumentTemplate | None = None) -> None:
        self._tm = TemplateManager()
        self._tm.ensure_buildin()
        self._template = template or self._tm.get_template("test_report_default")
        if self._template is None:
            self._template = self._tm.buildin_templates()[2]

    def generate(
        self,
        test_results: list[dict],
        project_name: str = "医保 DRG 入组智能体",
    ) -> str:
        ctx = _build_project_context(project_name)
        total = len(test_results)
        passed = sum(1 for r in test_results if r.get("passed"))
        failed = sum(1 for r in test_results if not r.get("passed") and not r.get("skipped"))
        skipped = sum(1 for r in test_results if r.get("skipped"))
        pass_rate = f"{passed / total * 100:.1f}%" if total > 0 else "N/A"

        # 构建测试详情
        detail_lines = []
        for i, r in enumerate(test_results, 1):
            status_icon = "✅" if r.get("passed") else "⏭️" if r.get("skipped") else "❌"
            detail_lines.append(
                f"### {status_icon} 用例 {i}: {r.get('title', '未命名')}\n\n"
                f"- **分类**: {r.get('category', 'N/A')} | **优先级**: {r.get('priority', 'N/A')} | **模块**: {r.get('module', 'N/A')}\n"
                f"- **输入**: {json.dumps(r.get('input', {}), ensure_ascii=False)}\n"
                f"- **预期**: {json.dumps(r.get('expected', {}), ensure_ascii=False)}\n"
                f"- **实际**: {json.dumps(r.get('actual', {}), ensure_ascii=False)}\n"
                f"- **耗时**: {r.get('duration_ms', 'N/A')} ms\n"
                f"- **错误**: {r.get('error', '无')}\n"
            )

        # 缺陷汇总
        defect_lines = []
        for r in test_results:
            if not r.get("passed") and not r.get("skipped"):
                defect_lines.append(
                    f"- **{r.get('title', '未命名')}**: {r.get('error', '未知错误')}"
                )

        placeholders = {
            "doc_version": "1.0",
            "timestamp": ctx["timestamp"],
            "project_name": ctx["project_name"],
            "tester": ctx["author"],
            "test_objective": (
                "验证 DRG 入组智能体核心引擎在正常、边界和异常场景下的分组结果正确性，"
                "确保规则引擎按预期执行 MDC → ADRG → DRG 推理链。"
            ),
            "test_scope": (
                "- 核心引擎：GroupingEngine.group() 分组正确性\n"
                "- 病历解析：parse_emr_text() 字段提取准确性\n"
                "- 规则匹配：MDC / ADRG / MCC / CC / DRG 各层规则覆盖\n"
                "- 排除逻辑：主诊断排除表（mcc_exclusions_by_principal）\n"
                "- 边界行为：UNKNOWN 兜底路径"
            ),
            "test_environment": (
                f"- Python: {__import__('sys').version}\n"
                f"- 规则版本: {ctx['rules_version']}\n"
                f"- 测试时间: {ctx['timestamp']}\n"
                f"- 平台: {__import__('sys').platform}"
            ),
            "total_cases": str(total),
            "passed": str(passed),
            "failed": str(failed),
            "skipped": str(skipped),
            "pass_rate": pass_rate,
            "test_details": "\n".join(detail_lines) if detail_lines else "无测试结果。",
            "defects": "\n".join(defect_lines) if defect_lines else "无缺陷。",
            "conclusion": (
                f"本次测试共执行 {total} 个用例，通过 {passed} 个，失败 {failed} 个，通过率 {pass_rate}。\n\n"
                + ("所有用例通过，系统功能正常。✅"
                   if failed == 0 else
                   f"存在 {failed} 个失败用例，建议优先排查并修复后再进行回归测试。")
            ),
        }

        return self._template.content.format(**placeholders)


# ═══════════════════════════════════════════════════════════════════
# FR-016: 文档预览与修订接口
# ═══════════════════════════════════════════════════════════════════

def preview_document(content: str) -> dict:
    """返回文档预览数据。"""
    return {
        "content": content,
        "lines": len(content.splitlines()),
        "chars": len(content),
        "preview": content[:500] + ("..." if len(content) > 500 else ""),
    }


def revise_document(original: str, edits: list[dict]) -> str:
    """将修订应用到文档。edits: [{"line": N, "new_text": "..."}]"""
    lines = original.splitlines()
    for edit in edits:
        idx = edit.get("line", -1)
        if 0 <= idx < len(lines):
            lines[idx] = edit.get("new_text", lines[idx])
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# AI 增强：调用 LLM 提升文档质量
# ═══════════════════════════════════════════════════════════════════

# 复用 agent.py 的 LLM 环境解析逻辑
def _resolve_llm_config() -> tuple[str | None, str | None, str]:
    """返回 (base_url, api_key, model)。"""
    from drg_agent.agent import resolve_llm_env, resolve_llm_model

    base, key = resolve_llm_env(None, None)
    return base, key, resolve_llm_model()


def _is_llm_available() -> bool:
    base, key, _ = _resolve_llm_config()
    return bool(base and key)


def _llm_chat(system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str | None:
    """调用 OpenAI 兼容 LLM，失败时返回 None。"""
    try:
        from openai import OpenAI

        base, key, model = _resolve_llm_config()
        if not base or not key:
            return None
        base_url = base.rstrip("/")
        client = OpenAI(api_key=key, base_url=base_url)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "stream": False,
        }
        if "dashscope.aliyuncs.com" in base_url.lower():
            kwargs["extra_body"] = {"enable_thinking": os.environ.get("DASHSCOPE_ENABLE_THINKING", "").lower().strip() in ("1", "true", "yes", "on")}
        completion = client.chat.completions.create(**kwargs)
        text = (completion.choices[0].message.content or "").strip()
        return text if text else None
    except Exception:
        return None


class LLMDocEnhancer:
    """使用 LLM 增强文档内容质量。

    策略：
    - LLM 可用时：用模板生成骨架，再用 LLM 对关键章节做深度展开
    - LLM 不可用时：完全走模板（无感降级）
    """

    @staticmethod
    def enhance_srs(template_content: str, project_name: str) -> str:
        """将 SRS 骨架交由 LLM 改写为更专业、更详尽的 IEEE 830 文档。"""
        if not _is_llm_available():
            return template_content

        system = (
            "你是一位高级软件架构师和需求分析专家。请将下面这份软件需求规格说明书（SRS）骨架，"
            "改写为一份专业、详尽、符合 IEEE 830 标准的正式文档。要求：\n"
            "1. 保持原有章节结构（1-5 章 + 附录）\n"
            "2. 每个章节扩充更多实质性内容，增加具体细节\n"
            "3. 功能需求部分要使用「系统应…」的规范表述\n"
            "4. 补充更详细的用例描述、前置条件、后置条件\n"
            "5. 语言使用中文，专业术语保留英文缩写\n"
            "6. 保持 Markdown 格式输出"
        )
        user = (
            f"项目名称：{project_name}\n\n"
            f"以下是当前 SRS 骨架文档，请在此基础上做专业级改写：\n\n"
            f"{template_content}"
        )

        enhanced = _llm_chat(system, user, temperature=0.3)
        return enhanced if enhanced else template_content

    @staticmethod
    def enhance_design(template_content: str, project_name: str) -> str:
        """将设计文档骨架交由 LLM 改写为更详尽的技术文档。"""
        if not _is_llm_available():
            return template_content

        system = (
            "你是一位资深系统架构师。请将下面这份概要设计文档骨架，"
            "改写为一份专业的技术设计文档。要求：\n"
            "1. 保持原有章节结构\n"
            "2. 对架构设计部分补充设计决策的理由（trade-off 分析）\n"
            "3. 接口设计部分要给出更具体的 API 规格（请求/响应示例）\n"
            "4. 类设计部分补充关键方法的伪代码或时序说明\n"
            "5. 语言使用中文，专业术语保留英文\n"
            "6. 保持 Markdown 格式输出"
        )
        user = (
            f"项目名称：{project_name}\n\n"
            f"以下是当前概要设计骨架文档，请在此基础上做专业级改写：\n\n"
            f"{template_content}"
        )

        enhanced = _llm_chat(system, user, temperature=0.3)
        return enhanced if enhanced else template_content

    @staticmethod
    def enhance_test_report(template_content: str, test_summary: dict) -> str:
        """使用 LLM 对测试报告做智能分析，补充根因分析和改进建议。"""
        if not _is_llm_available():
            return template_content

        system = (
            "你是一位资深测试工程师。请将下面这份测试报告进行专业改写。要求：\n"
            "1. 保持原有章节结构\n"
            "2. 对测试结果做深入分析，给出每个失败用例的根因推测\n"
            "3. 补充测试覆盖度分析和改进建议\n"
            "4. 结论部分要给出明确的质量评估和发布建议\n"
            "5. 语言使用中文\n"
            "6. 保持 Markdown 格式输出"
        )
        user = (
            f"测试结果摘要：{json.dumps(test_summary, ensure_ascii=False)}\n\n"
            f"以下是当前测试报告骨架，请在此基础上做专业级改写：\n\n"
            f"{template_content}"
        )

        enhanced = _llm_chat(system, user, temperature=0.3)
        return enhanced if enhanced else template_content

    @staticmethod
    def generate_custom_section(prompt: str, context: str = "") -> str | None:
        """自由内容生成：用户自定义 prompt，LLM 返回文档片段。"""
        if not _is_llm_available():
            return None
        system = "你是一个专业的软件工程文档撰写助手，输出使用中文、Markdown 格式。"
        full_user = f"项目上下文：\n{context}\n\n用户要求：\n{prompt}" if context else prompt
        return _llm_chat(system, full_user, temperature=0.4)


# ═══════════════════════════════════════════════════════════════════
# 更新后的生成器 — 集成 LLM
# ═══════════════════════════════════════════════════════════════════

class AI_SRSGenerator(SRSGenerator):
    """SRS 生成器 + AI 增强。"""

    def generate(self, project_name: str = "医保 DRG 入组智能体", use_llm: bool = True) -> str:
        base = super().generate(project_name)
        if use_llm and _is_llm_available():
            return LLMDocEnhancer.enhance_srs(base, project_name)
        return base


class AI_DesignDocGenerator(DesignDocGenerator):
    """设计文档生成器 + AI 增强。"""

    def generate(self, project_name: str = "医保 DRG 入组智能体", use_llm: bool = True) -> str:
        base = super().generate(project_name)
        if use_llm and _is_llm_available():
            return LLMDocEnhancer.enhance_design(base, project_name)
        return base


class AI_TestReportGenerator(TestReportGenerator):
    """测试报告生成器 + AI 增强。"""

    def generate(
        self,
        test_results: list[dict],
        project_name: str = "医保 DRG 入组智能体",
        use_llm: bool = True,
    ) -> str:
        base = super().generate(test_results, project_name)
        if use_llm and _is_llm_available() and test_results:
            summary = {
                "total": len(test_results),
                "passed": sum(1 for r in test_results if r.get("passed")),
                "failed": sum(1 for r in test_results if not r.get("passed") and not r.get("skipped")),
            }
            return LLMDocEnhancer.enhance_test_report(base, summary)
        return base


# ═══════════════════════════════════════════════════════════════════
# 便捷入口
# ═══════════════════════════════════════════════════════════════════

def generate_all_docs(project_name: str = "医保 DRG 入组智能体", use_llm: bool = False) -> dict:
    """一次性生成三类文档（SRS + 设计 + 测试报告骨架），可选 AI 增强。"""
    tm = TemplateManager()
    tm.ensure_buildin()
    srs_gen = AI_SRSGenerator() if use_llm else SRSGenerator()
    design_gen = AI_DesignDocGenerator() if use_llm else DesignDocGenerator()
    return {
        "srs": srs_gen.generate(project_name, use_llm=use_llm) if use_llm else srs_gen.generate(project_name),
        "design": design_gen.generate(project_name, use_llm=use_llm) if use_llm else design_gen.generate(project_name),
        "test_report": TestReportGenerator().generate([]),
    }
