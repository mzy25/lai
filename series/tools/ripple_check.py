#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ripple_check：按改动类型跑“涟漪检查”清单。

用法：
    python3 series/tools/ripple_check.py "series/§N-….md" --type claim
    python3 series/tools/ripple_check.py "series/§N-….md" --type number --run
    python3 series/tools/ripple_check.py "series/§N-….md" --type claim --phrase "更值钱"
    python3 series/tools/ripple_check.py --selftest

类型：edit / wording / claim / term / number / structure / table。
默认只打印清单；--run 执行安全的轻量检查（不 build）。
退出码：0 全过；1 有检查失败；2 用法/文件错误。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

CHAPTER_CMDS = {"coherence_scan.py", "answer_mirror_check.py", "first_use_scan.py"}

PLAN = {
    "edit": {
        "read": "本节 + 章末 + 答案；确认删掉的是体例声明，不是读者需要的路标",
        "run": ["answer_mirror_check.py", "reference_lint.py", "coherence_scan.py"],
        "manual": ["grep 旧体例声明/旧路标（用 --phrase）"],
    },
    "wording": {
        "read": "上一段末两句 + 改动段 + 下一段首两句；出声读",
        "run": ["coherence_scan.py"],
        "manual": [],
    },
    "claim": {
        "read": "本节 + 章末回顾 + 答案块；确认旧断言是否在别处复述",
        "run": ["answer_mirror_check.py", "reference_lint.py"],
        "manual": ["grep 旧断言/旧评价词（用 --phrase）"],
    },
    "term": {
        "read": "本章 + 术语总账 + 答案块",
        "run": ["first_use_scan.py", "symbol_coverage.py",
                "reference_lint.py", "answer_mirror_check.py"],
        "manual": ["确认跨章引用与路线卡是否仍用旧称"],
    },
    "number": {
        "read": "本节 + 所有依赖计算 + 表格/答案/图注",
        "run": ["answer_mirror_check.py"],
        "manual": ["grep 旧数字/旧表格", "句长基准变时跑 row_check.py"],
    },
    "structure": {
        "read": "整节 + 相邻节 + 系列引用",
        "run": ["reference_lint.py", "route_lint.py"],
        "manual": ["build 后跑 series_check.py", "核对 anchors 漂移与 README/路线"],
    },
    "table": {
        "read": "本节 + 表格 + 引用/答案",
        "run": ["table_check.py", "answer_mirror_check.py", "reference_lint.py"],
        "manual": ["核对表头/行数/数字口径/引用"],
    },
}


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(HERE / cmd[0]), *cmd[1:]],
                       capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out


def short(out: str, n: int = 3) -> str:
    lines = [l for l in out.splitlines() if l.strip()]
    return "\n".join("   " + l for l in lines[-n:])


def grep_phrase(target: Path, phrase: str) -> str:
    hits = []
    for i, line in enumerate(target.read_text(encoding="utf-8").splitlines(), 1):
        if phrase in line:
            hits.append(f"   L{i}: {line.strip()[:160]}")
    if not hits:
        return f"   （未找到：{phrase}）"
    return "\n".join(hits)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", nargs="?", help="章文件")
    ap.add_argument("--type", required=False, choices=sorted(PLAN),
                    default="wording")
    ap.add_argument("--run", action="store_true", help="执行轻量检查")
    ap.add_argument("--strict-global", action="store_true",
                    help="全系列检查失败也退出 1")
    ap.add_argument("--phrase", help="额外 grep 的旧断言/旧数字/旧术语")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        ok = ("wording" in PLAN and "claim" in PLAN
              and "term" in PLAN and "number" in PLAN
              and "structure" in PLAN
              and "coherence_scan.py" in PLAN["wording"]["run"])
        print("ripple_check selftest:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    if not args.target:
        ap.print_help()
        return 2
    target = Path(args.target)
    if not target.is_file():
        print(f"章文件不存在：{target}", file=sys.stderr)
        return 2
    plan = PLAN[args.type]
    print(f"== ripple_check · {args.type} ==")
    print(f"读：{plan['read']}")
    print("跑：" + "、".join(plan["run"]))
    for m in plan["manual"]:
        print("人工：" + m)
    if args.phrase:
        print(f"\n== grep：{args.phrase} ==")
        print(grep_phrase(target, args.phrase))
    bad_chapter = False
    bad_global = False
    if args.run:
        print("\n== 执行 ==")
        for cmd in plan["run"]:
            full = [cmd]
            if cmd in CHAPTER_CMDS:
                full.append(str(target))
            if cmd == "first_use_scan.py":
                full.append("--ledger-only")
            if cmd in {"reference_lint.py", "symbol_coverage.py"}:
                full.append("--strict")
            if cmd == "route_lint.py":
                full.append("--check")
            rc, out = run(full)
            scope = "本章" if cmd in CHAPTER_CMDS else "全系列"
            print(f"-- [{scope}] {cmd} rc={rc}")
            print(short(out))
            if scope == "本章":
                bad_chapter |= rc != 0
            else:
                bad_global |= rc != 0
    if bad_global:
        print("\n全系列检查有失败；默认只提示，加 --strict-global 才阻塞。")
    return 1 if (bad_chapter or (args.strict_global and bad_global)) else 0


if __name__ == "__main__":
    sys.exit(main())
