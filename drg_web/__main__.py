# -*- coding: utf-8 -*-
"""启动 Web 界面：python -m drg_web"""

from __future__ import annotations

import argparse
from pathlib import Path

import sys

# 确保项目根目录在 sys.path 中（兼容 IDE 直接运行 __main__.py 和 python -m drg_web）
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# 自动加载项目根目录的 .env 文件
try:
    from dotenv import load_dotenv

    _env_path = _project_root / ".env"
    if _env_path.is_file():
        load_dotenv(_env_path)
except ImportError:
    pass

import uvicorn


def main() -> None:
    p = argparse.ArgumentParser(description="医保 DRG 入组 Web 前端")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8848)
    args = p.parse_args()
    uvicorn.run(
        "drg_web.app:app",
        host=args.host,
        port=args.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
