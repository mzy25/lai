#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply_edits：断言式落文器（行文深审v2 修复批配套；2026-10-17 W2 复盘增补）。

背景：W2 前四单元出现 5 次「一处锚点不对、整批中止重跑」（§5 台账/gloss、§6 gloss×2、
§7 登记锚/幽灵登记、§8 锚点），共性＝锚点凭记忆构造。本工具把「先全量对锚、全过才写」
固化为纪律：任一处 miss，一次列全，文件不动。

用法
    python3 series/tools/apply_edits.py <目标.md> <edits.tsv> [--dry] [--show] [--replace-all]

edits.tsv（UTF-8；制表符分隔）每行一处替换：
    label<TAB>old<TAB>new        # 推荐：label 供 miss 定位
    old<TAB>new                  # 两列亦可（label 取 old 前 12 字）
  - 两字段均支持 \\n 转义（段落拆分等含换行替换）；# 开头行与空行跳过；
  - 默认：每处 old 在「顺序应用」后的文本中 count==1；
  - --replace-all：count≥1（逐处打印计数）；
  - --show：只打印各 old 当前计数（预检）；--dry：对锚全过但不写。
退出码：0 成功；1 有 miss；2 用法错。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def unesc(s: str) -> str:
    return s.replace("\\n", "\n").replace("\\t", "\t")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="目标 markdown 源稿")
    ap.add_argument("edits", help="edits.tsv（label<TAB>old<TAB>new）")
    ap.add_argument("--dry", action="store_true", help="只校验不写入")
    ap.add_argument("--show", action="store_true", help="先列出各 old 计数（预检）")
    ap.add_argument("--replace-all", action="store_true", help="每处允许 ≥1 次")
    a = ap.parse_args()

    t = Path(a.target).read_text(encoding="utf-8")
    rows = []
    seen = set()
    for ln, line in enumerate(Path(a.edits).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) == 3:
            label, old, new = parts
        elif len(parts) == 2:
            old, new = parts
            label = old[:12]
        else:
            print(f"TSV 第 {ln} 行 {len(parts)} 列（需 2 或 3 列）")
            return 2
        old, new = unesc(old), unesc(new)
        if old == new:
            print(f"TSV 第 {ln} 行 old==new：{label}")
            return 2
        if label in seen:
            print(f"TSV 第 {ln} 行 label 重复：{label}")
            return 2
        seen.add(label)
        rows.append((label, old, new))

    cur = t
    if a.show:
        for label, old, new in rows:
            print(f"  [{label}] count={cur.count(old)}")
            cur = cur.replace(old, new)
        return 0

    misses, counts = [], []
    for label, old, new in rows:
        c = cur.count(old)
        counts.append((label, c))
        if c == 0 or (c > 1 and not a.replace_all):
            misses.append((label, c))
        else:
            cur = cur.replace(old, new)

    if misses:
        print(f"对锚失败 {len(misses)}/{len(rows)}（文件未写）：")
        for label, c in misses:
            print(f"  MISS [{label}] count={c}")
        return 1

    if a.replace_all:
        for label, c in counts:
            print(f"  [{label}] ×{c}")
    if a.dry:
        print(f"对锚全过 {len(rows)} 处（--dry，未写）")
        return 0
    Path(a.target).write_text(cur, encoding="utf-8")
    print(f"已写入 {len(rows)} 处 → {Path(a.target).name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
