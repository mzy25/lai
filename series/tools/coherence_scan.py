#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""coherence_scan：局部衔接候选扫描（只定位，不判罚）。

用法：
    python3 series/tools/coherence_scan.py "series/§N-….md"
    python3 series/tools/coherence_scan.py "series/§N-….md" --out series/.tmp/§N.coherence.md
    python3 series/tools/coherence_scan.py --selftest

检查六类候选：
  1. 段首指代：段落首句以“这/那/它/其/该/此…”开头，提示回看先行词。
  2. 上下文引用：上一节/下一节/刚才/此前等，检查是否落在无对应节的边界。
  3. 孤岛术语：全章只出现一次的加粗术语，提示“引入后未复用”。
  4. 相邻段重复开头：相邻两段首句共享同一 4 字开头。
  5. 超长段落：超过 --max-paragraph 字的正文段。
  6. 无句末标点的长段：超过 80 字却没有“。！？”。

输出是候选清单，不是判决。退出码恒 0（文件错误除外）。
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

from prose_common import (DASH, PRONOUN_STARTS, SENT_END, TRANSITIONS,
                          bold_terms, paragraphs, prefix_of, read_lines,
                          sections, split_sentences)


def scan(path: Path, max_paragraph: int = 600) -> list[dict]:
    lines = read_lines(path)
    paras = paragraphs(lines)
    secs = sections(lines)
    findings: list[dict] = []

    def add(kind: str, start: int, msg: str, context: str = "") -> None:
        findings.append({"kind": kind, "line": start, "msg": msg, "context": context})

    # 1. 段首指代
    for i, p in enumerate(paras):
        sents = split_sentences(p["text"])
        if not sents:
            continue
        first = sents[0].lstrip()
        hit = next((w for w in PRONOUN_STARTS if first.startswith(w)), None)
        if hit:
            prev = split_sentences(paras[i - 1]["text"]) if i else []
            add("段首指代", p["start"],
                f"首句以“{hit}”开头：{prefix_of(first, 52)}",
                f"上一段末句：{prefix_of(prev[-1], 52)}" if prev else "（本章首段）")

    # 2. 上下文引用
    section_titles = [s["title"] for s in secs]
    for i, p in enumerate(paras):
        first = split_sentences(p["text"])[0] if split_sentences(p["text"]) else ""
        sec_idx = next((j for j, s in enumerate(secs)
                        if s["start"] <= p["start"] <= s["end"]), 0)
        if "上一节" in p["text"] and sec_idx <= 1:
            add("上下文引用", p["start"], "“上一节”出现在本章第一节之前/首节",
                f"所在节：{section_titles[sec_idx] if sec_idx < len(section_titles) else '？'}")
        if "下一节" in p["text"] and sec_idx >= len(secs) - 1:
            add("上下文引用", p["start"], "“下一节”出现在本章最后一节",
                f"所在节：{section_titles[sec_idx] if sec_idx < len(section_titles) else '？'}")
        if ("刚才" in p["text"] or "此前" in p["text"]) and i == 0:
            add("上下文引用", p["start"], "“刚才/此前”出现在本章首段", prefix_of(first, 52))

    # 3. 孤岛术语：加粗引入，但全章正文只出现一次（含未加粗复用）
    full_text = "\n".join(p["text"] for p in paras)
    term_hits: dict[str, list[int]] = defaultdict(list)
    for p in paras:
        for t in bold_terms(p["text"]):
            term_hits[t].append(p["start"])
    for term, hits in sorted(term_hits.items()):
        if len(term) >= 2 and full_text.count(term) == 1:
            para_text = next((p["text"] for p in paras if p["start"] == hits[0]), "")
            def_like = bool(re.search(r"\*\*" + re.escape(term) + r"\*\*\s*[：:是指]",
                                      para_text))
            add("孤岛术语", hits[0], f"加粗术语全章只出现一次：{term}",
                "定义式点名（后文不复用可接受）" if def_like
                else "若只是点名/标签可忽略；若是新概念，后文应有复用或回指")

    # 4. 相邻段重复开头
    for i in range(1, len(paras)):
        a = split_sentences(paras[i - 1]["text"])
        b = split_sentences(paras[i]["text"])
        if not a or not b:
            continue
        pa = a[0].lstrip()[:4]
        pb = b[0].lstrip()[:4]
        if len(pa) == 4 and pa == pb and pa not in TRANSITIONS:
            add("重复开头", paras[i]["start"],
                f"相邻两段首句同以“{pa}”开头", f"上一段：{prefix_of(a[0], 44)}")

    # 5/6. 超长段与无句末标点
    for p in paras:
        chars = len("".join(p["text"].split()))
        if chars > max_paragraph:
            add("超长段落", p["start"], f"段长 {chars} 字（阈值 {max_paragraph}）",
                prefix_of(p["text"], 52))
        if chars > 80 and not SENT_END.search(p["text"]):
            add("无句末标点", p["start"], f"段长 {chars} 字，未见“。！？”",
                prefix_of(p["text"], 52))
    return findings


def render(path: Path, findings: list[dict], max_orphans: int = 12) -> str:
    lines = [f"# {path.stem} · coherence scan", ""]
    if not findings:
        lines.append("未发现候选。")
        return "\n".join(lines) + "\n"
    order = ["段首指代", "上下文引用", "孤岛术语", "重复开头", "超长段落", "无句末标点"]
    groups: dict[str, list[dict]] = defaultdict(list)
    for f in findings:
        groups[f["kind"]].append(f)
    for kind in order:
        items = groups.get(kind)
        if not items:
            continue
        lines += [f"## {kind}（{len(items)}）", ""]
        shown = items
        if kind == "孤岛术语" and max_orphans > 0:
            shown = items[:max_orphans]
        for f in shown:
            lines.append(f"- L{f['line']}：{f['msg']}")
            if f["context"]:
                lines.append(f"  - {f['context']}")
        if len(shown) < len(items):
            lines.append(f"- …另有 {len(items) - len(shown)} 条，用 --max-orphans 调整")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def selftest() -> int:
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="coh_"))
    f = tmp / "t.md"
    f.write_text(
        "# 测试\n\n"
        "第一段。这是上一段的结论。\n\n"
        "这一段以“这”开头。看它指什么。\n\n"
        "## 第一节\n\n"
        "下一节会讲。**只出现一次**。\n\n"
        "## 第二节\n\n"
        "下一节没有了吗。\n",
        encoding="utf-8")
    findings = scan(f)
    kinds = {x["kind"] for x in findings}
    ok = ("段首指代" in kinds and "上下文引用" in kinds
          and "孤岛术语" in kinds and "下一节" in render(f, findings))
    print("coherence_scan selftest:", "PASS" if ok else f"FAIL {kinds}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", nargs="?", help="章文件")
    ap.add_argument("--out", help="输出文件（默认 stdout）")
    ap.add_argument("--max-paragraph", type=int, default=600)
    ap.add_argument("--max-orphans", type=int, default=12,
                    help="孤岛术语最多列几条（默认 12；0 = 不限）")
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
    text = render(p, scan(p, args.max_paragraph), args.max_orphans)
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
