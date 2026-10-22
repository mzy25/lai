#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""residue_scan：修复批族批的「残留复扫」（2026-10-17 质检轮增补）。

用途：30 单元修复是逐单元做的，同一族问题可能在别的单元漏网（§6「纠葛」、
§1「该亲手」、§16「本书」即质检轮扫出的三例）。本工具把族批的全部缺陷模式
固化为常驻扫描——发布批/后续任何改稿后跑一次，防回流。

用法:
    python3 series/tools/residue_scan.py            # 扫全系列（散文单元）
    python3 series/tools/residue_scan.py <章.md>…   # 只扫指定文件
    python3 series/tools/residue_scan.py --list     # 连「判留族」一并列出

判读：EXPECT0＝应零命中（有命中即回流，需修）；LIST＝判留族，只提示计数防误删。
"""
from __future__ import annotations

import argparse
import glob
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERIES = HERE.parent

# (名称, 正则, 期望)
PATTERNS = [
    ("账本实物画面（台账禁注）", r"方差账本|账本实物|一本账|两本账|三本账|四本账", "EXPECT0"),
    ("本书/本文自指（B1）", r"(?<![一亿每整两三四五几])本书|本文（?!档）|笔者", "EXPECT0"),
    ("「该亲手」族", r"该亲手", "EXPECT0"),
    ("纠葛（统一用纠缠）", r"纠葛", "EXPECT0"),
    ("缝住/缝成（统一收进/并成）", r"缝住|缝成", "EXPECT0"),
    ("刺目喻词（修复批清除项）", r"双刃剑|发脆|血亏|拿捏|背进", "EXPECT0"),
    ("被围观（统一被咨询）", r"被围观", "EXPECT0"),
    ("第 0 章（统一第〇部）", r"第 0 章", "EXPECT0"),
    ("隐空间（统一潜空间）", r"隐空间", "EXPECT0"),
    ("拆掉/拆过/拆楼/拆封（收形族）", r"拆掉|拆过|拆楼|拆封", "EXPECT0"),
    ("「一行」体量注记（节题/公式族）", r"[^。，：；]{2}一行[：，]", "LIST"),
    ("拆族总账（判留，防误删）", r"拆成|拆开|拆出|拆法|拆链|拆解", "LIST"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="只扫指定章文件（默认全系列）")
    ap.add_argument("--list", action="store_true", help="连判留族一并列出")
    a = ap.parse_args()
    files = a.files or [f for f in glob.glob(str(SERIES / "§*.md")) + glob.glob(str(SERIES / "T*.md"))
                        + glob.glob(str(SERIES / "支线*.md")) if not Path(f).name.startswith(("AGENTS", "plan"))]
    missing = [f for f in files if not Path(f).is_file()]
    if missing:
        print(f"文件不存在：{', '.join(missing)}", file=sys.stderr)
        return 2
    total_bad = 0
    for name, pat, kind in PATTERNS:
        if kind == "LIST" and not a.list:
            continue
        hits = []
        for f in files:
            t = Path(f).read_text(encoding="utf-8")
            for m in re.finditer(pat, t):
                i = m.start()
                hits.append(f"{Path(f).name[:16]}…{t[max(0,i-15):i+len(m.group(0))+18]}…".replace("\n", "⏎"))
        if hits:
            print(f"== [{kind}] {name}: {len(hits)} ==")
            for h in hits[:12]:
                print("  ", h)
            if kind == "EXPECT0":
                total_bad += len(hits)
        else:
            print(f"== [{kind}] {name}: 0 ✓")
    print(f"\nresidue_scan：应零命中类合计 {total_bad} 处" + ("（有回流，需修）" if total_bad else "（全清洁）"))
    return 1 if total_bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
