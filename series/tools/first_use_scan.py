#!/usr/bin/env python3
"""first_use_scan：首现名词登记与术语总账核对。

v0.3 的公开仓没有 edit/<章>.edit.md 档案，日常用 --ledger-only。总账语义：
「首现章」指该词的**首次正式处理**（定义、机制或主责节），不是第一次字面出现。
更早的字面出现分三类，必须显式登记，否则仍报错：

  指针   「见 §14」「归 §16」「下一章」等交叉引用
  预览   支线导言/附录对 T1–T4 的提前点名
  多义   同一字面在不同章节是不同意思（特征、对齐、调度……）

规则表：series/edit/术语扫描规则.tsv
  名词<TAB>范围<TAB>类别<TAB>理由
  范围 = global 或章号列表（§0.3、T2、支线导言，逗号/顿号分隔）
  类别 = 指针｜预览｜多义｜常用｜概念名｜退役

核对项（--ledger-only）：
  ERROR 总账首现章＝本章，正文未现
  ERROR 提前裸现（未被指针/预览/多义规则豁免）
  INFO  单字词不自动判定（值、键、矩、谱、秩……）
  INFO  退役/已并入/旧称条目跳过
  INFO  指针/预览/多义/常用/概念名豁免

退出码：0 无 ERROR；1 有 ERROR；2 用法错误。--strict 时 WARN 也退 1。
用法：
  python series/tools/first_use_scan.py <章.md> --ledger-only [--report] [--explain]
  python series/tools/first_use_scan.py --all --ledger-only --strict
  python series/tools/first_use_scan.py --all --ledger-only --no-context-exempt
  python series/tools/first_use_scan.py --check-rules
  python series/tools/first_use_scan.py <章.md> --edit <档案.md> [--ledger <总账.tsv>]

阅读顺序由 series/profiles/chapters.json 的 parts 顺序＋部内章数组顺序导出；
profile 不可用时退回旧硬编码。
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

BOLD = re.compile(r"\*\*([^*]+)\*\*")
DIST_WARN = 250
SERIES = Path(__file__).resolve().parent.parent

# 体例标签固定不加粗：结构由排版与位置承担，强调是编辑在指路，干扰读者
# 注意力（本章问题/回望三题/记住一句话/它怎么运转/这套说法的边界/下章问题）。
# 若未来确需恢复模板加粗标签，在此登记白名单；空集 = 一律检查。
FRAME_LABELS: set = set()

# 安抚与政策预告腔（WARN 级；写作声音自检第 3 条）
VOICE_PATTERNS = ["不必担心", "不需要全懂", "不需要懂", "不用懂", "会有解释",
                  "先混个脸熟", "混个脸熟", "遇到了别停", "先记住名字", "先知道名字"]

# 退役/合并/旧称：不参与首现核对。
RETIRED_NOTE = re.compile(r"退役|删除|已并入|旧称|勿再用|撤名|退休")
# 总账备注里已声明的指针：不再重复报提前。
DECLARED_POINTER = re.compile(r"指针|主责|首用早于|补登记|门牌级|定义在|首现")
# 出现位置附近有这些词，按指针/预览处理（不报 ERROR）。
POINTER_CTX = re.compile(
    r"§\s*\d|见\s*§|归\s*§|后文|下一章|前文|前面|回收|点名|细算|展开|"
    r"主场|地界|再说|接着|门牌|首用|定义在|先于|留过|说过|讲过|回头|"
    r"后章|稍后|下一节|后一节|后面|见第"
)
ALIAS_SPLIT = re.compile(r"[／/｜|]")
QUALIFIER = re.compile(r"（[^）]*）|\([^)]*\)")
WORD = re.compile(r"[A-Za-z0-9一-鿿]")

RULES_NAME = "术语扫描规则.tsv"
SKIP_KINDS = {"多义", "常用", "概念名"}
POINTER_KINDS = {"指针", "预览"}
_ORDER_CACHE: dict[str, tuple[int, int]] | None = None


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


def _profile_order() -> dict[str, tuple[int, int]]:
    """parts 顺序 + 部内章数组顺序 = 阅读顺序。失败时返回空，走硬编码兜底。"""
    global _ORDER_CACHE
    if _ORDER_CACHE is not None:
        return _ORDER_CACHE
    try:
        cfg = json.loads((SERIES / "profiles" / "chapters.json").read_text(encoding="utf-8"))
        parts = {p["id"]: i for i, p in enumerate(cfg["parts"])}
        _ORDER_CACHE = {
            c["label"]: (parts[c["part"]], i)
            for i, c in enumerate(cfg["chapters"])
            if c.get("part") in parts
        }
    except Exception:
        _ORDER_CACHE = {}
    return _ORDER_CACHE


def chapter_key(uid: str) -> tuple:
    """按阅读顺序排序：优先 profiles/chapters.json（parts 序＋部内数组序）。"""
    order = _profile_order()
    if uid in order:
        part, index = order[uid]
        return (part, index, 0)
    # 兜底：临时文件/独立运行/旧 profile。
    if uid.startswith("支线导言"):
        return (1, 0, 0)
    if uid.startswith("支线附录"):
        return (1, 1, 0)
    m = re.fullmatch(r"§(\d+)(?:\.(\d+))?", uid)
    if m:
        n, minor = int(m.group(1)), int(m.group(2) or 0)
        if n == 0:
            return (0, 0, minor)
        if n <= 9:
            return (0, n, 0)
        return (2, n, 0)
    m = re.fullmatch(r"T(\d+)", uid)
    if m:
        return (1, 2 + int(m.group(1)), 0)
    return (9, 0, 0)


def load_ledger(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#") or line.startswith("名词"):
            continue
        cells = line.split("\t")
        if len(cells) >= 2 and cells[0].strip() and WORD.search(cells[0]):
            rows.append({"term": cells[0].strip(), "uid": cells[1].strip(),
                         "note": "\t".join(cells[2:]).strip()})
    return rows


def term_aliases(term: str) -> list[str]:
    """Stable Diffusion／SD → 两个别名；站（路线义）→ 站。"""
    base = QUALIFIER.sub("", term).strip()
    parts = [p.strip() for p in ALIAS_SPLIT.split(base) if p.strip()]
    return list(dict.fromkeys([base, *parts]))


def load_rules(path: Path | None) -> list[dict]:
    if path is None or not path.is_file():
        return []
    rows = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#") or line.startswith("名词"):
            continue
        c = [x.strip() for x in line.split("\t")]
        if len(c) < 3:
            continue
        scope = c[1] if len(c) > 1 else "global"
        rows.append({"term": c[0], "scope": scope,
                     "kind": c[2], "reason": c[3] if len(c) > 3 else "",
                     "line": lineno})
    return rows


def check_rules(ledger: Path, rules_path: Path | None) -> list[str]:
    """规则表自检：术语在总账、章号有效、理由非空、无冲突。"""
    entries = load_ledger(ledger)
    known = {e["uid"] for e in entries} | {"支线导言", "支线附录"}
    profile = SERIES / "profiles" / "chapters.json"
    if profile.is_file():
        try:
            cfg = json.loads(profile.read_text(encoding="utf-8"))
            known |= {c["label"] for c in cfg.get("chapters", [])}
        except Exception:
            pass
    rules = load_rules(rules_path)
    problems = []
    valid_kinds = SKIP_KINDS | POINTER_KINDS | {"退役"}
    ledger_aliases = [set(term_aliases(e["term"])) for e in entries]
    for r in rules:
        where = f"术语扫描规则.tsv:{r['line']}"
        if r["kind"] not in valid_kinds:
            problems.append(f"{where}: 未知类别「{r['kind']}」")
        if not r["reason"]:
            problems.append(f"{where}: 缺理由")
        if not any(set(term_aliases(r["term"])) & a for a in ledger_aliases):
            problems.append(f"{where}: 名词不在术语总账：「{r['term']}」")
        if r["scope"] not in ("global", "*", "全局"):
            for ch in (x.strip() for x in re.split(r"[、,，/]", r["scope"])):
                if ch and ch not in known:
                    problems.append(f"{where}: 未知章号「{ch}」")
    for i, a in enumerate(rules):
        for b in rules[i + 1:]:
            if not (set(term_aliases(a["term"])) & set(term_aliases(b["term"]))):
                continue
            if a["kind"] == b["kind"]:
                continue
            sa, sb = a["scope"], b["scope"]
            ga, gb = sa in ("global", "*", "全局"), sb in ("global", "*", "全局")
            ca = {x.strip() for x in re.split(r"[、,，/]", sa)} if not ga else set()
            cb = {x.strip() for x in re.split(r"[、,，/]", sb)} if not gb else set()
            if ga or gb or (ca & cb):
                problems.append(
                    f"术语扫描规则.tsv:{a['line']}/{b['line']}: "
                    f"「{a['term']}」同类规则冲突（{a['kind']} vs {b['kind']}）")
    return problems


def _scope_ok(scope: str, uid: str) -> bool:
    if scope in ("global", "*", "全局"):
        return True
    chapters = [x.strip() for x in re.split(r"[、,，/]", scope) if x.strip()]
    return uid in chapters


def rule_entry(term: str, uid: str, rules: list[dict]) -> dict | None:
    aliases = set(term_aliases(term))
    for r in rules:
        if (set(term_aliases(r["term"])) & aliases) and _scope_ok(r["scope"], uid):
            return r
    return None


def rule_kind(term: str, uid: str, rules: list[dict]) -> str:
    r = rule_entry(term, uid, rules)
    return r["kind"] if r else ""


def occurrences(text: str, aliases: list[str]) -> list[tuple[int, int, str]]:
    """所有别名的出现位置及 ±40 字上下文。ASCII 词加词边界，避免 SD 命中 SD3。"""
    out: list[tuple[int, int, str]] = []
    for alias in aliases:
        if not alias:
            continue
        if re.search(r"[A-Za-z0-9]", alias):
            pat = re.compile(r"(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![A-Za-z0-9])")
            spans = [(m.start(), m.end()) for m in pat.finditer(text)]
        else:
            spans = []
            start = 0
            while True:
                i = text.find(alias, start)
                if i < 0:
                    break
                spans.append((i, i + len(alias)))
                start = i + len(alias)
        for i, j in spans:
            out.append((i, j, text[max(0, i - 40):j + 40].replace("\n", "⏎")))
    return out


def analyze(chapter: Path, edit: Path | None,
            ledger: Path | None = None, uid: str = "",
            rules_path: Path | None = None, context_exempt: bool = True) -> dict:
    text = chapter.read_text(encoding="utf-8")
    rows = parse_registry(edit.read_text(encoding="utf-8")) if edit is not None else []
    registered = {t: r for r in rows for t in r["terms"]}
    structural = lambda r: r["gloss"] in ("—", "") or "结构命名" in r["gloss"]

    errors: list[str] = []
    warns: list[str] = []
    explained: list[str] = []
    stats = Counter()

    for pat in VOICE_PATTERNS:
        if pat in text:
            warns.append(f"安抚腔：出现「{pat}」（写作声音自检第 3 条，删）")

    if edit is not None:
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

    if ledger is not None and ledger.is_file():
        entries = load_ledger(ledger)
        rules = load_rules(rules_path or ledger.parent / RULES_NAME)
        in_ledger = {e["term"] for e in entries}
        my_key = chapter_key(uid)
        for t in sorted(registered):
            if WORD.search(t) and t not in in_ledger:
                warns.append(f"总账漏记：「{t}」在登记表但未入术语总账")
        for e in entries:
            term = e["term"]
            aliases = term_aliases(term)
            rule = rule_entry(term, uid, rules)
            kind = rule["kind"] if rule else ""
            k = chapter_key(e["uid"])
            occ = occurrences(text, aliases)
            if RETIRED_NOTE.search(e.get("note", "")) or kind == "退役":
                if k == my_key or (k > my_key and occ):
                    stats["retired"] += 1
                    explained.append(f"{uid} {term} retired")
                continue
            # 单字词没有可靠词边界，自动扫描只会造成假阳性。
            if len(QUALIFIER.sub("", term).strip()) <= 1:
                if k == my_key or (k > my_key and occ):
                    stats["single"] += 1
                    explained.append(f"{uid} {term} single")
                continue
            if k < my_key:
                continue
            if k == my_key:
                if edit is None:
                    if not occ:
                        if kind in SKIP_KINDS:
                            stats["waived"] += 1
                            explained.append(f"{uid} {term} waived {kind} {rule.get('reason', '')}")
                        else:
                            errors.append(f"总账首现章＝本章，正文未现：「{term}」")
                elif term not in text or term in registered:
                    continue
                else:
                    errors.append(f"漏登记：「{term}」总账首现章＝本章，正文出现但未登记")
                continue
            if not occ:
                continue
            if term in registered:
                continue
            if kind in SKIP_KINDS:
                stats["waived"] += 1
                explained.append(f"{uid} {term} waived {kind} {rule.get('reason', '')}")
                continue
            if kind in POINTER_KINDS:
                stats["pointer"] += 1
                explained.append(f"{uid} {term} {kind} rule {rule.get('reason', '')}")
                continue
            if context_exempt and DECLARED_POINTER.search(e.get("note", "")):
                stats["pointer"] += 1
                explained.append(f"{uid} {term} pointer note {e.get('note', '')[:80]}")
                continue
            if context_exempt and all(POINTER_CTX.search(c) for _, _, c in occ):
                stats["pointer"] += 1
                explained.append(f"{uid} {term} pointer context {occ[0][2][:80]}")
                continue
            errors.append(f"提前裸现：「{term}」总账首现为 {e['uid']}，本章提前出现"
                          f"（未登记指针/预览/多义；见编辑规则 edit/术语扫描规则.tsv）")

    return {"errors": errors, "warns": warns, "stats": stats, "explained": explained}


def scan(chapter: Path, edit: Path | None,
         ledger: Path | None = None, uid: str = ""):
    r = analyze(chapter, edit, ledger=ledger, uid=uid)
    return r["errors"], r["warns"]


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

    ch3 = tmp / "c3.md"
    ch3.write_text("# 章\n\n**损失**很大。\n", encoding="utf-8")
    led = tmp / "ledger.tsv"
    led.write_text("损失\t§2\t错误程度\n幽灵\t§2\t不在正文\n", encoding="utf-8")
    r3 = analyze(ch3, None, ledger=led, uid="§2")
    ok &= any("幽灵" in e for e in r3["errors"])
    ok &= r3["stats"]["single"] == 0

    # 别名：Stable Diffusion／SD 在正文只出现一个别名也算在场。
    led2 = tmp / "ledger2.tsv"
    led2.write_text("Stable Diffusion／SD\tT4\t文生图\n", encoding="utf-8")
    ch4 = tmp / "c4.md"
    ch4.write_text("# 章\n\nStable Diffusion v1.5 是一套配方。\n", encoding="utf-8")
    r4 = analyze(ch4, None, ledger=led2, uid="T4")
    ok &= not r4["errors"]

    # 单字词跳过；退役条目跳过。
    led3 = tmp / "ledger3.tsv"
    led3.write_text("值\t§0.1\tValue\n三把钥匙\t§0.1\t【已删除，仅存档案】\n",
                    encoding="utf-8")
    r5 = analyze(ch4, None, ledger=led3, uid="§0.1")
    ok &= not r5["errors"] and r5["stats"]["single"] == 1 and r5["stats"]["retired"] == 1

    # 指针/多义规则。
    rules = tmp / "rules.tsv"
    rules.write_text("回归\t§0.2\t指针\t自回归不是 §4 回归\n"
                     "特征\tglobal\t多义\t普通词/不同义\n", encoding="utf-8")
    led4 = tmp / "ledger4.tsv"
    led4.write_text("回归\t§4\t预测一个数\n特征\t§13\t表示义\n", encoding="utf-8")
    ch5 = tmp / "c5.md"
    ch5.write_text("# 章\n\n自回归的回归，以及普通特征。\n", encoding="utf-8")
    r6 = analyze(ch5, None, ledger=led4, uid="§0.2", rules_path=rules)
    ok &= not r6["errors"] and r6["stats"]["waived"] >= 1 and r6["stats"]["pointer"] >= 1

    # 未豁免的提前出现仍须报错；同一句加指针则放行。
    led5 = tmp / "ledger5.tsv"
    led5.write_text("新词\t§9\t后章词\n", encoding="utf-8")
    ch6 = tmp / "c6.md"
    ch6.write_text("# 章\n\n这里先用了新词。\n", encoding="utf-8")
    r7 = analyze(ch6, None, ledger=led5, uid="§0.2")
    ok &= any("提前裸现" in e and "新词" in e for e in r7["errors"])
    ch7 = tmp / "c7.md"
    ch7.write_text("# 章\n\n见 §9 的新词。\n", encoding="utf-8")
    r8 = analyze(ch7, None, ledger=led5, uid="§0.2")
    ok &= not r8["errors"] and r8["stats"]["pointer"] == 1

    ok &= (chapter_key("§9") < chapter_key("支线导言")
           < chapter_key("支线附录") < chapter_key("T1") < chapter_key("§10"))
    ok &= chapter_key("§0.3") < chapter_key("§1")
    ok &= chapter_key("T4") < chapter_key("§10")
    print("first_use_scan selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def report_line(uid: str, r: dict) -> str:
    s = r["stats"]
    return (f"{uid}: {len(r['errors'])} 错 / {len(r['warns'])} 警｜"
            f"指针 {s['pointer']}｜豁免 {s['waived']}｜"
            f"单字跳过 {s['single']}｜退役跳过 {s['retired']}")


def main() -> int:
    ap = argparse.ArgumentParser(description="首现名词登记＋术语总账核对")
    ap.add_argument("chapter", nargs="?", help="章节 md")
    ap.add_argument("--all", action="store_true", help="扫描全部阅读单元（配合 --ledger-only）")
    ap.add_argument("--edit", help="edit 档案 md（默认 ../edit/<同名>.edit.md）")
    ap.add_argument("--ledger-only", action="store_true",
                    help="无 edit 档案时只对账术语总账（不查加粗/幽灵/gloss）")
    ap.add_argument("--ledger", help="术语总账 tsv（默认 edit 档案同目录的 术语总账.tsv）")
    ap.add_argument("--rules", help="扫描规则 tsv（默认总账同目录的 术语扫描规则.tsv）")
    ap.add_argument("--no-ledger", action="store_true", help="关闭总账核对")
    ap.add_argument("--report", action="store_true", help="打印分类统计")
    ap.add_argument("--explain", action="store_true", help="逐条打印被豁免/跳过的判断")
    ap.add_argument("--no-context-exempt", action="store_true",
                    help="关闭指针的自动上下文豁免，只认规则表（审计用）")
    ap.add_argument("--check-rules", action="store_true", help="只校验术语扫描规则表")
    ap.add_argument("--strict", action="store_true", help="WARN 也退 1")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if args.check_rules:
        ledger = Path(args.ledger) if args.ledger else SERIES / "edit" / "术语总账.tsv"
        if not ledger.is_file():
            print(f"术语总账不存在：{ledger}", file=sys.stderr)
            return 2
        rules = Path(args.rules) if args.rules else ledger.parent / RULES_NAME
        if not rules.is_file():
            print(f"规则表不存在：{rules}", file=sys.stderr)
            return 2
        problems = check_rules(ledger, rules)
        for p in problems:
            print(f"ERROR {p}")
        print(f"first_use_scan --check-rules：{len(problems)} 问题")
        return 1 if problems else 0
    if args.all and args.chapter:
        print("--all 与章文件不能同时使用", file=sys.stderr)
        return 2
    if args.all and args.edit:
        print("--all 与 --edit 不能同时使用", file=sys.stderr)
        return 2
    if args.all:
        if args.no_ledger:
            print("--all 需要术语总账", file=sys.stderr)
            return 2
        ledger = Path(args.ledger) if args.ledger else SERIES / "edit" / "术语总账.tsv"
        if not ledger.is_file():
            print(f"术语总账不存在：{ledger}", file=sys.stderr)
            return 2
        rules = Path(args.rules) if args.rules else ledger.parent / RULES_NAME
        files = sorted(glob.glob(str(SERIES / "§*.md")) + glob.glob(str(SERIES / "T*.md"))
                       + glob.glob(str(SERIES / "支线*.md")))
        agg = Counter()
        bad = 0
        for f in files:
            p = Path(f)
            uid = p.stem.split("-")[0]
            r = analyze(p, None, ledger=ledger, uid=uid, rules_path=rules,
                        context_exempt=not args.no_context_exempt)
            bad += len(r["errors"])
            agg["warns"] += len(r["warns"])
            for k, v in r["stats"].items():
                agg[k] += v
            if args.report or r["errors"]:
                print(report_line(uid, r))
            for e in r["errors"]:
                print(f"ERROR {uid} {e}")
            if args.explain:
                for x in r["explained"]:
                    print(f"INFO  {x}")
            if args.strict:
                for w in r["warns"]:
                    print(f"WARN  {uid} {w}")
        print(f"first_use_scan --all：{len(files)} 单元，{bad} 错 / {agg['warns']} 警｜"
              f"指针 {agg['pointer']}｜豁免 {agg['waived']}｜"
              f"单字跳过 {agg['single']}｜退役跳过 {agg['retired']}")
        return 1 if bad or (args.strict and agg["warns"]) else 0

    if not args.chapter:
        ap.print_help()
        return 2
    if args.ledger_only and args.edit:
        print("--ledger-only 与 --edit 不能同时使用", file=sys.stderr)
        return 2
    chapter = Path(args.chapter)
    uid = chapter.stem.split("-")[0]
    if not chapter.is_file():
        print(f"文件不存在：{chapter}", file=sys.stderr)
        return 2
    if args.ledger_only:
        edit = None
    elif args.edit:
        edit = Path(args.edit)
        if not edit.is_file():
            print(f"文件不存在：{edit}", file=sys.stderr)
            return 2
    else:
        edit = chapter.parent / "edit" / f"{uid}.edit.md"
        if not edit.is_file():
            print(f"文件不存在：{edit}；无 edit 档案时请加 --ledger-only",
                  file=sys.stderr)
            return 2
    ledger = None
    if not args.no_ledger:
        base = edit.parent if edit is not None else chapter.parent / "edit"
        ledger = Path(args.ledger) if args.ledger else base / "术语总账.tsv"
        if not ledger.is_file():
            if args.ledger_only:
                print(f"--ledger-only 需要术语总账：{ledger}", file=sys.stderr)
                return 2
            ledger = None
    elif args.ledger_only:
        print("--ledger-only 与 --no-ledger 不能同时使用", file=sys.stderr)
        return 2
    rules = Path(args.rules) if args.rules else (ledger.parent / RULES_NAME if ledger else None)
    r = analyze(chapter, edit, ledger=ledger, uid=uid, rules_path=rules,
                context_exempt=not args.no_context_exempt)
    if args.report:
        print(report_line(uid, r))
    for e in r["errors"]:
        print(f"ERROR {e}")
    if args.explain:
        for x in r["explained"]:
            print(f"INFO  {x}")
    for w in r["warns"]:
        print(f"WARN  {w}")
    print(f"first_use_scan：{len(r['errors'])} 错 / {len(r['warns'])} 警")
    return 1 if (r["errors"] or (args.strict and r["warns"])) else 0


if __name__ == "__main__":
    sys.exit(main())
