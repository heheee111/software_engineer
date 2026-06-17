# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 自动加载项目根目录的 .env 文件
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.is_file():
        load_dotenv(_env_path)
except ImportError:
    pass

from drg_agent.emr_parser import parse_emr_text
from drg_agent.engine import GroupingEngine, GroupingInput, GroupingResult

# 与阿里云百炼 OpenAI 兼容 SDK 一致：base_url 需包含 /v1，由客户端拼接 /chat/completions
DASHSCOPE_COMPAT_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def _is_dashscope_compatible_base(base: str) -> bool:
    return "dashscope.aliyuncs.com" in base.lower()


def _dashscope_enable_thinking() -> bool:
    v = os.environ.get("DASHSCOPE_ENABLE_THINKING", "").lower().strip()
    return v in ("1", "true", "yes", "on")


def resolve_llm_env(
    llm_base_url: str | None,
    llm_api_key: str | None,
) -> tuple[str | None, str | None]:
    """从入参与环境变量解析 base 与 key；优先 OPENAI_API_KEY，其次 DASHSCOPE_API_KEY。"""
    key = llm_api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get(
        "DASHSCOPE_API_KEY"
    )
    base = llm_base_url or os.environ.get("OPENAI_BASE_URL")
    if (
        not base
        and key
        and os.environ.get("DASHSCOPE_API_KEY")
        and not os.environ.get("OPENAI_API_KEY")
        and not llm_api_key
    ):
        base = DASHSCOPE_COMPAT_BASE
    if base:
        base = base.strip()
        if _is_dashscope_compatible_base(base) and "/compatible-mode" in base.lower():
            b = base.rstrip("/")
            if not b.endswith("/v1"):
                base = b + "/v1"
    return (base if base else None, key if key else None)


@dataclass
class AgentReport:
    grouping: GroupingResult
    narrative: str
    raw_emr: str


class DRGAgent:
    """编排：病历解析 → 规则入组 →（可选）大模型润色入组说明。"""

    def __init__(
        self,
        rules_path: Path | None = None,
        *,
        llm_enabled: bool = True,
        llm_base_url: str | None = None,
        llm_api_key: str | None = None,
        llm_model: str | None = None,
    ) -> None:
        self._engine = GroupingEngine(rules_path)
        if llm_enabled:
            self._llm_base, self._llm_key = resolve_llm_env(llm_base_url, llm_api_key)
        else:
            self._llm_base, self._llm_key = None, None
        self._llm_model = llm_model or os.environ.get("OPENAI_MODEL") or (
            "qwen3-max"
            if os.environ.get("DASHSCOPE_API_KEY")
            and not os.environ.get("OPENAI_API_KEY")
            else "gpt-4o-mini"
        )

    def run(self, emr_text: str) -> AgentReport:
        parsed = parse_emr_text(emr_text)
        if not parsed.principal_diagnosis_code:
            raise ValueError("无法从病历中解析主要诊断编码，请检查「主要诊断：」格式")
        proc = parsed.principal_procedure_code
        inp = GroupingInput(
            principal_icd=parsed.principal_diagnosis_code,
            secondary_icds=parsed.secondary_diagnosis_codes,
            principal_procedure_icd=proc,
        )
        result = self._engine.group(inp)
        base_narrative = self._default_narrative(parsed, result)
        if self._llm_base and self._llm_key:
            narrative = self._llm_enhance(emr_text, result, base_narrative)
        else:
            narrative = base_narrative
        return AgentReport(grouping=result, narrative=narrative, raw_emr=emr_text)

    def _default_narrative(self, parsed: Any, g: GroupingResult) -> str:
        lines = [
            "【DRG 入组结论】",
            f"DRG 编码：{g.drg_code}，{g.drg_name}",
            f"MDC：{g.mdc_code}（{g.mdc_name}）",
            f"ADRG：{g.adrg_code}（{g.adrg_name}）",
            "",
            "【入组推理链】",
            *g.reason_steps,
        ]
        if g.mcc_hits:
            lines.extend(["", "【MCC】", *g.mcc_hits])
        if g.cc_hits:
            lines.extend(["", "【CC】", *g.cc_hits])
        return "\n".join(lines)

    def _llm_enhance(
        self, emr_text: str, g: GroupingResult, fallback: str
    ) -> str:
        try:
            from openai import OpenAI

            base = (self._llm_base or "").rstrip("/")
            client = OpenAI(api_key=self._llm_key, base_url=base)
            messages = [
                {
                    "role": "system",
                    "content": "你是医保 DRG 入组专家，根据给定结构化入组结果，用简洁中文写「入组原因说明」，勿 contradict 给定的编码结论。",
                },
                {
                    "role": "user",
                    "content": f"病历摘要：\n{emr_text}\n\n结构化结果：\n{fallback}\n\n请输出「入组原因说明」段落（200字内）。",
                },
            ]
            kwargs: dict[str, Any] = {
                "model": self._llm_model,
                "messages": messages,
                "temperature": 0.2,
                "stream": False,
            }
            if _is_dashscope_compatible_base(base):
                kwargs["extra_body"] = {
                    "enable_thinking": _dashscope_enable_thinking(),
                }
            completion = client.chat.completions.create(**kwargs)
            msg = completion.choices[0].message
            text = (msg.content or "").strip()
            if not text:
                return fallback
            return f"{fallback}\n\n【大模型入组说明】\n{text}"
        except Exception:
            return fallback
