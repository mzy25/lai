#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""unit_closeout：修复批单元收尾取证套件（2026-10-17 W2 复盘增补）。

用法
    python3 series/tools/unit_closeout.py "§N-….md" ["edit/§N.edit.md"]
    python3 series/tools/unit_closeout.py "§N-….md" --card   # 追加节地图/衔接/答案镜像摘要

依次运行并一屏汇总（正文只读；扫描报表写 series/.tmp/）：
  ① first_use_scan（有 edit 档案则查档案；v0.3 无档案时走 --ledger-only）
  ② sentence_stats --row（句长行）
  ③ residue_scan（残留复扫）
  ④ cliche_scan（套话 WARN 与计数）
  ⑤ taste_probe（品味层探针摘要）
  ⑥ --card：section_map --summary、coherence_scan、answer_mirror_check 摘要
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
    card = "--card" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--card"]
    if not args:
        print(__doc__)
        return 2
    target = args[0]
    edit = args[1] if len(args) > 1 else None
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

    if card:
        print("== ⑥ 质量卡 ==")
        out = run("section_map.py", target, "--summary")
        rows = [l for l in out.splitlines() if l.startswith("|") and "---" not in l]
        for l in rows[:9]:
            print("   " + l)
        out = run("coherence_scan.py", target)
        kinds = [l[3:] for l in out.splitlines() if l.startswith("## ")]
        print("   衔接候选：" + ("；".join(kinds) if kinds else "无"))
        out = run("answer_mirror_check.py", target)
        summary = [l for l in out.splitlines() if "答案块" in l or "未发现" in l]
        for l in (summary or ["（无摘要）"]):
            print("   镜像：" + l)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
