# -*- coding: utf-8 -*-

from pathlib import Path

import pytest

from drg_agent.engine import GroupingEngine, GroupingInput


@pytest.fixture
def engine():
    return GroupingEngine()


def test_slide6_bb11(engine: GroupingEngine):
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


def test_no_mcc_bb15(engine: GroupingEngine):
    inp = GroupingInput(
        principal_icd="A01.002+G01*",
        secondary_icds=[],
        principal_procedure_icd="38.1000x002",
    )
    r = engine.group(inp)
    assert r.drg_code == "BB15"


def test_bad_procedure_falls_back_surgical_bucket(engine: GroupingEngine):
    """主手术不命中专科表时，归入该 MDC 综合手术 ADRG（BS9），仍可判 MCC。"""
    inp = GroupingInput(
        principal_icd="A01.002+G01*",
        secondary_icds=["J96.0"],
        principal_procedure_icd="38.9999",
    )
    r = engine.group(inp)
    assert r.adrg_code == "BS9"
    assert r.mcc_hits
    assert r.drg_code == "BS91"


def test_pneumonia_medical_no_surgery(engine: GroupingEngine):
    inp = GroupingInput(
        principal_icd="J18.901",
        secondary_icds=[],
        principal_procedure_icd=None,
    )
    r = engine.group(inp)
    assert r.mdc_code == "MDCE"
    assert r.adrg_code == "EM0"
    assert r.drg_code == "EM05"


def test_case5_femoral_neck_if13(engine: GroupingEngine):
    inp = GroupingInput(
        principal_icd="S72.000",
        secondary_icds=["M81.000"],
        principal_procedure_icd="79.3500x001",
    )
    r = engine.group(inp)
    assert r.mdc_code == "MDCI"
    assert r.adrg_code == "IF1"
    assert r.drg_code == "IF13"
    assert r.cc_hits
    assert not r.mcc_hits
