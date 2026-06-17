# -*- coding: utf-8 -*-
"""测试用例生成智能体：生成 / 分类 / 执行 / 导出。"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent
from typing import Any

from drg_agent.engine import GroupingEngine, GroupingInput


# ═══════════════════════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════════════════════

@dataclass
class TestCase:
    id: str
    title: str
    category: str  # "normal" | "boundary" | "exception"
    priority: str  # "P0" | "P1" | "P2" | "P3"
    module: str  # "engine" | "parser" | "agent"
    description: str
    input: dict  # GroupingInput 可序列化形式
    expected: dict  # 预期 GroupingResult 字段
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "priority": self.priority,
            "module": self.module,
            "description": self.description,
            "input": self.input,
            "expected": self.expected,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TestCase":
        return cls(
            id=d["id"],
            title=d["title"],
            category=d["category"],
            priority=d["priority"],
            module=d["module"],
            description=d["description"],
            input=d["input"],
            expected=d["expected"],
            tags=d.get("tags", []),
        )


@dataclass
class TestResult:
    case_id: str
    title: str
    category: str
    priority: str
    module: str
    input: dict
    expected: dict
    actual: dict
    passed: bool
    error: str = ""
    duration_ms: float = 0.0
    skipped: bool = False

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "title": self.title,
            "category": self.category,
            "priority": self.priority,
            "module": self.module,
            "input": self.input,
            "expected": self.expected,
            "actual": self.actual,
            "passed": self.passed,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "skipped": self.skipped,
        }


# ═══════════════════════════════════════════════════════════════════
# FR-017: 测试用例自动生成
# ═══════════════════════════════════════════════════════════════════

class TestCaseGenerator:
    """基于 DRG 入组规则文件自动生成测试用例集。"""

    def __init__(self, rules_path: Path | None = None) -> None:
        self._engine = GroupingEngine(rules_path)
        base = Path(__file__).resolve().parent / "rules" / "sample_rules.json"
        self._rules_path = rules_path or base
        self._rules = json.loads(self._rules_path.read_text(encoding="utf-8"))

    def generate(self) -> list[TestCase]:
        """生成覆盖正常、边界、异常三类场景的测试用例。"""
        cases: list[TestCase] = []
        idx = 0

        # ── 正常场景 ──────────────────────────────────────────
        normal_cases = self._generate_normal_cases()
        for c in normal_cases:
            idx += 1
            c.id = f"TC-N{idx:03d}"
            cases.append(c)

        # ── 边界场景 ──────────────────────────────────────────
        boundary_cases = self._generate_boundary_cases()
        for c in boundary_cases:
            idx += 1
            c.id = f"TC-B{idx:03d}"
            cases.append(c)

        # ── 异常场景 ──────────────────────────────────────────
        exception_cases = self._generate_exception_cases()
        for c in exception_cases:
            idx += 1
            c.id = f"TC-E{idx:03d}"
            cases.append(c)

        return cases

    def _generate_normal_cases(self) -> list[TestCase]:
        """正常入组场景：预期规则命中并得到确定的 DRG 编码。"""
        cases: list[TestCase] = []

        # N1: slide6 课件实例 — BB11 (有 MCC)
        cases.append(TestCase(
            id="", title="课件实例 — 伤寒脑膜炎+呼吸衰竭 → BB11",
            category="normal", priority="P0", module="engine",
            description="主诊断 A01.002+G01*（伤寒性脑膜炎），次要 J96.0（呼吸衰竭），手术 38.1000x002 → BB11",
            input={
                "principal_icd": "A01.002+G01*",
                "secondary_icds": ["J96.0"],
                "principal_procedure_icd": "38.1000x002",
            },
            expected={"mdc_code": "MDCB", "adrg_code": "BB1", "drg_code": "BB11", "has_mcc": True},
            tags=["slide6", "MCC", "神经系统"],
        ))

        # N2: 无次要诊断 → BB15
        cases.append(TestCase(
            id="", title="课件实例 — 无合并症 → BB15",
            category="normal", priority="P0", module="engine",
            description="主诊断 A01.002+G01*，手术 38.1000x002，无次要诊断 → BB15",
            input={
                "principal_icd": "A01.002+G01*",
                "secondary_icds": [],
                "principal_procedure_icd": "38.1000x002",
            },
            expected={"mdc_code": "MDCB", "adrg_code": "BB1", "drg_code": "BB15", "has_mcc": False},
            tags=["slide6", "无MCC", "神经系统"],
        ))

        # N3: case5 股骨颈骨折 + 骨质疏松 → IF13 (CC)
        cases.append(TestCase(
            id="", title="股骨颈骨折+骨质疏松 → IF13",
            category="normal", priority="P0", module="engine",
            description="主诊断 S72.000（股骨颈骨折），次要 M81.000（骨质疏松），手术 79.3500x001 → IF13",
            input={
                "principal_icd": "S72.000",
                "secondary_icds": ["M81.000"],
                "principal_procedure_icd": "79.3500x001",
            },
            expected={"mdc_code": "MDCI", "adrg_code": "IF1", "drg_code": "IF13", "has_cc": True},
            tags=["case5", "CC", "骨科"],
        ))

        # N4: 肺炎无手术 — 内科路径 EM05
        cases.append(TestCase(
            id="", title="肺炎无手术 — 内科路径 EM05",
            category="normal", priority="P1", module="engine",
            description="主诊断 J18.901（肺炎），无手术 → MDCE/EM0/EM05",
            input={
                "principal_icd": "J18.901",
                "secondary_icds": [],
                "principal_procedure_icd": None,
            },
            expected={"mdc_code": "MDCE", "adrg_code": "EM0", "drg_code": "EM05"},
            tags=["内科", "呼吸"],
        ))

        # N5: 手术不命中专科表但命中 catch-all → BS91
        cases.append(TestCase(
            id="", title="手术不命中专科 → catch-all BS91",
            category="normal", priority="P1", module="engine",
            description="主诊断 A01.002+G01*，次要 J96.0，手术 38.9999（不在专科表）→ BS9/BS91",
            input={
                "principal_icd": "A01.002+G01*",
                "secondary_icds": ["J96.0"],
                "principal_procedure_icd": "38.9999",
            },
            expected={"mdc_code": "MDCB", "adrg_code": "BS9", "drg_code": "BS91", "has_mcc": True},
            tags=["catch-all", "MCC"],
        ))

        return cases

    def _generate_boundary_cases(self) -> list[TestCase]:
        """边界场景：恰好在规则边缘的情况。"""
        cases: list[TestCase] = []

        # B1: 次要诊断存在但不在 MCC 列表（如仅高血压 I10）
        cases.append(TestCase(
            id="", title="仅 CC 无 MCC — 高血压 → BB13",
            category="boundary", priority="P1", module="engine",
            description="次要诊断仅有 I10（高血压，属于 CC 非 MCC），预期命中 BB13（伴一般合并症）",
            input={
                "principal_icd": "A01.002+G01*",
                "secondary_icds": ["I10"],
                "principal_procedure_icd": "38.1000x002",
            },
            expected={"mdc_code": "MDCB", "adrg_code": "BB1", "drg_code": "BB13", "has_cc": True, "has_mcc": False},
            tags=["边界", "CC-only"],
        ))

        # B2: 既有 MCC 又有 CC
        cases.append(TestCase(
            id="", title="MCC+CC 同时存在 — 优先 MCC → BB11",
            category="boundary", priority="P1", module="engine",
            description="MCC (J96.0) 和 CC (I10) 同时命中，MCC 优先 → BB11",
            input={
                "principal_icd": "A01.002+G01*",
                "secondary_icds": ["J96.0", "I10"],
                "principal_procedure_icd": "38.1000x002",
            },
            expected={"mdc_code": "MDCB", "adrg_code": "BB1", "drg_code": "BB11", "has_mcc": True},
            tags=["边界", "MCC+CC"],
        ))

        # B3: 手术为空但内科路径需要手术
        cases.append(TestCase(
            id="", title="有手术但内科 fallback 不要求手术",
            category="boundary", priority="P2", module="engine",
            description="主诊断 A01.002+G01* 在 MDCB，不提供手术，走内科 fallback BM0",
            input={
                "principal_icd": "A01.002+G01*",
                "secondary_icds": [],
                "principal_procedure_icd": None,
            },
            expected={"mdc_code": "MDCB", "adrg_code": "BM0", "drg_code": "BM05"},
            tags=["内科fallback"],
        ))

        # B4: 次要诊断匹配 MCC 但被排除表过滤
        # (当前排除表为空，此用例验证排除逻辑路径)
        cases.append(TestCase(
            id="", title="MCC 候选但通过排除表检查（空排除表）",
            category="boundary", priority="P2", module="engine",
            description="验证 mcc_exclusions_by_principal 为空时所有 MCC 都能命中",
            input={
                "principal_icd": "A01.002+G01*",
                "secondary_icds": ["J96.0", "I50"],
                "principal_procedure_icd": "38.1000x002",
            },
            expected={"mdc_code": "MDCB", "adrg_code": "BB1", "drg_code": "BB11", "has_mcc": True},
            tags=["排除表", "多MCC"],
        ))

        return cases

    def _generate_exception_cases(self) -> list[TestCase]:
        """异常场景：预期系统能妥善处理异常输入。"""
        cases: list[TestCase] = []

        # E1: 主要诊断格式错误 — 无有效 ICD-10 编码，走兜底规则
        cases.append(TestCase(
            id="", title="无法解析的主要诊断编码 — 走兜底",
            category="exception", priority="P1", module="parser",
            description="主要诊断 'XXXXX' 不是标准 ICD-10 编码，命中通配规则 mdc-fallback-any → MDCS / SM0",
            input={
                "principal_icd": "XXXXX",
                "secondary_icds": [],
                "principal_procedure_icd": None,
            },
            expected={"mdc_code": "MDCS"},
            tags=["异常", "解析失败", "兜底"],
        ))

        # E2: 不匹配任何 MDC 规则的 ICD
        cases.append(TestCase(
            id="", title="ICD 不匹配任何 MDC → UNKNOWN",
            category="exception", priority="P1", module="engine",
            description="编码 U99.0 不匹配任何 mdc_rules（U 类归 MDCR 兜底）→ 实际上会走 fallback",
            input={
                "principal_icd": "U99.0",
                "secondary_icds": [],
                "principal_procedure_icd": None,
            },
            expected={"mdc_code": "MDCR"},
            tags=["兜底", "fallback"],
        ))

        # E3: 手术编码格式异常 — 不匹配专科手术，走 catch-all 手术桶
        cases.append(TestCase(
            id="", title="畸形手术编码 — 走 catch-all 手术桶",
            category="exception", priority="P2", module="engine",
            description="手术编码 'ABC' 不匹配任何专科手术，走综合手术 catch-all BS9",
            input={
                "principal_icd": "A01.002+G01*",
                "secondary_icds": [],
                "principal_procedure_icd": "ABC",
            },
            expected={"mdc_code": "MDCB", "adrg_code": "BS9"},
            tags=["畸形编码", "catch-all"],
        ))

        # E4: 空输入（次要诊断列表为空 + 无手术）
        cases.append(TestCase(
            id="", title="极简输入 — 仅主诊断无手术无次要",
            category="exception", priority="P2", module="engine",
            description="仅提供主诊断 A01.002+G01*，无手术无次要 → 内科 fallback BM05",
            input={
                "principal_icd": "A01.002+G01*",
                "secondary_icds": [],
                "principal_procedure_icd": None,
            },
            expected={"mdc_code": "MDCB", "drg_code": "BM05"},
            tags=["极简输入"],
        ))

        # E5: 有手术但手术码不在该 MDC 的 ADRG 规则中 → catch-all
        cases.append(TestCase(
            id="", title="跨 MDC 手术 → catch-all",
            category="exception", priority="P2", module="engine",
            description="MDCI 下手术不是骨科手术 → 走 catch-all IS9",
            input={
                "principal_icd": "S72.000",
                "secondary_icds": [],
                "principal_procedure_icd": "38.1000x002",
            },
            expected={"mdc_code": "MDCI", "adrg_code": "IS9"},
            tags=["跨MDC"],
        ))

        return cases


# ═══════════════════════════════════════════════════════════════════
# FR-018: 测试用例分类
# ═══════════════════════════════════════════════════════════════════

class TestCaseClassifier:
    """按功能模块和优先级对测试用例进行分类组织。"""

    @staticmethod
    def by_category(cases: list[TestCase]) -> dict[str, list[TestCase]]:
        """按场景分类：normal / boundary / exception。"""
        groups: dict[str, list[TestCase]] = {"normal": [], "boundary": [], "exception": []}
        for c in cases:
            groups.setdefault(c.category, []).append(c)
        return groups

    @staticmethod
    def by_priority(cases: list[TestCase]) -> dict[str, list[TestCase]]:
        """按优先级分类：P0 / P1 / P2 / P3。"""
        groups: dict[str, list[TestCase]] = {}
        for c in cases:
            groups.setdefault(c.priority, []).append(c)
        return groups

    @staticmethod
    def by_module(cases: list[TestCase]) -> dict[str, list[TestCase]]:
        """按功能模块分类：engine / parser / agent。"""
        groups: dict[str, list[TestCase]] = {}
        for c in cases:
            groups.setdefault(c.module, []).append(c)
        return groups

    @staticmethod
    def summary(cases: list[TestCase]) -> dict:
        """返回分类摘要统计。"""
        return {
            "total": len(cases),
            "by_category": {k: len(v) for k, v in TestCaseClassifier.by_category(cases).items()},
            "by_priority": {k: len(v) for k, v in TestCaseClassifier.by_priority(cases).items()},
            "by_module": {k: len(v) for k, v in TestCaseClassifier.by_module(cases).items()},
        }


# ═══════════════════════════════════════════════════════════════════
# FR-019: 测试用例执行
# ═══════════════════════════════════════════════════════════════════

class TestCaseRunner:
    """执行测试用例并比对预期结果。"""

    def __init__(self, rules_path: Path | None = None) -> None:
        self._engine = GroupingEngine(rules_path)

    def run(self, cases: list[TestCase]) -> list[TestResult]:
        """执行全部用例，返回结果列表。"""
        return [self._run_one(c) for c in cases]

    def _run_one(self, case: TestCase) -> TestResult:
        inp = GroupingInput(
            principal_icd=case.input["principal_icd"],
            secondary_icds=case.input.get("secondary_icds", []),
            principal_procedure_icd=case.input.get("principal_procedure_icd"),
        )

        start = time.perf_counter()
        try:
            result = self._engine.group(inp)
            actual = {
                "mdc_code": result.mdc_code,
                "mdc_name": result.mdc_name,
                "adrg_code": result.adrg_code,
                "adrg_name": result.adrg_name,
                "drg_code": result.drg_code,
                "drg_name": result.drg_name,
                "has_mcc": bool(result.mcc_hits),
                "has_cc": bool(result.cc_hits),
                "mcc_hits": result.mcc_hits,
                "cc_hits": result.cc_hits,
                "reason_steps": result.reason_steps,
            }
            passed = self._check_expected(case.expected, actual)
            error = "" if passed else self._diff_expected(case.expected, actual)
            skipped = False
        except Exception as e:
            actual = {"error": str(e)}
            passed = False
            error = str(e)
            skipped = False
        duration_ms = (time.perf_counter() - start) * 1000

        return TestResult(
            case_id=case.id,
            title=case.title,
            category=case.category,
            priority=case.priority,
            module=case.module,
            input=case.input,
            expected=case.expected,
            actual=actual,
            passed=passed,
            error=error,
            duration_ms=round(duration_ms, 2),
            skipped=skipped,
        )

    def _check_expected(self, expected: dict, actual: dict) -> bool:
        """检查实际结果是否匹配预期（仅检查 expected 中指定的字段）。"""
        for key, val in expected.items():
            actual_val = actual.get(key)
            if actual_val != val:
                return False
        return True

    def _diff_expected(self, expected: dict, actual: dict) -> str:
        """生成预期 vs 实际的差异说明。"""
        diffs = []
        for key, val in expected.items():
            actual_val = actual.get(key)
            if actual_val != val:
                diffs.append(f"{key}: 预期={val}, 实际={actual_val}")
        return "; ".join(diffs) if diffs else "未知差异"


# ═══════════════════════════════════════════════════════════════════
# FR-020: 测试用例导出
# ═══════════════════════════════════════════════════════════════════

class TestCaseExporter:
    """将测试用例或结果导出为 JSON 格式。"""

    @staticmethod
    def cases_to_json(cases: list[TestCase], indent: int = 2) -> str:
        """导出测试用例为 JSON 字符串。"""
        data = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total": len(cases),
            "classification": TestCaseClassifier.summary(cases),
            "cases": [c.to_dict() for c in cases],
        }
        return json.dumps(data, ensure_ascii=False, indent=indent)

    @staticmethod
    def results_to_json(results: list[TestResult], indent: int = 2) -> str:
        """导出测试结果为 JSON 字符串。"""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        data = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate": f"{passed / total * 100:.1f}%" if total > 0 else "N/A",
                "total_duration_ms": round(sum(r.duration_ms for r in results), 2),
            },
            "results": [r.to_dict() for r in results],
        }
        return json.dumps(data, ensure_ascii=False, indent=indent)

    @staticmethod
    def save_to_file(data: str, path: Path) -> Path:
        """将导出数据写入文件。"""
        path.write_text(data, encoding="utf-8")
        return path


# ═══════════════════════════════════════════════════════════════════
# AI 增强：调用 LLM 智能生成测试用例 + 覆盖分析
# ═══════════════════════════════════════════════════════════════════

def _resolve_test_llm_config() -> tuple[str | None, str | None, str]:
    """返回 (base_url, api_key, model)。"""
    import os
    from drg_agent.agent import resolve_llm_env

    base, key = resolve_llm_env(None, None)
    model = (
        os.environ.get("OPENAI_MODEL")
        or (
            "qwen3-max"
            if os.environ.get("DASHSCOPE_API_KEY") and not os.environ.get("OPENAI_API_KEY")
            else "gpt-4o-mini"
        )
    )
    return base, key, model


def _test_llm_available() -> bool:
    base, key, _ = _resolve_test_llm_config()
    return bool(base and key)


def _test_llm_chat(system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str | None:
    """调用 OpenAI 兼容 LLM，失败时返回 None。"""
    try:
        from openai import OpenAI

        base, key, model = _resolve_test_llm_config()
        if not base or not key:
            return None
        base_url = base.rstrip("/")
        client = OpenAI(api_key=key, base_url=base_url)
        kwargs: dict = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "stream": False,
        }
        if "dashscope.aliyuncs.com" in base_url.lower():
            import os as _os
            kwargs["extra_body"] = {
                "enable_thinking": _os.environ.get("DASHSCOPE_ENABLE_THINKING", "").lower().strip() in ("1", "true", "yes", "on")
            }
        completion = client.chat.completions.create(**kwargs)
        text = (completion.choices[0].message.content or "").strip()
        return text if text else None
    except Exception:
        return None


class LLMTestEnhancer:
    """使用 LLM 智能生成额外测试用例 + 分析规则覆盖盲区。"""

    @staticmethod
    def generate_additional_cases(rules_summary: str, existing_count: int) -> list:
        """让 LLM 基于规则摘要和已有用例数，生成额外的高质量测试用例。"""
        if not _test_llm_available():
            return []

        system = (
            "你是一个资深的软件测试工程师，专精于医保 DRG 分组系统的测试设计。"
            "请基于提供的规则文件摘要，生成额外的 DRG 入组测试用例（JSON 数组格式）。"
            "要求：\n"
            "1. 输出必须是严格的 JSON 数组，每个元素包含字段：\n"
            '   id(如 "TC-AI01"), title, category("normal"|"boundary"|"exception"),\n'
            '   priority("P0"|"P1"|"P2"), module("engine"|"parser"|"agent"),\n'
            '   description, input({principal_icd, secondary_icds, principal_procedure_icd}),\n'
            '   expected({mdc_code, adrg_code, drg_code, has_mcc, has_cc}), tags(字符串数组)\n'
            "2. 覆盖正常入组、边界情况和异常处理三个维度\n"
            "3. 不要与已有用例重复（已有用例数：{}）\n"
            "4. 生成 3-5 个高质量用例，关注容易出错的边缘场景\n"
            "5. 只输出 JSON 数组，不要其他文字"
        ).format(existing_count)

        user = f"规则文件摘要：\n{rules_summary}"

        response = _test_llm_chat(system, user, temperature=0.5)
        if not response:
            return []

        return LLMTestEnhancer._parse_llm_cases(response)

    @staticmethod
    def analyze_coverage_gaps(rules_summary: str, existing_cases: list) -> str | None:
        """让 LLM 分析当前测试覆盖盲区，返回分析报告。"""
        if not _test_llm_available():
            return None

        existing_summary = "\n".join(
            f"- {c.id}: {c.title} [{c.category}/{c.priority}]"
            for c in existing_cases
        )

        system = (
            "你是一个测试覆盖度分析专家。请分析当前 DRG 入组系统的测试覆盖情况，"
            "指出覆盖盲区和建议增加的测试场景。输出简洁的 Markdown 分析报告。"
        )
        user = (
            f"规则摘要：\n{rules_summary}\n\n"
            f"已有用例（{len(existing_cases)} 个）：\n{existing_summary}\n\n"
            f"请分析覆盖盲区并给出建议。"
        )

        return _test_llm_chat(system, user, temperature=0.3)

    @staticmethod
    def _parse_llm_cases(json_text: str) -> list:
        """解析 LLM 返回的 JSON 数组为 TestCase 列表。"""
        try:
            import re
            match = re.search(r"\[[\s\S]*\]", json_text)
            if not match:
                return []
            data = json.loads(match.group(0))
            return [TestCase.from_dict(item) for item in data if isinstance(item, dict)]
        except (json.JSONDecodeError, KeyError, TypeError):
            return []


class AITestCaseGenerator(TestCaseGenerator):
    """测试用例生成器 + AI 增强：规则用例 + LLM 生成的额外用例 + 覆盖分析。"""

    def generate(self, use_llm: bool = True) -> list:
        base_cases = super().generate()

        if not use_llm or not _test_llm_available():
            return base_cases

        # 构建规则摘要给 LLM
        rules_summary = json.dumps({
            "version": self._rules.get("version"),
            "mdc_count": len(self._rules.get("mdc_rules", [])),
            "adrg_count": len(self._rules.get("adrg_rules", [])),
            "mcc_count": len(self._rules.get("mcc_list", [])),
            "cc_count": len(self._rules.get("cc_list", [])),
            "sample_mdc": self._rules.get("mdc_rules", [])[:5],
            "sample_adrg": self._rules.get("adrg_rules", [])[:5],
        }, ensure_ascii=False)

        # 生成额外用例
        extra = LLMTestEnhancer.generate_additional_cases(rules_summary, len(base_cases))

        # 给 AI 生成的用例重编号
        for i, c in enumerate(extra):
            c.id = f"TC-AI{i + 1:03d}"

        return base_cases + extra

    def coverage_analysis(self, cases: list) -> str | None:
        """返回 AI 覆盖分析报告（如有 LLM），否则返回 None。"""
        if not _test_llm_available():
            return None
        rules_summary = json.dumps({
            "version": self._rules.get("version"),
            "mdc_count": len(self._rules.get("mdc_rules", [])),
            "adrg_count": len(self._rules.get("adrg_rules", [])),
        }, ensure_ascii=False)
        return LLMTestEnhancer.analyze_coverage_gaps(rules_summary, cases)
