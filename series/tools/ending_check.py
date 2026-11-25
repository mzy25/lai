#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ending_check：末节「回望与下一章」体例门禁（2026-11-11 末节严审）。

只管可计算项：引导句、提示括号、部件标签、电报式过渡、每题问号数、
题量范围（常规 3–6，长章 10–12）与回望长度。语义好坏仍归人工。

用法:
    python3 series/tools/ending_check.py            # 全系列
    python3 series/tools/ending_check.py <章.md>…   # 只查指定章
    python3 series/tools/ending_check.py --selftest # 夹具自检

§0.2 是查阅页：不写末节、不出题，NO_ENDING 中豁免。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERIES = HERE.parent

ENDING = re.compile(r"^## (回望与下一章|回望与收束|收束)$", re.M)
ITEM = re.compile(r"^\d+\. (.+)$")
LABEL = re.compile(r"(?:^|[。；\n])\s*(?:现象|规律|机制|边界|现状|取舍与边界)：")
LEAD = re.compile(r"先别翻答案|试着回答|把书合上|先答这十题")
HINT = re.compile(
    r"（(?=[^）]*(?:想不起来|想想|先问|先想|先分清|先写|先算|先回到|"
    r"逐元素|一个点积|查表那段|认小字|可以从|先标出|先各写|"
    r"没有调整这一步|别只报))[^）]*）"
)
TYPE_LABEL = re.compile(r"（知识点）|（逻辑链迁移）")
SHORT_NEXT = re.compile(r"下一章，[^。]{1,8}。")
LONG_CHAPTERS = {"§9", "§14", "§21"}
NO_ENDING = {"§0.2"}  # 查阅页：不写回望，也不出题
PROSE_LIMIT = 320
PROSE_LIMIT_LONG = 340
ITEM_LIMIT = 60


def _key(path: Path) -> str:
    name = path.name
    if name.startswith("§"):
        return "§" + re.match(r"§([\d.]+)", name).group(1)
    return name[:2]


def _ending_section(text: str) -> str | None:
    ms = list(ENDING.finditer(text))
    return text[ms[-1].start():] if ms else None


def _scan(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    key = _key(path)
    sec = _ending_section(text)
    if sec is None:
        return [] if key in NO_ENDING else ["缺末节（回望与下一章／回望与收束／收束）"]
    errors: list[str] = []
    if LEAD.search(sec):
        errors.append("出现引导句（先别翻答案／把书合上）")
    if HINT.search(sec.split("<details>")[0]):
        errors.append("出现提示括号")
    if TYPE_LABEL.search(sec):
        errors.append("出现题型标签（知识点／逻辑链迁移）")
    if SHORT_NEXT.search(sec):
        errors.append("出现电报式过渡「下一章，X。」")

    # 回望正文（到第一个编号项为止；§21 先截到「## 深究」）
    prose_src = sec.split("## 深究")[0]
    prose_src = re.split(r"^\d+\. ", prose_src, flags=re.M)[0]
    prose = re.sub(r"\s+", "", prose_src.split("\n", 1)[-1])
    limit = PROSE_LIMIT_LONG if key in LONG_CHAPTERS else PROSE_LIMIT
    if len(prose) > limit:
        errors.append(f"回望 {len(prose)} 字 > {limit}")
    if LABEL.search(prose_src):
        errors.append("回望出现部件标签（现象／规律／机制／边界／现状／取舍）")

    # 只收 details 之外的编号项；取最后一段连续编号（§21 的十题在 details 之后）
    in_details = False
    items: list[str] = []
    for line in sec.split("\n"):
        if "<details>" in line:
            in_details = True
            continue
        if "</details>" in line:
            in_details = False
            continue
        if not in_details:
            m = ITEM.match(line)
            if m:
                items.append(m.group(1))
    lo, hi = (10, 12) if key in LONG_CHAPTERS else (3, 6)
    if not (lo <= len(items) <= hi):
        errors.append(f"题量 {len(items)} 不在 {lo}–{hi} 范围")
    for i, item in enumerate(items, 1):
        q = item.count("？")
        if q != 1:
            errors.append(f"第 {i} 题问号 {q} 个（应为 1）")
        body = re.sub(r"（§[^）]*）", "", item)
        if len(body) > ITEM_LIMIT:
            errors.append(f"第 {i} 题 {len(body)} 字 > {ITEM_LIMIT}")
    if "先写，再看" in sec:
        errors.append("答案块摘要仍含「先写，再看」")
    return errors


def _selftest() -> int:
    import tempfile
    ok = """# T

## 回望与下一章

一句平常话。

1. 问一？
2. 问二？
3. 问三？
"""
    ok4 = """# T

## 回望与下一章

一句平常话。

1. 问一？
2. 问二？
3. 问三？
4. 问四？
"""
    too = """# T

## 回望与下一章

一句平常话。

1. 问一？
2. 问二？
3. 问三？
4. 问四？
5. 问五？
6. 问六？
7. 问七？
"""
    bad = """# T

## 回望与下一章

现象：一句。

先别翻答案，试着回答：

1. 问一？问二？
2. 问二？（想想再说。）
3. 问三？
4. 问四？
"""
    with tempfile.TemporaryDirectory() as td:
        okp = Path(td) / "ok.md"
        ok4p = Path(td) / "ok4.md"
        toop = Path(td) / "too.md"
        badp = Path(td) / "bad.md"
        okp.write_text(ok, encoding="utf-8")
        ok4p.write_text(ok4, encoding="utf-8")
        toop.write_text(too, encoding="utf-8")
        badp.write_text(bad, encoding="utf-8")
        e1 = _scan(okp)
        e4 = _scan(ok4p)
        et = _scan(toop)
        e2 = _scan(badp)
        good = (not e1 and not e4 and len(e2) >= 4
                and any("题量 7 不在 3–6 范围" in x for x in et))
        print(f"ending_check selftest: {'PASS' if good else 'FAIL'}")
        if not good:
            print("  ok errors:", e1)
            print("  ok4 errors:", e4)
            print("  too errors:", et)
            print("  bad errors:", e2)
        return 0 if good else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return _selftest()
    if a.files:
        files = [Path(f) for f in a.files]
    else:
        files = sorted(SERIES.glob("§*.md")) + sorted(SERIES.glob("T*.md"))
    bad = 0
    for p in files:
        if not p.is_file():
            print(f"文件不存在：{p}", file=sys.stderr)
            return 2
        errs = _scan(p)
        if errs:
            bad += 1
            print(f"✗ {p.name}")
            for e in errs:
                print(f"    {e}")
    print(f"ending_check：{len(files)} 章，{bad} 章未过")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
