#!/usr/bin/env python3
"""sentence_stats：句长与破折号密度的机械测量（句长基准.md 的底座）。

测量口径（series/style/句长基准.md；v1.1 起两条细则钉死，数值以本工具为准）：
  - 剔除：标题行（# 开头）、表格行（| 开头）、图注占位行（〔 开头）、空行。
  - 句 = 以 。！？ 切分；引号内的 。！？ 同样切句（细则①）；
    顿号、分号、冒号不切句（含冒号领起的跨段，细则②沿用原口径）。
  - 句长 = 句内非空白字符数（CJK 与 ASCII 均计 1；markdown 强调符 ** 计入前剥除）。
  - 破折号密度 = "——" 出现次数 ÷ 句数；双破折插入按 2 计（自然命中两次）。
  - P90 = 最近秩百分位（ceil(0.9 × n) 位，1 起）。
  - 连续短句 run = 句长 ≤20 字的连续句段；另报最长 run 长度及其首句位置，
    ≥5 时打 WARN（B10② 的机械底座）。--row 导出口径不含此项。

用法：
  python series/tools/sentence_stats.py <章.md> [<章.md> ...]
  python series/tools/sentence_stats.py series/§*.md --row   # 直接输出基准表行
  python series/tools/sentence_stats.py <章.md> --update [--note "前缀"] [--dry-run]
      # 就地刷新 style/句长基准.md 对应行：数值替换＋备注追加「日期 前缀后复测 旧→新」
  python series/tools/sentence_stats.py --selftest
"""
from __future__ import annotations

import argparse
import math
import re
import statistics
import sys
from pathlib import Path

SENT_END = re.compile(r"[。！？]")
DASH = "——"
SKIP_PREFIX = ("#", "|", "〔")
SHORT = 20  # B10②：≤20 字算短句，连续 5 句须插长句垫底


def short_run(lens: list[int]) -> tuple[int, int]:
    """连续短句（≤SHORT 字）的最长 run：(长度, 首句 0 基序号)。无短句则 (0, -1)。"""
    best_len, best_start, cur_len, cur_start = 0, -1, 0, 0
    for i, L in enumerate(lens):
        if L <= SHORT:
            if cur_len == 0:
                cur_start = i
            cur_len += 1
            if cur_len > best_len:
                best_len, best_start = cur_len, cur_start
        else:
            cur_len = 0
    return best_len, best_start


def sentences(path: Path) -> list[str]:
    """切句（与 measure 同一口径：剥强调符、去题锚、。！？切分）。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    body = []
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith(SKIP_PREFIX):
            continue
        body.append(s)
    plain = "\n".join(body).replace("**", "").replace("{#", "")
    plain = re.sub(r"\{#[^}]*\}", "", plain)
    return [s.strip() for s in SENT_END.split(plain) if s.strip()]


def sents_head(path: Path, idx: int, width: int = 16) -> str:
    """第 idx 句的前 width 个非空白字符（run 报告定位用）。"""
    sents = sentences(path)
    if not (0 <= idx < len(sents)):
        return "…"
    s = re.sub(r"\s", "", sents[idx])
    return s[:width] + ("…" if len(s) > width else "")


def measure(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    body = []
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith(SKIP_PREFIX):
            continue
        body.append(s)
    text = "\n".join(body)
    dashes = text.count(DASH)
    sents = sentences(path)
    lens = [len(re.sub(r"\s", "", s)) for s in sents]
    n = len(lens)
    if n == 0:
        return {"n": 0, "mean": 0, "med": 0, "p90": 0, "dashes": dashes,
                "dens": 0, "run": 0, "run_start": -1}
    p90 = sorted(lens)[math.ceil(0.9 * n) - 1]
    run_len, run_start = short_run(lens)
    return {
        "n": n,
        "mean": round(statistics.mean(lens), 1),
        "med": statistics.median(lens),
        "p90": p90,
        "dashes": dashes,
        "dens": round(dashes / n, 2),
        "run": run_len,
        "run_start": run_start,
    }


def part_of(uid: str) -> str:
    m = re.fullmatch(r"§(\d+)(?:\.\d+)?", uid)
    if not m:
        return "支线" if uid.startswith("T") else "—"
    n = int(m.group(1))
    return {0: "第〇部"}.get(n) or ("第一部" if n <= 9 else
           "第二部" if n <= 14 else "第三部")


def row(path: Path, m: dict) -> str:
    uid = path.stem.split("-")[0]
    title = path.stem.split("-", 1)[1] if "-" in path.stem else path.stem
    return (f"| {uid} {title} | {part_of(uid)} | {m['n']} | {m['mean']} | "
            f"{int(m['med'])} | {m['p90']} | {m['dashes']} | {m['dens']:.2f} |")


def selftest() -> int:
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="sst_"))
    f = tmp / "t.md"
    f.write_text(
        "# 标题不计\n\n"
        "短句。这是第二句，有点长。\n\n"
        "| 表格 | 不计 |\n\n"
        "〔图 0-1：占位图注不计。〕\n\n"
        "他问：\"去哪看？怎么办？\"两问都计。破折——一次。\n",
        encoding="utf-8")
    m = measure(f)
    # 句：短句(3)／这是第二句有点长(9)／他问："去哪看(7)／怎么办(3)／"两问都计(5)
    # ／破折——一次(6) —— 引号内两问各自成句（细则①）
    ok = (m["n"] == 6 and m["dashes"] == 1 and abs(m["dens"] - round(1 / 6, 2)) < 1e-9
          and m["med"] == 5.5 and m["p90"] == 9)
    print("sentence_stats selftest:", "PASS" if ok else f"FAIL {m}")
    return 0 if ok else 1



def update_row(p: Path, m: dict, note: str, dry: bool) -> int:
    """就地刷新 style/句长基准.md 对应行。行定位＝『| <文件名第一段> 』前缀。"""
    import datetime
    bench = Path(__file__).resolve().parent.parent / "style" / "句长基准.md"
    lines = bench.read_text(encoding="utf-8").splitlines()
    key = p.name.split("-")[0] if "-" in p.name else p.stem
    vals = [str(m["n"]), f"{m['mean']:.1f}", str(int(m["med"])), str(m["p90"]),
            str(m["dashes"]), f"{m['dens']:.2f}"]
    date = datetime.date.today().isoformat()
    hit = -1
    for i, ln in enumerate(lines):
        if ln.startswith("| " + key + " "):
            hit = i
            break
    if hit < 0:
        print(f"基准表无此行：{key}", file=sys.stderr)
        return 2
    f = lines[hit].split("|")
    if len(f) < 10:
        print(f"行格式异常：{key}", file=sys.stderr)
        return 2
    old = [x.strip() for x in f[3:9]]
    changed = old != vals
    delta = ""
    if changed:
        pairs = [f"{o}→{n}" for o, n in zip(old, vals) if o != n]
        delta = " " + "／".join(pairs)
        for j, v in zip(range(3, 9), vals):
            f[j] = " " + v + " "
    tail = f"{date} {note}后复测" if note else f"{date} 复测"
    f[9] = " " + f[9].strip() + "；" + tail + (delta if changed else "值不变") + " "
    lines[hit] = "|".join(f)
    if dry:
        print(f"[dry-run] {key}：{tail}{delta if changed else '值不变'}")
        return 0
    bench.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{key}：{tail}{delta if changed else '值不变'}")
    return 0

def main() -> int:
    ap = argparse.ArgumentParser(description="句长与破折号密度测量")
    ap.add_argument("chapters", nargs="*", help="章节 md")
    ap.add_argument("--row", action="store_true", help="输出基准表行格式")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--update", action="store_true", help="就地刷新句长基准行")
    ap.add_argument("--note", default="", help="复测备注前缀（如「抽样 R9」）")
    ap.add_argument("--dry-run", action="store_true", help="只打印不写盘")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.chapters:
        ap.print_help()
        return 2
    rc = 0
    for c in args.chapters:
        p = Path(c)
        if not p.exists():
            print(f"文件不存在：{p}", file=sys.stderr)
            rc = 2
            continue
        m = measure(p)
        if args.update:
            rc = update_row(p, m, args.note, args.dry_run) or rc
            continue
        if args.row:
            print(row(p, m))
        else:
            print(f"{p.name}：{m['n']} 句／均值 {m['mean']}／中位 {int(m['med'])}"
                  f"／P90 {m['p90']}／破折号 {m['dashes']}／密度 {m['dens']:.2f}")
            if m["run"]:
                head = sents_head(p, m["run_start"])
                print(f"　连续短句 run：最长 {m['run']} 句"
                      f"（首句第 {m['run_start'] + 1} 句：{head}）")
            if m["run"] >= 5:
                print(f"WARN 连续短句 run={m['run']} ≥ 5（B10②：须插长句垫底，"
                      f"首句第 {m['run_start'] + 1} 句）")
    return rc


if __name__ == "__main__":
    sys.exit(main())
