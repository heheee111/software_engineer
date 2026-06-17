# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ParsedEMR:
    principal_diagnosis_raw: str
    principal_diagnosis_code: str | None
    secondary_diagnoses_raw: list[str]
    secondary_diagnosis_codes: list[str]
    principal_procedure_raw: str | None
    principal_procedure_code: str | None
    raw_text: str


_LEADING_ICD10 = re.compile(
    r"^([A-TV-Z][0-9]{2}(?:\.[0-9A-Z*+]+)?)"
)
# 手术操作编码常以数字开头（如 38.1000x002）
_LEADING_PROC = re.compile(r"^([0-9]{2}\.[0-9A-Za-z*+]+)")


def _strip_dx_code(line: str) -> tuple[str | None, str]:
    line = line.strip()
    if not line:
        return None, ""
    m = _LEADING_ICD10.match(line)
    if m:
        code = m.group(1)
        rest = line[m.end() :].lstrip()
        return code, rest
    return None, line


def _strip_proc_code(line: str) -> tuple[str | None, str]:
    line = line.strip()
    if not line:
        return None, ""
    m = _LEADING_PROC.match(line)
    if m:
        code = m.group(1)
        rest = line[m.end() :].lstrip()
        return code, rest
    return None, line


def parse_emr_text(text: str) -> ParsedEMR:
    """从中文电子病历片段解析主要/次要诊断与主要手术（与课件字段一致）。"""
    principal_raw = ""
    secondary_raw: list[str] = []
    procedure_raw = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("主要诊断"):
            principal_raw = re.split(r"[：:]", line, maxsplit=1)[-1].strip()
        elif line.startswith("次要诊断"):
            rest = re.split(r"[：:]", line, maxsplit=1)[-1].strip()
            for part in re.split(r"[，,、;；]", rest):
                p = part.strip()
                if p:
                    secondary_raw.append(p)
        elif line.startswith("主要手术"):
            procedure_raw = re.split(r"[：:]", line, maxsplit=1)[-1].strip()

    p_code, _ = _strip_dx_code(principal_raw)
    s_codes: list[str] = []
    for s in secondary_raw:
        c, _ = _strip_dx_code(s)
        if c:
            s_codes.append(c)
    proc_code, _ = _strip_proc_code(procedure_raw) if procedure_raw else (None, "")

    return ParsedEMR(
        principal_diagnosis_raw=principal_raw,
        principal_diagnosis_code=p_code,
        secondary_diagnoses_raw=secondary_raw,
        secondary_diagnosis_codes=s_codes,
        principal_procedure_raw=procedure_raw or None,
        principal_procedure_code=proc_code,
        raw_text=text,
    )
