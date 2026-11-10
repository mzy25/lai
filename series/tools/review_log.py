#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""review_log：审阅裁决日志（防重复改、防过度改）。

用法：
    python3 series/tools/review_log.py append --chapter "§13" --pass prose \
        --candidate "C-003" --location "L110" --decision reject --reason "盲评 1:1，保留原样"
    python3 series/tools/review_log.py summary
    python3 series/tools/review_log.py summary --chapter "§13"
    python3 series/tools/review_log.py --selftest

默认日志：series/edit/review_log.tsv；无 series/edit/ 时退回 series/.tmp/。
决策：accept / reject / defer / keep。summary 只统计 accept/reject 的接受率。
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / "series" / "edit" / "review_log.tsv"
FALLBACK = ROOT / "series" / ".tmp" / "review_log.tsv"
HEADER = ["date", "chapter", "pass", "candidate", "location",
          "decision", "reason", "commit"]


def default_log() -> Path:
    return PRIVATE if (ROOT / "series" / "edit").is_dir() else FALLBACK


def append_row(log: Path, row: dict) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    new = not log.exists()
    with log.open("a", encoding="utf-8", newline="\n") as f:
        if new:
            f.write("\t".join(HEADER) + "\n")
        f.write("\t".join(str(row.get(k, "")) for k in HEADER) + "\n")


def read_rows(log: Path) -> list[dict]:
    if not log.exists():
        return []
    lines = log.read_text(encoding="utf-8").splitlines()
    if not lines:
        return []
    head = lines[0].split("\t")
    return [dict(zip(head, ln.split("\t"))) for ln in lines[1:] if ln.strip()]


def summary(rows: list[dict], chapter: str | None = None) -> str:
    if chapter:
        rows = [r for r in rows if r.get("chapter") == chapter]
    if not rows:
        return "（无记录）"
    by_ch: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        by_ch[r.get("chapter", "?")][r.get("decision", "?")] += 1
    out = ["| 章 | accept | reject | defer | keep | 接受率 |",
           "| --- | --- | --- | --- | --- | --- |"]
    total_a = total_r = 0
    for ch in sorted(by_ch):
        c = by_ch[ch]
        a, r = c.get("accept", 0), c.get("reject", 0)
        total_a += a
        total_r += r
        rate = f"{a / (a + r) * 100:.0f}%" if (a + r) else "—"
        out.append(f"| {ch} | {a} | {r} | {c.get('defer', 0)} | {c.get('keep', 0)} | {rate} |")
    rate = f"{total_a / (total_a + total_r) * 100:.0f}%" if (total_a + total_r) else "—"
    out.append(f"| **合计** | **{total_a}** | **{total_r}** | "
               f"**{sum(c.get('defer', 0) for c in by_ch.values())}** | "
               f"**{sum(c.get('keep', 0) for c in by_ch.values())}** | **{rate}** |")
    return "\n".join(out)


def selftest() -> int:
    import tempfile
    log = Path(tempfile.mkdtemp(prefix="rlog_")) / "review_log.tsv"
    append_row(log, {"date": "2026-11-04", "chapter": "§13", "pass": "prose",
                     "candidate": "C-1", "location": "L1", "decision": "accept",
                     "reason": "更顺", "commit": "abc"})
    append_row(log, {"date": "2026-11-04", "chapter": "§13", "pass": "prose",
                     "candidate": "C-2", "location": "L2", "decision": "reject",
                     "reason": "盲评分歧", "commit": "abc"})
    rows = read_rows(log)
    text = summary(rows, "§13")
    ok = len(rows) == 2 and "50%" in text and "C-1" not in text
    print("review_log selftest:", "PASS" if ok else f"FAIL {rows}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--log", help="日志路径（默认 edit/review_log.tsv）")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("append")
    a.add_argument("--chapter", required=True)
    a.add_argument("--pass", dest="pass_", required=True,
                   choices=["structure", "prose", "audit", "closeout"])
    a.add_argument("--candidate", default="")
    a.add_argument("--location", default="")
    a.add_argument("--decision", required=True,
                   choices=["accept", "reject", "defer", "keep"])
    a.add_argument("--reason", default="")
    a.add_argument("--commit", default="")
    s = sub.add_parser("summary")
    s.add_argument("--chapter")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    log = Path(args.log) if args.log else default_log()
    if args.cmd == "append":
        append_row(log, {
            "date": dt.date.today().isoformat(),
            "chapter": args.chapter,
            "pass": args.pass_,
            "candidate": args.candidate,
            "location": args.location,
            "decision": args.decision,
            "reason": args.reason,
            "commit": args.commit,
        })
        print(f"appended {log}")
        return 0
    if args.cmd == "summary":
        print(summary(read_rows(log), args.chapter))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
