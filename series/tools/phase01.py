#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""phase01：Phase 0/1 一键体检（只读，不改稿）。

把“先跑什么、看哪几条”压成一条命令：
  - logic_lint：语病/条件/二分/约数候选；
  - consistency_scan：第N部/第N章/§N 指针、术语多释；
  - 可选数字台账。

输出到 series/.tmp/phase01/（可随时清空），不进入硬门禁。

用法：
    python3 series/tools/phase01.py
    python3 series/tools/phase01.py --top 15 --numbers
    python3 series/tools/phase01.py --strict   # 有 L0/指针错/术语多释时退出 1
    python3 series/tools/phase01.py --selftest
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import consistency_scan as cs
import logic_lint as ll
from prose_common import paragraphs, prefix_of

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / ".tmp" / "phase01"


def run_gate() -> tuple[str, str]:
    try:
        p = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "series_check.py")],
                           cwd=ROOT.parent, capture_output=True, text=True, timeout=180)
        last = next((l for l in reversed((p.stdout + p.stderr).splitlines()) if l.strip()), "")
        return ("PASS" if p.returncode == 0 else "FAIL"), last
    except Exception as e:
        return "FAIL", str(e)[:120]


def write_coverage(out_dir: Path, files: list[Path], per_chapter: int) -> int:
    rows = []
    for p in files:
        paras = [x for x in paragraphs(p.read_text(encoding="utf-8").splitlines())
                 if len(re.sub(r"\s", "", x["text"])) >= 80]
        if not paras:
            continue
        n = min(per_chapter, len(paras))
        if n == 1:
            idxs = [0]
        else:
            idxs = sorted({round(i * (len(paras) - 1) / (n - 1)) for i in range(n)})
        for i in idxs:
            q = paras[i]
            rows.append(f"| {p.name} | {q['start']} | {prefix_of(q['text'], 64)} |")
    text = [
        "# 覆盖抽样（不是判决）",
        "",
        f"每章抽 {per_chapter} 段，共 {len(rows)} 段。逐段回答四问：",
        "",
        "1. 这段的主张是什么（一句话）？",
        "2. 依据在哪（定义/定理/实验/例子/作者判断）？",
        "3. 有没有指代不明、条件过强、因果倒置、范围漂移？",
        "4. 读者会误解成什么？",
        "",
        "| 章 | 行 | 首句 |",
        "| --- | --- | --- |",
        *rows,
        "",
    ]
    (out_dir / "coverage.md").write_text("\n".join(text), encoding="utf-8", newline="\n")
    return len(rows)


def build(out_dir: Path, top: int, include_absolute: bool, numbers: bool,
          gates: bool = False, recall: bool = False, coverage: int = 0) -> dict:
    files = ll.series_units()
    findings = ll.scan_files(files, include_absolute or recall, recall)
    pointers = cs.scan_pointers(files)
    glosses, table = cs.scan_glosses(files)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "logic.md").write_text(ll.render_md(findings, files, top),
                                     encoding="utf-8", newline="\n")
    (out_dir / "logic.tsv").write_text(ll.render_tsv(findings),
                                      encoding="utf-8", newline="\n")
    (out_dir / "consistency.md").write_text(cs.render_report(files, pointers, glosses),
                                           encoding="utf-8", newline="\n")
    term_rows = [{"term": t, **r} for t, rows in table.items() for r in rows]
    cs.write_tsv(out_dir / "terms.tsv", ["term", "file", "line", "gloss"], term_rows)
    if numbers:
        cs.write_tsv(out_dir / "numbers.tsv", ["file", "line", "number", "context"],
                     cs.scan_numbers(files))
    cov = write_coverage(out_dir, files, coverage) if coverage > 0 else 0
    if recall:
        (out_dir / "candidates.tsv").write_text(ll.render_tsv(findings),
                                               encoding="utf-8", newline="\n")

    l0 = [f for f in findings if f["level"] == "L0"]
    l1 = [f for f in findings if f["level"] == "L1"]
    l2 = [f for f in findings if f["level"] == "L2"]
    p0 = [f for f in pointers if f["level"] == "L0"]
    p1 = [f for f in pointers if f["level"] == "L1"]

    report = [
        "# Phase 0/1 体检",
        "",
        f"单元 {len(files)}｜语病/逻辑 L0 {len(l0)}｜L1 {len(l1)}｜L2 {len(l2)}"
        f"｜指针 L0 {len(p0)}｜L1 {len(p1)}｜术语多释 {len(glosses)}",
        "",
        "先读 L0/L1；L2 只抽读，不按条数刷。语义论证（主张-依据是否匹配）仍需人工/LLM 审稿。",
        "",
    ]
    if gates:
        status, note = run_gate()
        report += ["## Phase 0 基线", "", f"- `series_check`：**{status}**（{note}）", ""]
    if l0 or l1 or p0 or p1 or glosses:
        report += ["## 先看这些", "", "| 级别 | 类型 | 位置 | 引文 | 为什么 |",
                   "| --- | --- | --- | --- | --- |"]
        for f in l0 + l1 + p0 + p1 + glosses:
            report.append(
                f"| {f['level']} | {f.get('check', f.get('kind', ''))} | "
                f"{f['file']}:{f['line']} | {f['quote']} | {f['why']} |")
        report.append("")
    else:
        report += ["未发现 L0/L1 候选。", ""]
    if l2:
        report += [f"## L2 抽读（前 {min(top, len(l2))} / {len(l2)}）", "",
                   "| 检查 | 位置 | 原句 | 为什么 |", "| --- | --- | --- | --- |"]
        for f in l2[:top]:
            report.append(f"| {f['check']} | {f['file']}:{f['line']} | {f['quote']} | {f['why']} |")
        report.append("")
    if cov:
        report += [f"## 覆盖抽样（{cov} 段）", "",
                   "见 `coverage.md`。它不是判决，逐段回答主张/依据/漏洞/读者误解四问；",
                   "用来发现规则扫不到的语义问题，并检验“零命中章”是否真的干净。", ""]
    report += [
        "## 下一步",
        "",
        "1. L0 逐条读原文；能修则修，不能修写明原因。",
        "2. L1/术语多释读上下文；只有能说出 reader consequence 才修。",
        "3. L2 只抽读 5–10 条，确认是否有系统性问题（如条件句过强）。",
        "4. 本报告不是判决；`logic_lint` 只做候选定位。",
        "",
    ]
    (out_dir / "report.md").write_text("\n".join(report), encoding="utf-8", newline="\n")
    return {"files": files, "findings": findings, "pointers": pointers,
            "glosses": glosses, "l0": l0, "l1": l1, "l2": l2, "p0": p0, "p1": p1,
            "coverage": cov}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT))
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--include-absolute", action="store_true")
    ap.add_argument("--numbers", action="store_true")
    ap.add_argument("--recall", action="store_true",
                    help="召回模式：加绝对化与“不是…而是”候选，写 candidates.tsv")
    ap.add_argument("--coverage", type=int, default=0,
                    help="每章抽 N 段写 coverage.md（建议 5），用于发现规则扫不到的语义问题")
    ap.add_argument("--gates", action="store_true", help="同时跑 series_check 结构门禁，记入 Phase 0 基线")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    r = build(Path(args.out_dir), args.top, args.include_absolute, args.numbers,
              args.gates, args.recall, args.coverage)
    print(f"Phase 0/1：{len(r['files'])} 单元｜L0 {len(r['l0'])}｜L1 {len(r['l1'])}"
          f"｜L2 {len(r['l2'])}｜指针 L0 {len(r['p0'])}｜术语多释 {len(r['glosses'])}")
    print(f"报告：{Path(args.out_dir) / 'report.md'}")
    bad = bool(r["l0"] or r["p0"] or r["glosses"])
    if args.strict and bad:
        return 1
    return 0


def selftest() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "phase01"
        r = build(out, top=5, include_absolute=False, numbers=False)
        assert (out / "report.md").is_file()
        assert (out / "logic.md").is_file()
        assert (out / "consistency.md").is_file()
        assert (out / "terms.tsv").is_file()
        print("phase01 selftest: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
