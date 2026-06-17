# -*- coding: utf-8 -*-

from pathlib import Path

from drg_agent.agent import DRGAgent


def test_agent_gastric_tumor_example():
    """端到端测试：读取 example EMR 文件，验证分组结果"""
    emr = Path(__file__).resolve().parent.parent / "examples" / "slide6_emr.txt"
    report = DRGAgent().run(emr.read_text(encoding="utf-8"))
    assert report.grouping.drg_code == "GB29"
