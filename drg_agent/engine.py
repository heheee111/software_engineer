# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GroupingInput:
    principal_icd: str
    secondary_icds: list[str]
    principal_procedure_icd: str | None


@dataclass
class GroupingResult:
    mdc_code: str
    mdc_name: str
    adrg_code: str
    adrg_name: str
    drg_code: str
    drg_name: str
    mcc_hits: list[str] = field(default_factory=list)
    cc_hits: list[str] = field(default_factory=list)
    reason_steps: list[str] = field(default_factory=list)


def _match_any(patterns: list[str], value: str) -> bool:
    v = value.strip()
    for p in patterns:
        if re.search(p, v, re.IGNORECASE):
            return True
    return False


class GroupingEngine:
    def __init__(self, rules_path: Path | None = None) -> None:
        base = Path(__file__).resolve().parent / "rules" / "sample_rules.json"
        path = rules_path or base
        self._rules = json.loads(path.read_text(encoding="utf-8"))

    def group(self, inp: GroupingInput) -> GroupingResult:
        p = inp.principal_icd
        steps: list[str] = []

        mdc_code, mdc_name = self._resolve_mdc(p, steps)
        adrg_code, adrg_name, supports_layer = self._resolve_adrg(
            mdc_code, p, inp.principal_procedure_icd, steps
        )
        mcc_hits, cc_hits = self._resolve_cc_mcc(inp, p, supports_layer, steps)
        drg_code, drg_name = self._resolve_fine_drg(
            adrg_code, adrg_name, mcc_hits, cc_hits, supports_layer, steps
        )

        return GroupingResult(
            mdc_code=mdc_code,
            mdc_name=mdc_name,
            adrg_code=adrg_code,
            adrg_name=adrg_name,
            drg_code=drg_code,
            drg_name=drg_name,
            mcc_hits=mcc_hits,
            cc_hits=cc_hits,
            reason_steps=steps,
        )

    def _resolve_mdc(self, principal_icd: str, steps: list[str]) -> tuple[str, str]:
        for rule in self._rules.get("mdc_rules", []):
            if _match_any(rule["match_principal_icd"], principal_icd):
                code = rule["mdc_code"]
                name = rule["mdc_name"]
                steps.append(
                    f"主要诊断 {principal_icd} 匹配规则「{rule['id']}」→ {code}（{name}）"
                )
                return code, name
        steps.append(f"主要诊断 {principal_icd} 未命中任何 MDC 规则")
        return "UNKNOWN", "未分组"

    def _resolve_adrg(
        self,
        mdc_code: str,
        principal_icd: str,
        procedure: str | None,
        steps: list[str],
    ) -> tuple[str, str, bool]:
        if mdc_code == "UNKNOWN":
            return "UNKNOWN", "未分组", False

        proc = procedure.strip() if procedure else None

        def take(rule: dict, reason: str) -> tuple[str, str, bool]:
            code = rule["adrg_code"]
            name = rule["adrg_name"]
            sup = bool(rule.get("supports_complication_layer", True))
            steps.append(reason)
            return code, name, sup

        if proc:
            for rule in self._rules.get("adrg_rules", []):
                if rule["mdc_code"] != mdc_code:
                    continue
                proc_pats = rule.get("match_principal_procedure") or []
                dx_pats = rule.get("match_principal_icd") or []
                if dx_pats and not _match_any(dx_pats, principal_icd):
                    continue
                if rule.get("surgical_catch_all"):
                    continue
                if proc_pats and _match_any(proc_pats, proc):
                    return take(
                        rule,
                        f"在 {mdc_code} 下，主要手术 {proc} 命中 ADRG「{rule['adrg_code']}」{rule['adrg_name']}",
                    )
            for rule in self._rules.get("adrg_rules", []):
                if rule["mdc_code"] != mdc_code or not rule.get("surgical_catch_all"):
                    continue
                return take(
                    rule,
                    f"在 {mdc_code} 下，主要手术 {proc} 未命中专科手术表，归入综合手术 ADRG「{rule['adrg_code']}」{rule['adrg_name']}",
                )

        for rule in self._rules.get("adrg_medical_rules", []):
            if rule["mdc_code"] != mdc_code:
                continue
            dx_pats = rule.get("match_principal_icd") or []
            if dx_pats and not _match_any(dx_pats, principal_icd):
                continue
            need_proc = rule.get("require_procedure", False)
            if need_proc and not proc:
                continue
            if rule.get("require_no_procedure") and proc:
                continue
            return take(
                rule,
                f"在 {mdc_code} 下，{'无手术，' if not proc else ''}主要诊断 {principal_icd} 命中内科/非手术 ADRG「{rule['adrg_code']}」{rule['adrg_name']}",
            )

        for rule in self._rules.get("adrg_medical_fallback", []):
            if rule["mdc_code"] != mdc_code:
                continue
            return take(
                rule,
                f"在 {mdc_code} 下，归入该 MDC 默认内科路径 ADRG「{rule['adrg_code']}」{rule['adrg_name']}",
            )

        if not proc:
            steps.append("无主要手术操作，且未匹配到内科入组规则")
        else:
            steps.append(f"MDC {mdc_code} 下主要手术 {proc} 未匹配到可用 ADRG")
        return "UNKNOWN", "未分组", False

    def _principal_excludes_secondary(
        self, principal_icd: str, secondary_icd: str
    ) -> bool:
        for block in self._rules.get("mcc_exclusions_by_principal", []):
            if not _match_any(block["principal_patterns"], principal_icd):
                continue
            for pat in block.get("excluded_secondary_patterns", []):
                if re.search(pat, secondary_icd, re.IGNORECASE):
                    return True
        return False

    def _resolve_cc_mcc(
        self,
        inp: GroupingInput,
        principal_icd: str,
        supports_layer: bool,
        steps: list[str],
    ) -> tuple[list[str], list[str]]:
        mcc_hits: list[str] = []
        cc_hits: list[str] = []

        if not supports_layer:
            steps.append("当前 ADRG 不支持并发症分层，不判定 MCC/CC")
            return mcc_hits, cc_hits

        for entry in self._rules.get("mcc_list", []):
            pat = entry["icd_pattern"]
            label = entry["label"]
            for sec in inp.secondary_icds:
                if not re.search(pat, sec, re.IGNORECASE):
                    continue
                if self._principal_excludes_secondary(principal_icd, sec):
                    steps.append(
                        f"次要诊断 {sec}（{label}）被主诊断排除表剔除，不计入 MCC"
                    )
                    continue
                mcc_hits.append(f"{sec} ← {label}")
                steps.append(
                    f"次要诊断 {sec} 属于 MCC 列表（{label}），且未被主诊断排除表排除"
                )

        for entry in self._rules.get("cc_list", []):
            pat = entry["icd_pattern"]
            label = entry["label"]
            for sec in inp.secondary_icds:
                if re.search(pat, sec, re.IGNORECASE) and not any(
                    re.search(m["icd_pattern"], sec, re.IGNORECASE)
                    for m in self._rules.get("mcc_list", [])
                ):
                    if self._principal_excludes_secondary(principal_icd, sec):
                        continue
                    cc_hits.append(f"{sec} ← {label}")
                    steps.append(f"次要诊断 {sec} 归入 CC：{label}")

        return mcc_hits, cc_hits

    def _resolve_fine_drg(
        self,
        adrg_code: str,
        adrg_name: str,
        mcc_hits: list[str],
        cc_hits: list[str],
        supports_layer: bool,
        steps: list[str],
    ) -> tuple[str, str]:
        fm = self._rules.get("drg_fine_map", {}).get(adrg_code)

        if not supports_layer or adrg_code == "UNKNOWN":
            if fm:
                chosen = fm["without_cc_mcc"]
                code, name = chosen["code"], chosen["name"]
                steps.append(f"并发症分层结果 → DRG {code}（{name}）")
                return code, name
            steps.append("无法细分为 DRG（规则未定义或上游未命中）")
            return "UNKNOWN", "未分组"

        if fm:
            if mcc_hits:
                key = "with_mcc"
            elif cc_hits:
                key = "with_cc_only"
            else:
                key = "without_cc_mcc"
            chosen = fm[key]
            code = chosen["code"]
            name = chosen["name"]
            steps.append(f"并发症分层结果 → DRG {code}（{name}）")
            return code, name

        tier = "1" if mcc_hits else "3" if cc_hits else "5"
        suffix = "伴严重合并症或并发症" if tier == "1" else "伴一般合并症或并发症" if tier == "3" else "不伴合并症或并发症"
        if len(adrg_code) >= 2 and adrg_code[-1].isdigit():
            body = adrg_code[:-1]
            last = adrg_code[-1]
            code = f"{body}{last}{tier}"
        else:
            code = f"{adrg_code}{tier}"
        name = f"{adrg_name}，{suffix}（综合推断）"
        steps.append(f"并发症分层结果 → DRG {code}（{name}）")
        return code, name
