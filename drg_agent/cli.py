# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
from pathlib import Path

from drg_agent.agent import DRGAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="医保 DRG 入组智能体 CLI")
    parser.add_argument(
        "emr_file",
        nargs="?",
        type=Path,
        help="电子病历文本文件路径（UTF-8）；省略则从标准输入读取",
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=None,
        help="自定义规则 JSON 路径（默认可省略，使用内置 sample_rules.json）",
    )
    args = parser.parse_args()

    if args.emr_file:
        text = args.emr_file.read_text(encoding="utf-8")
    else:
        import sys

        text = sys.stdin.read()

    agent = DRGAgent(rules_path=args.rules)
    report = agent.run(text)
    print(report.narrative)


if __name__ == "__main__":
    main()
