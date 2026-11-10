#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""logic_lint：语病与逻辑候选扫描（只定位，不判罚）。

目标不是“扫得多”，而是“扫得准、能分诊”：
  - L0：明确的语病/逻辑错误模式，几乎不需要人工判断；
  - L1：高概率问题，需读上下文确认；
  - L2：候选，可能是正常表达，只供抽读。

当前只收高精度规则，避免把“都/一定/不是…而是”这类正常表达全量倒出。
语义论证（主张-依据是否匹配）仍归人工/LLM 审稿，不在此脚本假装判断。

用法：
    python3 series/tools/logic_lint.py "series/§N-….md"
    python3 series/tools/logic_lint.py --series
    python3 series/tools/logic_lint.py --series --format tsv --out series/.tmp/logic.tsv
    python3 series/tools/logic_lint.py --selftest

退出码：0 无 L0；1 有 L0（--strict 时）；2 用法/文件错误。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from prose_common import prefix_of, prose_items

ROOT = Path(__file__).resolve().parents[1]

# 允许的范围限定词：出现这些词时，绝对化断言不报。
SCOPE_RE = re.compile(
    r"在[^。；]{0,16}(下|中|上)|当前|目前|通常|一般|往往|多数|主要|可能|约|左右|"
    r"之一|部分|某些|特定|这套|本文|本书|本系列|截至|根据|按.*口径"
)
CERTAIN_SKIP_RE = re.compile(r"不一定|一定程度|一定范围|一定条件|一定比例|有一定")

RULES = [
    # (check, level, pattern, why, hint)
    (
        "约数重复", "L1",
        re.compile(r"(约|大约|将近|超过|不到|至少|最多)[^。；，]{0,14}\d[^。；，]{0,14}(左右|上下|多(?=人|个|次|年|张|条|步|层|倍|秒|分钟|小时|天|帧|轮|位|篇|页|块))"),
        "“约/将近/超过”与“左右/上下/多”重复，数量边界不清。",
        "保留一个边界词：约 100 人，或 100 人左右。",
    ),
    (
        "减少倍数", "L0",
        re.compile(r"(减少|降低|下降|缩小|便宜)[^。；]{0,10}\d+(?:\.\d+)?\s*倍"),
        "中文里“减少 N 倍”逻辑不成立/易歧义；倍数只能用于增加，减少用百分比或“降到 1/N”。",
        "改为“减少 N%”“降低到原来的 1/N”或“降为原来的 N 分之一”。",
    ),
    (
        "原因杂糅", "L0",
        re.compile(r"原因[^。；]{0,24}(造成|导致|引起)"),
        "“原因是……造成的/导致的”句式杂糅。",
        "改为“原因是……”或“由……造成”。",
    ),
    (
        "围绕杂糅", "L1",
        re.compile(r"围绕[^。；]{0,24}为中心|本着[^。；]{0,24}为原则"),
        "“围绕……为中心”“本着……为原则”句式杂糅。",
        "改为“以……为中心”“本着……原则”。",
    ),
    (
        "通过缺主语", "L1",
        re.compile(r"通过[^。；]{0,42}，\s*(使|让|令)"),
        "“通过……，使……”容易缺主语：是谁使？",
        "补出主语，或改为“通过……，模型/系统……”。",
    ),
    (
        "两面对一面", "L1",
        re.compile(r"(能否|是否|能不能|有没有|可否)[^。；]{0,32}(关键在于|取决于|是[^。；]{0,8}的关键)"),
        "前面是“能否/是否”两面，后面只给一面条件，逻辑不对应。",
        "改成两面都接（“能否……取决于是否……”），或前面改成单面。",
    ),
    (
        "条件句", "L2",
        re.compile(r"只要[^。；]{0,50}就|只有[^。；]{0,50}才"),
        "充分/必要条件句：确认“只要…就”是否被写成普遍规律，“只有…才”是否真必要。",
        "补范围（“在这套设定下/通常”），或改“如果…那么/需要…才”。",
    ),
    (
        "条件绝对", "L1",
        re.compile(r"只要[^。；]{0,50}(必然|一定|永远|从不|绝不)"),
        "“只要……就必然/一定/永远”把条件句写成了无例外规律，通常需要范围或概率限定。",
        "改为“可能/通常会”，或补“在这套设定下”。",
    ),
    (
        "条件范围", "L1",
        re.compile(r"(通常|往往|多数)[^。；]{0,50}只有[^。；]{0,50}才|只有[^。；]{0,50}才[^。；]{0,50}(通常|往往|多数)"),
        "同一句里“通常/往往”与“只有……才”强度不一致：前文说多数，后文写成唯一条件。",
        "把“只有……才”改成“通常要……才”，或删掉前面的“通常”。",
    ),
    (
        "虚假二分", "L2",
        re.compile(r"要么[^。；]{0,40}要么|非此即彼"),
        "二选一句式：确认是否还有第三选项。",
        "若有第三选项，改成“常见的有 A、B，另有 C”。",
    ),
]

ABS_RE = re.compile(r"所有|任何|一切|永远|从不|绝不|必然|一定|唯一|毫无")
ABS_SKIP_RE = re.compile(r"不一定|一定程度|一定范围|一定条件|一定比例|有一定|唯一.*之一")

# 召回模式专用：这些句式本身正常，只作为“可能虚假二分/对比过强”的抽读候选。
COMMON_RULES = [
    (
        "对比二分（抽读）", "L2",
        re.compile(r"不是[^。；]{0,60}而是|不是[^。；]{0,24}就是"),
        "“不是……而是/就是”可能把连续谱写成二选一；确认是否还有第三选项。",
        "若有第三选项，改成“常见的是 A，另有 B/C”。",
    ),
]


def series_units() -> list[Path]:
    files = sorted(ROOT.glob("§*.md"))
    files += sorted(ROOT.glob("T*.md"))
    files += sorted(ROOT.glob("支线*.md"))
    return files


def scan_text(text: str, label: str, include_absolute: bool = False,
              recall: bool = False) -> list[dict]:
    findings: list[dict] = []
    lines = text.splitlines()
    rules = RULES + (COMMON_RULES if recall else [])
    for lineno, line in prose_items(lines):
        for sent in re.split(r"[。！？]", line):
            s = sent.strip()
            if not s:
                continue
            for check, level, pat, why, hint in rules:
                m = pat.search(s)
                if not m:
                    continue
                if check == "虚假二分" and (s.rstrip().endswith("？") or "吗" in s[-6:]):
                    continue
                if check == "虚假二分" and "不是非此即彼" in s:
                    continue
                if check == "虚假二分" and ("两种结局" in s or "两类结局" in s or "常见两种" in s):
                    continue
                if check == "条件句" and ("约只要" in s or "只需要" in s):
                    continue
                findings.append({
                    "level": level, "check": check, "file": label,
                    "line": lineno, "quote": prefix_of(s, 72),
                    "why": why, "hint": hint,
                })
            if include_absolute and ABS_RE.search(s) and not SCOPE_RE.search(s) and not CERTAIN_SKIP_RE.search(s):
                findings.append({
                    "level": "L2", "check": "绝对化（抽读）", "file": label,
                    "line": lineno, "quote": prefix_of(s, 72),
                    "why": "出现“所有/任何/永远/必然/一定/唯一”等绝对词，句内没有范围限定。",
                    "hint": "确认这是定义/定理，还是漏了“在这套设定下/通常/多数/目前”。",
                })
    # 同一句同一检查只留一条
    seen = set()
    out = []
    for f in findings:
        key = (f["check"], f["file"], f["line"], f["quote"])
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def scan_files(files: list[Path], include_absolute: bool = False,
               recall: bool = False) -> list[dict]:
    out = []
    for p in files:
        out.extend(scan_text(p.read_text(encoding="utf-8"), p.name,
                             include_absolute, recall))
    return out


def render_md(findings: list[dict], files: list[Path], top: int = 25) -> str:
    l0 = [f for f in findings if f["level"] == "L0"]
    l1 = [f for f in findings if f["level"] == "L1"]
    l2 = [f for f in findings if f["level"] == "L2"]
    out = [
        "# logic_lint 报告",
        "",
        f"扫描：{len(files)} 个单元；候选 {len(findings)} 条（L0 {len(l0)}｜L1 {len(l1)}｜L2 {len(l2)}）。",
        "",
        "只定位，不判罚。L0 必读；L1 读上下文；L2 抽读，不按条数刷。",
        "",
    ]
    if l2:
        from collections import Counter
        counts = Counter(f["check"] for f in l2)
        out.append("L2 分布：" + "｜".join(f"{k} {v}" for k, v in counts.most_common()))
        out.append("")
    for level, rows in (("L0", l0), ("L1", l1)):
        if not rows:
            continue
        out += [f"## {level}（{len(rows)}）", "", "| 检查 | 位置 | 原句 | 为什么 | 怎么改 |", "| --- | --- | --- | --- | --- |"]
        for f in rows:
            out.append(
                f"| {f['check']} | {f['file']}:{f['line']} | {f['quote']} | {f['why']} | {f['hint']} |"
            )
        out.append("")
    if l2:
        shown = l2[:top]
        out += [f"## L2 抽读（前 {len(shown)} / {len(l2)}）", "",
                "| 检查 | 位置 | 原句 | 为什么 |", "| --- | --- | --- | --- |"]
        for f in shown:
            out.append(f"| {f['check']} | {f['file']}:{f['line']} | {f['quote']} | {f['why']} |")
        out.append("")
        if len(l2) > top:
            out.append(f"其余 {len(l2) - top} 条见 `--format tsv`。")
            out.append("")
    return "\n".join(out)


def render_tsv(findings: list[dict]) -> str:
    lines = ["level\tcheck\tfile\tline\tquote\twhy\thint"]
    for f in findings:
        lines.append("\t".join(str(f[k]).replace("\t", " ") for k in
                               ("level", "check", "file", "line", "quote", "why", "hint")))
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", help="章文件；省略则需 --series")
    ap.add_argument("--series", action="store_true", help="扫描全部 30 个单元")
    ap.add_argument("--format", choices=("md", "tsv", "json"), default="md")
    ap.add_argument("--out", help="写入文件；默认 stdout")
    ap.add_argument("--top", type=int, default=25, help="Markdown 里 L2 最多展示条数")
    ap.add_argument("--include-absolute", action="store_true",
                    help="额外列出“所有/任何/必然”等绝对化候选（默认关闭，噪声大）")
    ap.add_argument("--recall", action="store_true",
                    help="召回模式：加绝对化与“不是…而是”候选；机器面清单，不直接给人看")
    ap.add_argument("--strict", action="store_true", help="有 L0 时退出 1")
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

    findings = scan_files(files, args.include_absolute or args.recall, args.recall)
    if args.format == "json":
        text = json.dumps(findings, ensure_ascii=False, indent=2) + "\n"
    elif args.format == "tsv":
        text = render_tsv(findings)
    else:
        text = render_md(findings, files, args.top)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8", newline="\n")
        print(f"logic_lint：{len(files)} 个单元，{len(findings)} 条候选 → {args.out}")
    else:
        print(text, end="")

    if args.strict and any(f["level"] == "L0" for f in findings):
        return 1
    return 0


def selftest() -> int:
    sample = (
        "这是约 100 人左右的规模。\n"
        "成本减少了 3 倍。\n"
        "失败的原因是接口超时造成的。\n"
        "围绕性能为中心做优化。\n"
        "通过增加缓存，使延迟下降。\n"
        "能否成功取决于投入。\n"
        "只要给足数据，模型就一定学会。\n"
        "通常只有换模型，才能解决这类问题。\n"
        "要么全量重训，要么放弃。\n"
        "所有模型都会过拟合。\n"
    )
    got = {f["check"] for f in scan_text(sample, "selftest.md", include_absolute=True)}
    want = {"约数重复", "减少倍数", "原因杂糅", "围绕杂糅", "通过缺主语",
            "两面对一面", "条件句", "条件绝对", "条件范围", "虚假二分", "绝对化（抽读）"}
    missing = want - got
    if missing:
        print("logic_lint selftest: FAIL 漏检 " + "、".join(sorted(missing)))
        return 1
    print(f"logic_lint selftest: PASS（{len(got)} 类）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
