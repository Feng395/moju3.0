#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""历史板料线验证脚本兼容壳。"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from tools.diagnostics.verify_integration import main


if __name__ == "__main__":
    raise SystemExit(main())
