#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""unit_closeout：修复批单元收尾取证套件（2026-10-17 W2 复盘增补）。

用法
    python3 series/tools/unit_closeout.py "§N-….md" "edit/§N.edit.md"

依次运行并一屏汇总（只读，不改任何文件）：
  ① first_use_scan（登记/gloss 违规）
  ② sentence_stats --row（句长行）
  ③ hw_scan（行文四家族候选合计）
  ④ cliche_scan（套话 WARN 与计数）
  ⑤ taste_probe（品味层探针摘要）
把此屏抄入 §N.edit 修订 log 与总表 §六，即收尾取证；随后 build＋series_check＋两笔提交。
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(*args: str) -> str:
    p = subprocess.run(
        [sys.executable, str(HERE / args[0]), *args[1:]],
        capture_output=True,
        text=True,
    )
    return (p.stdout or "") + (p.stderr or "")


def last_lines(out: str, n: int) -> list[str]:
    lines = [l for l in out.splitlines() if l.strip()]
    return lines[-n:]


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    target, edit = sys.argv[1], sys.argv[2]

    print("== ① first_use_scan ==")
    print("\n".join("   " + l for l in last_lines(run("first_use_scan.py", target, "--edit", edit), 3)))

    print("== ② sentence_stats --row ==")
    out = run("sentence_stats.py", target, "--row")
    print("\n".join("   " + l for l in last_lines(out, 1)))

    print("== ③ hw_scan ==")
    out = run("hw_scan.py", target)
    hits = [l for l in out.splitlines() if "合计" in l]
    for l in (hits[-1:] or ["(无合计行)"]):
        print("   " + l)

    print("== ④ cliche_scan ==")
    out = run("cliche_scan.py", target)
    hits = [l for l in out.splitlines() if "WARN" in l or "命中" in l]
    for l in (hits[-4:] or ["(无 WARN)" if "WARN" not in out else out[-1]]):
        print("   " + l if hits else "   " + str(l))

    print("== ⑤ taste_probe ==")
    out = run("taste_probe.py", target)
    keep = [l for l in out.splitlines() if re.match(r"\s*[SFCQBE][)）]", l)]
    for l in (keep or last_lines(out, 6)):
        print("   " + l)
    return 0


if __name__ == "__main__":
    sys.exit(main())
