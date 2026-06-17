# -*- coding: utf-8 -*-

from pathlib import Path

from drg_agent.agent import DRGAgent


def test_agent_slide6_example():
    emr = Path(__file__).resolve().parent.parent / "examples" / "slide6_emr.txt"
    report = DRGAgent().run(emr.read_text(encoding="utf-8"))
    assert report.grouping.drg_code == "BB11"
