#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""answer_mirror_check：章末答案块 × 正文的镜像对账。

用法：
    python3 series/tools/answer_mirror_check.py "series/§N-….md"
    python3 series/tools/answer_mirror_check.py "series/§N-….md" --strict
    python3 series/tools/answer_mirror_check.py --selftest

做法：
  - 抽出 <details> 中含“答案”/“先写，再看”的块；
  - 答案块里的显著数字、加粗术语、引号短语，逐个回正文找字面；
  - 报告“答案有、正文无”的条目（正文有、答案无默认不报，避免噪音）。

只定位，不判对错；默认退出码 0，--strict 有候选才退 1。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from prose_common import (bold_terms, contains_text, normalize_number,
                          quoted_terms, read_lines, significant_numbers)


def extract_blocks(lines: list[str]) -> tuple[list[dict], list[str]]:
    """返回 (答案块列表, 正文行)。答案块含 start/title/text。"""
    blocks: list[dict] = []
    body: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "<details>" not in line:
            body.append(line)
            i += 1
            continue
        start = i + 1
        block: list[str] = [line]
        i += 1
        while i < len(lines) and "</details>" not in lines[i]:
            block.append(lines[i])
            i += 1
        if i < len(lines):
            block.append(lines[i])
            i += 1
        text = "\n".join(block)
        summary = ""
        for bl in block:
            if "<summary>" in bl:
                summary = bl.split("<summary>", 1)[1].split("</summary>", 1)[0]
                break
        if ("答案" in summary) or ("先写，再看" in summary):
            content = text.split("</summary>", 1)[-1].replace("</details>", "")
            blocks.append({"start": start, "title": summary.strip(), "text": content})
        else:
            body.extend(block)
    return blocks, body


def check(path: Path) -> dict:
    lines = read_lines(path)
    blocks, body_lines = extract_blocks(lines)
    body_text = "\n".join(body_lines)
    body_nums = {normalize_number(x) for x in significant_numbers(body_text)}
    out = {"file": str(path), "blocks": len(blocks), "items": []}
    for b in blocks:
        answer_nums = significant_numbers(b["text"])
        nums = sorted(x for x in answer_nums if normalize_number(x) not in body_nums)
        terms = sorted(t for t in bold_terms(b["text"])
                       if not contains_text(t, body_text))
        quotes = sorted(q for q in quoted_terms(b["text"])
                        if not contains_text(q, body_text))
        if nums or terms or quotes:
            out["items"].append({
                "start": b["start"],
                "title": b["title"],
                "numbers": nums,
                "terms": terms,
                "quotes": quotes,
            })
    return out


def render(data: dict) -> str:
    lines = [f"# {Path(data['file']).stem} · answer mirror", ""]
    lines.append(f"答案块：{data['blocks']} 个；有候选的块：{len(data['items'])} 个。")
    lines.append("")
    if not data["items"]:
        lines.append("未发现“答案有、正文无”的数字/术语/引号短语。")
        return "\n".join(lines) + "\n"
    for item in data["items"]:
        lines.append(f"## L{item['start']} · {item['title']}")
        if item["numbers"]:
            lines.append("- 数字：正文未找到 " + "、".join(f"`{x}`" for x in item["numbers"]))
        if item["terms"]:
            lines.append("- 加粗术语：正文未找到 " + "、".join(f"`{x}`" for x in item["terms"]))
        if item["quotes"]:
            lines.append("- 引号短语：正文未找到 " + "、".join(f"`{x}`" for x in item["quotes"]))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def selftest() -> int:
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="mirror_"))
    f = tmp / "t.md"
    f.write_text(
        "# 测试\n\n正文只说 3.2 和 **旧术语**。\n\n"
        "<details>\n<summary>先写，再看：答案与去处</summary>\n\n"
        "答案里有 9.7、3.20 和 **新术语**，还有“引号短语”。\n\n</details>\n",
        encoding="utf-8")
    data = check(f)
    ok = (data["blocks"] == 1 and len(data["items"]) == 1
          and "9.7" in data["items"][0]["numbers"]
          and "3.20" not in data["items"][0]["numbers"]
          and "新术语" in data["items"][0]["terms"]
          and "引号短语" in data["items"][0]["quotes"]
          and "9.7" in render(data))
    print("answer_mirror_check selftest:", "PASS" if ok else f"FAIL {data}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", nargs="?", help="章文件")
    ap.add_argument("--strict", action="store_true", help="有候选时退出 1")
    ap.add_argument("--out", help="输出文件（默认 stdout）")
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
    data = check(p)
    text = render(data)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {out}")
    else:
        print(text, end="")
    return 1 if (args.strict and data["items"]) else 0


if __name__ == "__main__":
    sys.exit(main())
