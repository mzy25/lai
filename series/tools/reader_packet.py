#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reader_packet：生成冷读包（本章正文＋截至本章之前的术语表）。

用法：
    python3 series/tools/reader_packet.py "series/§5-….md"
    python3 series/tools/reader_packet.py "§5" --out series/.tmp/review/§5.packet.md
    python3 series/tools/reader_packet.py "series/§5-….md" --include-side
    python3 series/tools/reader_packet.py --selftest

边界：
- 只给本章正文与“首现章在目标章之前”的术语；
- 默认排除支线术语；--include-side 才纳入目标章之前的支线；
- 不读答案、series/edit、审阅报告；
- 正文带行号；默认写 series/.tmp/review/<label>.packet.md。

说明：顺序按 profiles/chapters.json 的列表；支线目标章默认只取之前的主线，
支线读者的真实已读范围可能需要人工裁剪。
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERIES = HERE.parent
PROFILES = SERIES / "profiles" / "chapters.json"
TERMS = SERIES / "data" / "术语总账.tsv"
DEFAULT_OUT_DIR = SERIES / ".tmp" / "review"


def _read_chapters() -> list[dict]:
    data = json.loads(PROFILES.read_text(encoding="utf-8"))
    return data["chapters"]


def _resolve(chapters: list[dict], target: str) -> dict:
    path = Path(target)
    if path.is_file():
        name = path.name
        for chapter in chapters:
            if chapter["file"] == name:
                return chapter
        raise SystemExit(f"章节存在但不在 profiles/chapters.json：{name}")
    for chapter in chapters:
        if target in (chapter["label"], chapter.get("slug")):
            return chapter
    raise SystemExit(f"找不到章节：{target}")


def _prior(chapters: list[dict], target: dict, include_side: bool) -> list[dict]:
    out: list[dict] = []
    for chapter in chapters:
        if chapter["label"] == target["label"]:
            break
        if include_side or chapter["label"].startswith("§"):
            out.append(chapter)
    return out


def _terms() -> list[dict]:
    lines = [
        line for line in TERMS.read_text(encoding="utf-8").splitlines()
        if not line.startswith("#")
    ]
    return [row for row in csv.DictReader(lines, delimiter="\t") if row.get("名词")]


def _filter_terms(rows: list[dict], prior: list[dict]) -> list[dict]:
    labels = {chapter["label"] for chapter in prior}
    return [row for row in rows if row.get("首现章") in labels]


def _build(chapter: dict, terms: list[dict], include_side: bool) -> str:
    path = SERIES / chapter["file"]
    if not path.is_file():
        raise SystemExit(f"章文件不存在：{path}")
    text = path.read_text(encoding="utf-8")
    scope = "主线与支线" if include_side else "主线"
    lines = [
        f"# 冷读包：{chapter['label']}",
        "",
        f"你是一位第一次读这本书的读者。你只读过{scope}中目标章之前的部分；"
        "目标章及之后的内容都没读过。",
        "你只能读本文件。不要打开仓库其他文件，不要使用外部知识或猜测作者意图。",
        "",
        "读法：从章首逐段读；每段开头问“我刚翻开这一页，接得上吗？”",
        "只报告三类问题：",
        "1. 接不上：上一段/上一节留下的东西，这里没有接住。",
        "2. 不知道：术语、指代、前置知识没有落地，读者无法继续。",
        "3. 预期落空：前文承诺或本章开头承诺的东西，读到这里没有兑现。",
        "",
        "输出格式：最多 10 条，按阻塞程度排序；每条必须含："
        "类型 / 行号（L###）/ 原文引文 / 缺什么 / 阻塞或预览。",
        "后文同节或下一节马上解释的，标“预览”，不算阻塞；不确定时也标“预览”。",
        "不要评价文笔，不要给改写建议，不要报“写得很好”的地方。",
        "",
        f"## 已读术语表（截至 {chapter['label']} 之前，不含本章新词；共 {len(terms)} 条）",
        "",
        "| 名词 | 首现章 | 备注 |",
        "|---|---|---|",
    ]
    for row in terms:
        name = (row.get("名词") or "").replace("|", "\\|")
        note = (row.get("备注") or "").replace("|", "\\|")
        lines.append(f"| {name} | {row.get('首现章', '')} | {note} |")
    lines += ["", "## 本章正文（行号已标注）", ""]
    for number, line in enumerate(text.splitlines(), 1):
        lines.append(f"L{number} | {line}")
    return "\n".join(lines) + "\n"


def _selftest() -> int:
    chapters = _read_chapters()
    rows = _terms()
    for label in ("§5", "§13", "§21"):
        chapter = _resolve(chapters, label)
        prior = _prior(chapters, chapter, include_side=False)
        labels = {item["label"] for item in prior}
        selected = _filter_terms(rows, prior)
        if not selected:
            raise SystemExit(f"selftest: {label} 没有选到术语")
        if any(row["首现章"] == label for row in selected):
            raise SystemExit(f"selftest: {label} 泄漏本章新词")
        if any(row["首现章"] not in labels for row in selected):
            raise SystemExit(f"selftest: {label} 选中了未读术语")
        packet = _build(chapter, selected, include_side=False)
        if "L1 |" not in packet:
            raise SystemExit(f"selftest: {label} 正文没有行号")
        if packet.splitlines()[0] != f"# 冷读包：{label}":
            raise SystemExit(f"selftest: {label} 标题错误")
    print("reader_packet selftest: PASS（§5/§13/§21；目标章术语 0 泄漏）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("chapter", nargs="?", help="章文件路径，或 §N / slug")
    ap.add_argument("--out", help="输出文件；默认 series/.tmp/review/<label>.packet.md")
    ap.add_argument("--include-side", action="store_true", help="纳入目标章之前的支线术语")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()
    if not args.chapter:
        ap.error("需要章文件或章节标签")

    chapters = _read_chapters()
    chapter = _resolve(chapters, args.chapter)
    prior = _prior(chapters, chapter, args.include_side)
    terms = _filter_terms(_terms(), prior)
    packet = _build(chapter, terms, args.include_side)

    out = Path(args.out) if args.out else DEFAULT_OUT_DIR / f"{chapter['label']}.packet.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(packet, encoding="utf-8")
    print(
        f"reader_packet：{chapter['label']} → {out}"
        f"（术语 {len(terms)} 条，输出 {len(packet.splitlines())} 行）"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
