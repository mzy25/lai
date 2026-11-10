#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""section_map：按 H2 输出正文质量地图。

用法：
    python3 series/tools/section_map.py "series/§N-….md"
    python3 series/tools/section_map.py "series/§N-….md" --out series/.tmp/§N.sections.md
    python3 series/tools/section_map.py "series/§N-….md" --json
    python3 series/tools/section_map.py --selftest

每节给：段落数、句数、均值/中位/P90、破折号、短句 run、首句。
随后给段落图：行号、字数、句数、首句，供反向提纲填“段落职责”。
只读，不判语义；报告默认写 stdout。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from prose_common import (measure_text, paragraphs, prefix_of, read_lines,
                          sections, split_sentences)


def build_map(path: Path) -> dict:
    lines = read_lines(path)
    secs = sections(lines)
    title = ""
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break
    out = {"file": str(path), "title": title, "sections": []}
    all_paras = paragraphs(lines)
    for sec in secs:
        sec_lines = lines[sec["start"] - 1:sec["end"]]
        text = "\n".join(
            line for line in sec_lines
            if line.strip() and not line.strip().startswith(("#", "|", "〔", "```"))
        )
        m = measure_text(text)
        paras = [p for p in all_paras
                 if sec["start"] <= p["start"] and p["end"] <= sec["end"]]
        p_rows = []
        for p in paras:
            sents = split_sentences(p["text"])
            p_rows.append({
                "start": p["start"],
                "end": p["end"],
                "chars": len("".join(p["text"].split())),
                "sents": len(sents),
                "first": prefix_of(sents[0], 46) if sents else "",
            })
        out["sections"].append({
            "title": sec["title"] or "（首节之前）",
            "start": sec["start"],
            "end": sec["end"],
            "paras": len(paras),
            "n": m["n"],
            "mean": m["mean"],
            "med": m["med"],
            "p90": m["p90"],
            "dashes": m["dashes"],
            "dens": m["dens"],
            "run": m["run"],
            "first": prefix_of(split_sentences(text)[0], 46) if m["n"] else "",
            "paragraphs": p_rows,
        })
    return out


def render(data: dict, summary: bool = False) -> str:
    lines = [f"# {data['title'] or Path(data['file']).stem} · section map", ""]
    lines.append("| 节 | 行 | 段 | 句 | 均值 | 中位 | P90 | 破折号 | 密度 | 短句 run | 首句 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for s in data["sections"]:
        lines.append(
            f"| {s['title']} | {s['start']}–{s['end']} | {s['paras']} | {s['n']} | "
            f"{s['mean']:.1f} | {int(s['med'])} | {s['p90']} | {s['dashes']} | "
            f"{s['dens']:.2f} | {s['run']} | {s['first']} |"
        )
    lines += ["", "> 节级读数用于相对比较；章级基准与句长带以 `sentence_stats.py` 为准。"]
    if summary:
        return "\n".join(lines).rstrip() + "\n"
    lines += ["", "## 段落图", ""]
    for s in data["sections"]:
        lines.append(f"### {s['title']}（{s['start']}–{s['end']}）")
        if not s["paragraphs"]:
            lines.append("")
            lines.append("（无正文段落）")
            lines.append("")
            continue
        lines.append("")
        lines.append("| 行 | 字数 | 句数 | 首句 |")
        lines.append("| --- | --- | --- | --- |")
        for p in s["paragraphs"]:
            lines.append(f"| {p['start']}–{p['end']} | {p['chars']} | {p['sents']} | {p['first']} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def selftest() -> int:
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="smap_"))
    f = tmp / "t.md"
    f.write_text(
        "# 测试章\n\n导语一句。\n\n## 第一节\n\n第一段第一句。第一段第二句。\n\n"
        "第二段很长，但只有一句。\n\n## 第二节\n\n| 表 | 不计 |\n\n"
        "第三段：一句。两句。\n",
        encoding="utf-8")
    data = build_map(f)
    ok = (data["title"] == "测试章" and len(data["sections"]) == 3
          and data["sections"][1]["paras"] == 2
          and data["sections"][2]["n"] == 2
          and "第一节" in render(data))
    print("section_map selftest:", "PASS" if ok else f"FAIL {data}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", nargs="?", help="章文件")
    ap.add_argument("--out", help="输出文件（默认 stdout）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--summary", action="store_true", help="只输出节汇总表，不含段落图")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.target:
        ap.print_help()
        return 2
    p = Path(args.target)
    if not p.is_file():
        print(f"章文件不存在：{p}", file=sys.stderr)
        return 2
    data = build_map(p)
    text = json.dumps(data, ensure_ascii=False, indent=2) if args.json else render(data, args.summary)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {out}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
