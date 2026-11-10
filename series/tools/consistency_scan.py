#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""consistency_scan：跨章指针、术语多释与数字台账（只定位，不判罚）。

Phase 0/1 的“账本”工具：
  - 指针账：第N篇 / 第N章 / §N 是否落在本书范围内；
  - 术语账：同一 **术语** 在不同章是否给了不同括注；
  - 数字账：数字+单位逐条列出，供人工对同一量的不同口径。

用法：
    python3 series/tools/consistency_scan.py --series
    python3 series/tools/consistency_scan.py --series --out-dir series/.tmp/phase01
    python3 series/tools/consistency_scan.py --series --numbers
    python3 series/tools/consistency_scan.py --selftest

退出码：0 默认；--strict 有指针错/术语多释时 1。
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PART_RE = re.compile(r"第\s*([〇零一二三四五六七八九十0-9]+)\s*篇")
CHAP_RE = re.compile(r"第\s*(\d+)\s*章")
SEC_RE = re.compile(r"§\s*(\d+(?:\.\d+)?)")
GLOSS_RE = re.compile(r"\*\*([^*\n]{2,24})\*\*\s*[（(]([^）)\n]{2,80})[）)]")
NUM_UNIT_RE = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?)\s*"
    r"(%|倍|GB|MB|TB|KB|B|T|token|tokens|个|步|层|维|ms|毫秒|秒|分钟|小时|天|年|"
    r"帧|条|张|轮|次|篇|章|页|美元|元|块|位)"
)
CN_DIGITS = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def series_units() -> list[Path]:
    files = sorted(ROOT.glob("§*.md"))
    files += sorted(ROOT.glob("T*.md"))
    files += sorted(ROOT.glob("支线*.md"))
    return files


def cn_num(s: str) -> int | None:
    s = s.strip()
    if s.isdigit():
        return int(s)
    if s in CN_DIGITS:
        return CN_DIGITS[s]
    if s == "十":
        return 10
    if len(s) == 2 and s[0] == "十" and s[1] in CN_DIGITS:
        return 10 + CN_DIGITS[s[1]]
    if len(s) == 2 and s[0] in CN_DIGITS and s[1] == "十":
        return CN_DIGITS[s[0]] * 10
    if len(s) == 3 and s[0] in CN_DIGITS and s[1] == "十" and s[2] in CN_DIGITS:
        return CN_DIGITS[s[0]] * 10 + CN_DIGITS[s[2]]
    return None


def allowed_sections(files: list[Path]) -> set[str]:
    out = set()
    for p in files:
        m = re.match(r"^§(\d+(?:\.\d+)?)", p.name)
        if m:
            out.add(m.group(1))
    return out


def scan_pointers(files: list[Path]) -> list[dict]:
    allowed_sec = allowed_sections(files)
    findings = []
    for p in files:
        for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for m in PART_RE.finditer(line):
                n = cn_num(m.group(1))
                if n is None or not 1 <= n <= 3:
                    findings.append({
                        "level": "L0", "kind": "指针", "file": p.name,
                        "line": lineno, "quote": m.group(0),
                        "why": f"本书只有第一至第三篇（另有开篇与终篇），没有“{m.group(0)}”。",
                    })
            for m in CHAP_RE.finditer(line):
                n = int(m.group(1))
                if not 1 <= n <= 21:
                    findings.append({
                        "level": "L1", "kind": "章号", "file": p.name,
                        "line": lineno, "quote": m.group(0),
                        "why": f"主线章号应在 1–21；“{m.group(0)}”超出范围（外部书引用请人工确认）。",
                    })
            for m in SEC_RE.finditer(line):
                sec = m.group(1)
                if sec not in allowed_sec:
                    findings.append({
                        "level": "L0", "kind": "节号", "file": p.name,
                        "line": lineno, "quote": m.group(0),
                        "why": f"本书没有 §{sec}（允许：{', '.join(sorted(allowed_sec))}）。",
                    })
    return findings


def norm_gloss(s: str) -> str:
    return re.sub(r"[\s，。；：、（）()“”\"'`]+", "", s)


def scan_glosses(files: list[Path]) -> tuple[list[dict], dict[str, list[dict]]]:
    table: dict[str, list[dict]] = defaultdict(list)
    for p in files:
        for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for m in GLOSS_RE.finditer(line):
                term, gloss = m.group(1).strip(), m.group(2).strip()
                table[term].append({"file": p.name, "line": lineno,
                                    "gloss": gloss, "norm": norm_gloss(gloss)})
    findings = []
    for term, rows in sorted(table.items()):
        norms = {r["norm"] for r in rows}
        if len(norms) <= 1:
            continue
        where = "；".join(f"{r['file']}:{r['line']} {r['gloss']}" for r in rows[:4])
        findings.append({
            "level": "L1", "kind": "术语多释", "file": rows[0]["file"],
            "line": rows[0]["line"], "quote": term,
            "why": f"同一术语出现 {len(norms)} 种不同括注：{where}",
        })
    return findings, table


def scan_numbers(files: list[Path]) -> list[dict]:
    rows = []
    for p in files:
        for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for m in NUM_UNIT_RE.finditer(line):
                s = max(0, m.start() - 16)
                e = min(len(line), m.end() + 16)
                rows.append({"file": p.name, "line": lineno,
                             "number": m.group(0), "context": line[s:e].strip()})
    return rows


def render_report(files: list[Path], pointers: list[dict], glosses: list[dict]) -> str:
    l0 = [f for f in pointers if f["level"] == "L0"]
    l1 = [f for f in pointers if f["level"] == "L1"] + glosses
    out = [
        "# consistency_scan 报告",
        "",
        f"扫描：{len(files)} 个单元；指针/术语候选 {len(l0) + len(l1)} 条"
        f"（L0 {len(l0)}｜L1 {len(l1)}）。",
        "",
    ]
    if not l0 and not l1:
        out.append("未发现候选。")
        return "\n".join(out) + "\n"
    out += ["| 级别 | 类型 | 位置 | 引文 | 为什么 |", "| --- | --- | --- | --- | --- |"]
    for f in l0 + l1:
        out.append(f"| {f['level']} | {f['kind']} | {f['file']}:{f['line']} | {f['quote']} | {f['why']} |")
    out.append("")
    return "\n".join(out)


def write_tsv(path: Path, headers: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["\t".join(headers)]
    for r in rows:
        lines.append("\t".join(str(r.get(h, "")).replace("\t", " ") for h in headers))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", help="章文件；省略则需 --series")
    ap.add_argument("--series", action="store_true")
    ap.add_argument("--out-dir", help="写出 consistency.md / terms.tsv / numbers.tsv")
    ap.add_argument("--numbers", action="store_true", help="同时生成数字台账")
    ap.add_argument("--strict", action="store_true", help="有 L0 或术语多释时退出 1")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    files = [Path(p) for p in args.files]
    if args.series:
        files = series_units()
    if not files:
        ap.print_help()
        return 2
    missing = [str(p) for p in files if not p.is_file()]
    if missing:
        print("找不到文件：" + "、".join(missing), file=sys.stderr)
        return 2

    pointers = scan_pointers(files)
    glosses, table = scan_glosses(files)
    report = render_report(files, pointers, glosses)
    if args.out_dir:
        out = Path(args.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "consistency.md").write_text(report, encoding="utf-8", newline="\n")
        term_rows = [{"term": t, **r} for t, rows in table.items() for r in rows]
        write_tsv(out / "terms.tsv", ["term", "file", "line", "gloss"], term_rows)
        if args.numbers:
            write_tsv(out / "numbers.tsv", ["file", "line", "number", "context"],
                      scan_numbers(files))
        print(f"consistency_scan：{len(files)} 个单元，{len(pointers) + len(glosses)} 条候选 → {out}")
    else:
        print(report, end="")

    bad = any(f["level"] == "L0" for f in pointers) or bool(glosses)
    if args.strict and bad:
        return 1
    return 0


def selftest() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "§1-a.md").write_text(
            "这是第一篇。\n这里写第四篇。\n参见 §1 和 §99。\n"
            "**对齐**（把表示对到同一空间）。\n", encoding="utf-8")
        (d / "§2-b.md").write_text(
            "**对齐**（让行为符合人类偏好）。\n", encoding="utf-8")
        files = [d / "§1-a.md", d / "§2-b.md"]
        p = scan_pointers(files)
        g, _ = scan_glosses(files)
        checks = {
            "part": any("第四篇" in x["quote"] for x in p),
            "section": any("§99" in x["quote"] for x in p),
            "gloss": any(x["quote"] == "对齐" for x in g),
        }
        if not all(checks.values()):
            print(f"consistency_scan selftest: FAIL {checks}")
            return 1
    print("consistency_scan selftest: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
