#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""unit_closeout：修复批单元收尾取证套件（2026-10-17 W2 复盘增补）。

用法
    python3 series/tools/unit_closeout.py "§N-….md" ["edit/§N.edit.md"]

依次运行并一屏汇总（正文只读；扫描报表写 series/.tmp/）：
  ① first_use_scan（有 edit 档案则查档案；v0.3 无档案时走 --ledger-only）
  ② sentence_stats --row（句长行）
  ③ residue_scan（残留复扫）
  ④ cliche_scan（套话 WARN 与计数）
  ⑤ taste_probe（品味层探针摘要）
把此屏抄入 §N 的修订记录（若有）与总表 §六，即收尾取证；随后 build＋series_check＋提交。
退出码：0 全过；1 first_use 有错或 residue_scan 有回流；2 用法/文件错。
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
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target = sys.argv[1]
    edit = sys.argv[2] if len(sys.argv) > 2 else None
    if not Path(target).is_file():
        print(f"章文件不存在：{target}", file=sys.stderr)
        return 2

    print("== ① first_use_scan ==")
    fu = ["first_use_scan.py", target]
    if edit and Path(edit).is_file():
        fu += ["--edit", edit]
    else:
        if edit:
            print(f"   （档案不存在，改走 --ledger-only：{edit}）")
        fu += ["--ledger-only"]
    fu_out = run(*fu)
    print("\n".join("   " + l for l in last_lines(fu_out, 3)))
    bad = "0 错" not in fu_out

    print("== ② sentence_stats --row ==")
    out = run("sentence_stats.py", target, "--row")
    print("\n".join("   " + l for l in last_lines(out, 1)))

    print("== ③ residue_scan ==")
    out = run("residue_scan.py", target)
    hits = [l for l in out.splitlines() if "应零命中" in l]
    for l in (hits[-1:] or ["(无合计行)"]):
        print("   " + l)
    bad |= "有回流" in out

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
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
