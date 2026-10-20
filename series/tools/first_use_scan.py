#!/usr/bin/env python3
"""first_use_scan：首现名词登记的机械核对（写作声音"审者视角"第 2 条的底座）。

双向核对 edit 档案"首现名词登记"表与正文：
  ERROR 漏登记   正文加粗术语（≤12 字）未在登记表中
  ERROR 幽灵登记 登记表中的词在正文不存在
  ERROR 漏 gloss  登记 gloss 的关键词在正文全文未出现
  WARN  延后     gloss 出现但距首现 >250 字（铺垫断档，人工判断）

加 --ledger（默认自动找 edit 档案同目录的 术语总账.tsv）后三向核对总账：
  ERROR 漏登记   总账首现章＝本章，正文出现但未登记
  WARN  提前裸现 总账首现章晚于本章，正文提前出现（指针式提及人工豁免）
  WARN  总账漏记 登记表的词未入总账

gloss 为"—"或含"结构命名"的行跳过 gloss 检查（名词先用/结构命名免检）。
退出码：0 干净（可有 WARN）；1 有 ERROR；2 用法错误。--strict 时 WARN 也退 1。

用法：
  python series/tools/first_use_scan.py series/§0.1-大模型是怎么训练出来的.md
  python series/tools/first_use_scan.py <章.md> --edit <档案.md> [--ledger <总账.tsv>]
         [--no-ledger] [--strict] [--selftest]
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

BOLD = re.compile(r"\*\*([^*]+)\*\*")
DIST_WARN = 250

# 体例标签固定不加粗：结构由排版与位置承担，强调是编辑在指路，干扰读者
# 注意力（本章问题/回望三题/记住一句话/它怎么运转/这套说法的边界/下章问题）。
# 若未来确需恢复模板加粗标签，在此登记白名单；空集 = 一律检查。
FRAME_LABELS: set = set()

# 安抚与政策预告腔（WARN 级；写作声音自检第 3 条）
VOICE_PATTERNS = ["不必担心", "不需要全懂", "不需要懂", "不用懂", "会有解释",
                  "先混个脸熟", "混个脸熟", "遇到了别停", "先记住名字", "先知道名字"]


def parse_registry(edit_text: str) -> list[dict]:
    """edit 档案"首现名词登记"节 → [{terms, gloss, owner}]。"""
    m = re.search(r"^##\s*三、首现名词登记(.+?)(?=^##\s|\Z)", edit_text, re.M | re.S)
    if not m:
        return []
    rows = []
    for line in m.group(1).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0] in ("名词", "---") or set(cells[0]) <= {"-", " "}:
            continue
        terms = [t.strip() for t in re.split(r"[／/、]", cells[0]) if t.strip()]
        rows.append({"terms": terms, "gloss": cells[2], "owner": cells[3]})
    return rows


def gloss_key(gloss: str) -> str:
    g = re.sub(r"（[^）]*）", "", gloss)
    g = re.sub(r"[，。；：、\s]", "", g)
    return g[:4]


# ---- 术语总账（跨章知识状态核对的机械底座） ----
# edit/术语总账.tsv：全系列首现名词唯一登记处。三向核对：
#   ERROR 漏登记   总账首现章＝本章，正文出现但未入本章登记表
#   WARN  提前裸现 总账首现章晚于本章，正文提前出现（指针式提及由人工裁决豁免）
#   WARN  总账漏记 本章登记表的词未入总账（符号类如 ▽ 跳过）

WORD = re.compile(r"[A-Za-z0-9一-鿿]")


def chapter_key(uid: str) -> tuple:
    """§0.1 → (0, 0, 1)；§15 → (0, 15, 0)；T2 → (1, 2, 0)。§ 先于 T。"""
    m = re.fullmatch(r"§(\d+)(?:\.(\d+))?", uid)
    if m:
        return (0, int(m.group(1)), int(m.group(2) or 0))
    m = re.fullmatch(r"T(\d+)", uid)
    if m:
        return (1, int(m.group(1)), 0)
    return (9, 0, 0)


def load_ledger(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#") or line.startswith("名词"):
            continue
        cells = line.split("\t")
        if len(cells) >= 2 and cells[0].strip() and WORD.search(cells[0]):
            rows.append({"term": cells[0].strip(), "uid": cells[1].strip()})
    return rows


def scan(chapter: Path, edit: Path, strict: bool = False,
         ledger: Path | None = None, uid: str = ""):
    text = chapter.read_text(encoding="utf-8")
    rows = parse_registry(edit.read_text(encoding="utf-8"))
    registered = {t: r for r in rows for t in r["terms"]}
    structural = lambda r: r["gloss"] in ("—", "") or "结构命名" in r["gloss"]

    errors, warns = [], []

    for pat in VOICE_PATTERNS:
        if pat in text:
            warns.append(f"安抚腔：出现「{pat}」（写作声音自检第 3 条，删）")

    bold_terms = {b.strip() for b in BOLD.findall(text) if 1 < len(b.strip()) <= 12}
    gloss_text = "".join(r["gloss"] for r in rows)
    named = set(registered) | FRAME_LABELS
    for t in sorted(bold_terms - named):
        if any(p in t for p in "，。：；"):
            continue  # 整句强调，非术语
        if t in gloss_text:
            continue  # 作为某词的 gloss 出现（如"调模型的参数"是"训练"的定义）
        errors.append(f"漏登记：正文加粗「{t}」未入首现名词登记")

    for t, r in sorted(registered.items()):
        if t not in text:
            errors.append(f"幽灵登记：「{t}」不在正文中")
            continue
        if structural(r):
            continue
        key = gloss_key(r["gloss"])
        if not key:
            continue
        pos = text.find(t)
        if key not in text:
            errors.append(f"漏 gloss：「{t}」的 gloss「{r['gloss']}」全文未现")
        elif abs(text.find(key) - pos) > DIST_WARN:
            warns.append(f"延后：「{t}」首现于 {pos} 字处，gloss「{key}」距 "
                         f"{abs(text.find(key) - pos)} 字")

    if ledger is not None and ledger.exists():
        entries = load_ledger(ledger)
        in_ledger = {e["term"] for e in entries}
        my_key = chapter_key(uid)
        for t in sorted(registered):
            if WORD.search(t) and t not in in_ledger:
                warns.append(f"总账漏记：「{t}」在登记表但未入术语总账")
        for e in entries:
            t = e["term"]
            if t not in text or t in registered:
                continue
            k = chapter_key(e["uid"])
            if k == my_key:
                errors.append(f"漏登记：「{t}」总账首现章＝本章，正文出现但未登记")
            elif k > my_key:
                warns.append(f"提前裸现：「{t}」总账首现为 {e['uid']}，本章提前出现"
                             f"（指针式提及可人工豁免）")

    return errors, warns


def selftest() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="fus_"))
    ch = tmp / "c.md"
    ch.write_text("# 章\n\n**预测**是模型给出的答案，梯度再说。\n\n**梯度**的方向最陡。\n",
                  encoding="utf-8")
    ed = tmp / "e.md"
    ed.write_text("## 三、首现名词登记\n\n| 名词 | 首现处 | gloss | 主责 |\n"
                  "| --- | --- | --- | --- |\n"
                  "| 预测 | 首段 | 模型给出的答案 | §0.1 |\n"
                  "| 幽灵词 | 某处 | 不存在 | §9 |\n", encoding="utf-8")
    errors, warns = scan(ch, ed)
    ok = (any("梯度" in e and "漏登记" in e for e in errors)
          and any("幽灵词" in e for e in errors)
          and not any("预测" in e for e in errors))
    ch2 = tmp / "c2.md"
    ch2.write_text("# 章\n\n**损失**很大。\n", encoding="utf-8")
    ed2 = tmp / "e2.md"
    ed2.write_text("## 三、首现名词登记\n\n| 名词 | 首现处 | gloss | 主责 |\n"
                   "| --- | --- | --- | --- |\n"
                   "| 损失 | 首段 | 错误程度 | §2 |\n", encoding="utf-8")
    errors2, _ = scan(ch2, ed2)
    ok &= any("漏 gloss" in e for e in errors2)
    print("first_use_scan selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="首现名词登记双向核对＋术语总账三向核对")
    ap.add_argument("chapter", nargs="?", help="章节 md")
    ap.add_argument("--edit", help="edit 档案 md（默认 ../edit/<同名>.edit.md）")
    ap.add_argument("--ledger", help="术语总账 tsv（默认 edit 档案同目录的 术语总账.tsv）")
    ap.add_argument("--no-ledger", action="store_true", help="关闭总账核对")
    ap.add_argument("--strict", action="store_true", help="WARN 也退 1")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.chapter:
        ap.print_help()
        return 2
    chapter = Path(args.chapter)
    uid = chapter.stem.split("-")[0]  # §0.1-标题.md → §0.1.edit.md
    if args.edit:
        edit = Path(args.edit)
    else:
        edit = chapter.parent / "edit" / f"{uid}.edit.md"
    if not chapter.exists() or not edit.exists():
        print(f"文件不存在：{chapter if not chapter.exists() else edit}", file=sys.stderr)
        return 2
    ledger = None
    if not args.no_ledger:
        ledger = Path(args.ledger) if args.ledger else edit.parent / "术语总账.tsv"
        if not ledger.exists():
            ledger = None
    errors, warns = scan(chapter, edit, args.strict, ledger=ledger, uid=uid)
    for e in errors:
        print(f"ERROR {e}")
    for w in warns:
        print(f"WARN  {w}")
    print(f"first_use_scan：{len(errors)} 错 / {len(warns)} 警")
    return 1 if (errors or (args.strict and warns)) else 0


if __name__ == "__main__":
    sys.exit(main())
