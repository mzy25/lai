#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""row_check：句长基准表 × 实测全量对账（2026-10-17 质检轮增补）。

用途：style/句长基准.md 的 33 行是逐单元手工滚核的——手抄可能出错（质检轮就
抓到 §12 句数、§5 中位两处漂移）。本工具对每行重跑 sentence_stats 并逐列比对，
一处不齐即列出。改稿/重建后收尾跑一次。

用法:
    python3 series/tools/row_check.py            # 只报差异
    python3 series/tools/row_check.py --fix      # 差异列直接以实测值回写表
"""
from __future__ import annotations

import argparse
import glob
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERIES = HERE.parent
TABLE = SERIES / "style" / "句长基准.md"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="以实测值回写差异列")
    a = ap.parse_args()
    lines = TABLE.read_text(encoding="utf-8").splitlines()
    rows = {}
    for idx, ln in enumerate(lines):
        if ln.startswith("|") and ln.count("|") >= 8:
            lc = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(lc) >= 8 and lc[2].isdigit():
                rows[lc[0]] = (idx, lc)
    files = [f for f in glob.glob(str(SERIES / "§*.md")) + glob.glob(str(SERIES / "T*.md"))
             + glob.glob(str(SERIES / "支线*.md")) if not Path(f).name.startswith(("AGENTS", "plan"))]
    diffs, missing = [], []
    for f in sorted(files):
        uid = Path(f).name.split("-")[0]
        key = next((k for k in rows if k.startswith(uid)), None)
        if key is None:
            missing.append(Path(f).name)
            continue
        out = subprocess.run([sys.executable, str(HERE / "sentence_stats.py"), f, "--row"],
                             capture_output=True, text=True).stdout.strip()
        lc = [c.strip() for c in out.split("|") if c.strip()]
        got = (lc[2], lc[3], lc[4], lc[5], lc[6], lc[7])
        idx, rv = rows[key]
        have = (rv[2], rv[3], rv[4], rv[5], rv[6], rv[7])
        if got != have:
            diffs.append((key, idx, have, got))
    for k, idx, have, got in diffs:
        print(f"差异 {k[:22]}：表={have} 测={got}")
        if a.fix:
            lc = rows[k][1]
            for j, v in zip(range(2, 8), got):
                lc[j] = v
            lines[idx] = "| " + " | ".join(lc) + " |"
    if a.fix and diffs:
        TABLE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"已回写 {len(diffs)} 行")
    for m in missing:
        print("无表行:", m)
    print(f"row_check：{len(files)} 文件，差异 {len(diffs)}，无表行 {len(missing)}" + ("（全对齐）" if not diffs and not missing else ""))
    return 1 if diffs or missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
