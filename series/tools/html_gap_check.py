#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""html_gap_check：raw HTML 块与 markdown 内容必须空行分隔（CommonMark 语义）。

背景（2026-11-27 M1）：CommonMark 的 HTML block 一直吞到空行；标签与内容紧贴时，
内部 markdown 不会被解析、标签也可能被吞。pandoc 宽松、CommonMark 严格，两引擎
在此分歧。本仓裁定：块级标签行与内容行之间必须隔一个空行（围栏内除外）。

用法：
    python3 series/tools/html_gap_check.py            # 查默认文件集（31 单元＋supply）
    python3 series/tools/html_gap_check.py A.md ...   # 指定文件
    python3 series/tools/html_gap_check.py --selftest

退出码：0 无违例；1 有违例；2 用法错误。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERIES = HERE.parent

BLOCK = r"div|details|summary|section|figure|table|pre|blockquote"
OPEN = re.compile(rf"^\s*<({BLOCK})(\s|>|/|$)", re.I)
CLOSE = re.compile(rf"^\s*</({BLOCK})>\s*$", re.I)
FENCE = re.compile(r"^\s*```")


def scan_text(text: str) -> list[tuple[int, str]]:
    """返回 [(行号, 说明)]；行号 1 基。"""
    lines = text.splitlines()
    fence = False
    issues: list[tuple[int, str]] = []

    def blank(i: int) -> bool:
        return 0 <= i < len(lines) and not lines[i].strip()

    def tag_start(i: int) -> bool:
        return 0 <= i < len(lines) and lines[i].lstrip().startswith("<")

    for i, ln in enumerate(lines):
        if FENCE.match(ln):
            fence = not fence
            continue
        if fence:
            continue
        if OPEN.match(ln) and not CLOSE.match(ln):
            if i + 1 < len(lines) and not blank(i + 1) and not tag_start(i + 1):
                issues.append((i + 1, "块级开标签后缺空行"))
        if CLOSE.match(ln):
            if i > 0 and not blank(i - 1) and not tag_start(i - 1):
                issues.append((i + 1, "块级关标签前缺空行"))
    return issues


def default_files() -> list[Path]:
    files: list[Path] = []
    for g in ("§*.md", "T*.md", "支线导言-*.md", "支线补页-*.md", "支线附录-*.md"):
        files.extend(sorted(SERIES.glob(g)))
    files.extend(sorted((SERIES / "supply").glob("*.md")))
    return files


def selftest() -> int:
    ok = True

    def case(name: str, text: str, want: int) -> None:
        nonlocal ok
        got = len(scan_text(text))
        good = got == want
        ok = ok and good
        print(("PASS " if good else "FAIL ") + name + ("" if good else f"（{got} != {want}）"))

    case("合规：标签与内容空行分隔", "<div>\n\n正文\n\n</div>\n", 0)
    case("开标签紧贴内容", "<div>\n正文\n\n</div>\n", 1)
    case("关标签紧贴内容", "<div>\n\n正文\n</div>\n", 1)
    case("单行块后紧贴内容", "<div>x</div>\n正文\n", 1)
    case("嵌套标签之间无需空行", "<details>\n<summary>标题</summary>\n\n正文\n\n</details>\n", 0)
    case("围栏内豁免", "```\n<div>\n正文\n</div>\n```\n", 0)
    print("html_gap_check 自测：" + ("all pass" if ok else "FAILED"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="显式文件清单（默认 31 单元＋supply）")
    ap.add_argument("--selftest", action="store_true", help="内置对照自测")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    files = [Path(f) for f in args.files] if args.files else default_files()
    total = 0
    for p in files:
        for ln, msg in scan_text(p.read_text(encoding="utf-8")):
            print(f"{p}:{ln}: {msg}")
            total += 1
    print(f"html_gap_check：{len(files)} 文件，{total} 违例")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
