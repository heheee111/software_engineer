# -*- coding: utf-8 -*-

from pathlib import Path

import pytest

from drg_agent.engine import GroupingEngine, GroupingInput


@pytest.fixture
def engine():
    return GroupingEngine()


def test_gastric_tumor_gb29(engine: GroupingEngine):
    """胃窦恶性肿瘤 C16.301 + 腔隙性脑梗死 I63.801 (CC) + 胃大部切除术 43.7x03 → GB29"""
    inp = GroupingInput(
        principal_icd="C16.301",
        secondary_icds=["K66.002", "Z98.800x108", "I63.801", "K76.807"],
        principal_procedure_icd="43.7x03",
    )
    r = engine.group(inp)
    assert r.mdc_code == "MDCG"
    assert r.adrg_code == "GB2"
    assert r.drg_code == "GB29"
    assert r.cc_hits
    assert not r.mcc_hits


def test_respiratory_ec29(engine: GroupingEngine):
    """支气管胆管瘘 J86.000x013 + 肝内胆管癌 C22.100 (CC) + 膈肌缝合术 34.8200x002 → EC29"""
    inp = GroupingInput(
        principal_icd="J86.000x013",
        secondary_icds=["K66.002", "C22.100", "Z98.800x115"],
        principal_procedure_icd="34.8200x002",
    )
    r = engine.group(inp)
    assert r.mdc_code == "MDCE"
    assert r.adrg_code == "EC2"
    assert r.drg_code == "EC29"
    assert r.cc_hits
    assert not r.mcc_hits


def test_biliary_hc15(engine: GroupingEngine):
    """胆管狭窄 K83.105 + 胆总管切除术 51.6303 + 无 CC/MCC → HC15"""
    inp = GroupingInput(
        principal_icd="K83.105",
        secondary_icds=["K83.109", "K83.807", "K66.007", "Z43.402"],
        principal_procedure_icd="51.6303",
    )
    r = engine.group(inp)
    assert r.mdc_code == "MDCH"
    assert r.adrg_code == "HC1"
    assert r.drg_code == "HC15"
    assert not r.cc_hits
    assert not r.mcc_hits


def test_neuro_bb11(engine: GroupingEngine):
    """伤寒脑膜炎 A01.002+G01* + 呼吸衰竭 J96.0 (MCC) + 动脉内膜剥脱术 38.1000x002 → BB11"""
    inp = GroupingInput(
        principal_icd="A01.002+G01*",
        secondary_icds=["J96.0"],
        principal_procedure_icd="38.1000x002",
    )
    r = engine.group(inp)
    assert r.mdc_code == "MDCB"
    assert r.adrg_code == "BB1"
    assert r.drg_code == "BB11"
    assert r.mcc_hits
    assert any("J96.0" in h for h in r.mcc_hits)


def test_bad_procedure_fallback(engine: GroupingEngine):
    """主手术不命中专科表时，归入该 MDC 综合手术 ADRG（BS9），仍可判 MCC → BS91"""
    inp = GroupingInput(
        principal_icd="A01.002+G01*",
        secondary_icds=["J96.0"],
        principal_procedure_icd="38.9999",
    )
    r = engine.group(inp)
    assert r.adrg_code == "BS9"
    assert r.mcc_hits
    assert r.drg_code == "BS91"
