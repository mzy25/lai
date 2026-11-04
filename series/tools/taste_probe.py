#!/usr/bin/env python3
"""taste_probe v0.2：品味层族扫描探针（只定位不判罚；2026-10-16，行文深审 v2 配套）。

用法:
  python3 series/tools/taste_probe.py "series/§12-….md"
  python3 series/tools/taste_probe.py "series/§13-….md" --echo 明说,顺手
  python3 series/tools/taste_probe.py --selftest

输出六节：
  S) 单音动词种子候选（种子字＋助词/补语；语域/语义人工判读）
  F) 「拆」族扫描（排除推荐形「拆解」；形态分计：拆过/拆掉/拆开/拆完/拆成/拆一/其他）
  C) 量词失配候选（账：本/张/笔；旋钮：颗/枚/道；面孔：副/张；碗：座/只；台阶：级/道）
  Q) 直引号词频（≥3 列出；回声/装置名候选）
  B) 加粗词组频（≥3 列出；命名/术语强调候选）
  E) 回声词计数（默认表＋--echo 追加；≥3 列出）

v0.2 相对 .tmp/v2base 版：补 F/C/E 三节与 --selftest；代码块按原行数剥离，
行号与源稿一致。判读口径见 `series/edit/行文质量研讨.2026-10-16.md`。
"""
from __future__ import annotations

import argparse
import collections
import re
import sys

SEED = "拆搞弄掰抠拽怼抡砸踹掂缠撇掐掀撬"
PV = re.compile(f"[{SEED}][过了的得着掉]")
PQ = re.compile(r'"([^"\n]{2,12})"')
PB = re.compile(r"\*\*([^*\n]{2,12})\*\*")

CHAI = re.compile(r"拆(?!解)")
CHAI_FORMS: list[tuple[str, re.Pattern]] = [
    ("拆过", re.compile(r"拆过")),
    ("拆掉", re.compile(r"拆掉")),
    ("拆开", re.compile(r"拆开")),
    ("拆完", re.compile(r"拆完")),
    ("拆成", re.compile(r"拆成")),
    ("拆一", re.compile(r"拆一")),
]
QUANT: list[tuple[str, re.Pattern]] = [
    ("账量词", re.compile(r"[这那一两二三四五六七八九十]+[本张笔][^\s，。；：、」）]{0,4}账")),
    ("旋钮量词", re.compile(r"[这那一两二三四五六七八九十]*[颗枚道][^\s，。；：、」）]{0,3}旋钮")),
    ("面孔量词", re.compile(r"[这那一两二三四五六七八九十]*[副张][^\s，。；：、」）]{0,3}面孔")),
    ("碗量词", re.compile(r"[这那一两二三四五六七八九十]*[座只][^\s，。；：、」）]{0,3}碗")),
    ("台阶量词", re.compile(r"[这那一两二三四五六七八九十]*[级道][^\s，。；：、」）]{0,3}台阶")),
]
ECHO_DEFAULT = ["行话", "突然", "守着", "当场", "一路", "长成", "长出"]


def strip_code(t: str) -> str:
    """代码块按原行数替换为空行（保持行号与源稿一致）。"""
    return re.sub(r"```.*?```", lambda m: "\n" * m.group(0).count("\n"), t, flags=re.S)


def load(path: str) -> str:
    return strip_code(open(path, encoding="utf-8").read())


def snippet(ln: str, m: re.Match, w: int = 18) -> str:
    s, e = max(0, m.start() - w), min(len(ln), m.end() + w)
    return ln[s:e].strip()


def scan(pattern: re.Pattern, t: str, cap: int = 100, w: int = 18) -> int:
    n = 0
    for i, ln in enumerate(t.split("\n"), 1):
        for m in pattern.finditer(ln):
            n += 1
            if n <= cap:
                print(f"L{i}: …{snippet(ln, m, w)}…")
    if n > cap:
        print(f"（其余 {n - cap} 处从略）")
    return n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="品味层族扫描探针（只定位不判罚）")
    ap.add_argument("path", nargs="?", help="md 文件")
    ap.add_argument("--echo", default=None, help="附加回声词（逗号分隔，并入默认表）")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.path:
        ap.print_help()
        return 2
    t = load(args.path)

    print("== S 单音动词种子候选 ==")
    print(f"（共 {scan(PV, t)} 处）")

    print("== F 「拆」族扫描（排除「拆解」） ==")
    forms: collections.Counter[str] = collections.Counter()
    n = 0
    for i, ln in enumerate(t.split("\n"), 1):
        for m in CHAI.finditer(ln):
            n += 1
            form = "其他"
            for name, pat in CHAI_FORMS:
                if pat.match(ln, m.start()):
                    form = name
                    break
            forms[form] += 1
            if n <= 100:
                print(f"L{i}: …{snippet(ln, m, 20)}…")
    if n > 100:
        print(f"（其余 {n - 100} 处从略）")
    seg = "／".join(
        f"{k} {forms[k]}" for k in ("拆过", "拆掉", "拆开", "拆完", "拆成", "拆一", "其他") if forms[k]
    )
    print(f"（共 {n} 处；{seg or '—'}）")

    print("== C 量词失配候选 ==")
    for name, pat in QUANT:
        n = scan(pat, t, cap=40, w=14)
        print(f"（{name}：{n} 处）")

    print("== Q 直引号词（≥3 次） ==")
    qc = collections.Counter(PQ.findall(t))
    hit = False
    for k, v in qc.most_common():
        if v >= 3:
            hit = True
            print(f"{k} ×{v}")
    if not hit:
        print("（无）")

    print("== B 加粗词（≥3 次） ==")
    bc = collections.Counter(PB.findall(t))
    hit = False
    for k, v in bc.most_common():
        if v >= 3:
            hit = True
            print(f"{k} ×{v}")
    if not hit:
        print("（无）")

    print("== E 回声词计数（≥3） ==")
    echo = list(ECHO_DEFAULT)
    if args.echo:
        echo += [w for w in re.split(r"[,，]", args.echo) if w.strip()]
    hits = [(w, t.count(w)) for w in dict.fromkeys(echo) if t.count(w) >= 3]
    if hits:
        for w, c in sorted(hits, key=lambda kv: -kv[1]):
            print(f"{w} ×{c}")
    else:
        print("（无）")
    return 0


def selftest() -> int:
    ok = True

    def chk(name: str, cond: bool) -> None:
        nonlocal ok
        ok = ok and cond
        print(f"[{'ok' if cond else 'FAIL'}] {name}")

    t1 = "先拆掉旧版，再拆一份，最后拆完收工；拆解两字不算。"
    chk("拆族：排除「拆解」", len(CHAI.findall(t1)) == 3)
    chk("拆族：形态分计", [len(p.findall(t1)) for _, p in CHAI_FORMS] == [0, 1, 0, 1, 0, 1])

    t2 = "这两本账与三张梯度账，哪一本账？还有一笔误差账。"
    chk("量词族：账命中 ≥3", len(QUANT[0][1].findall(t2)) >= 3)

    t3 = "行话、行话、行话；突然，突然。"
    chk("回声计数", t3.count("行话") == 3 and t3.count("突然") == 2)

    s = "a\n```\nx\ny\n```\nb"
    chk("代码块剥离保持行数", len(strip_code(s).split("\n")) == len(s.split("\n")))

    print("selftest", "OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
