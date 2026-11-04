#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cliche_scan：系列惯用语/套话候选定位（只定位不判罚）。

机读单一源：series/style/套话词表.json（families: name/variants/threshold_per_file;
observe: 观察词，只计数不判罚）。
输出：逐文件 × family 计数表＋命中行；单章同 family ≥ threshold 打 WARN。
报表默认 series/.tmp/cliche_scan.md。退出码恒 0（候选态）。

用法：
    python3 series/tools/cliche_scan.py [targets …] [--out-dir DIR] [--selftest]

判读：校准门（2026-10-13 行文深审批）——真收束 vs 印章；阈值按试点定版。
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERIES = HERE.parent
LEXICON = SERIES / "style" / "套话词表.json"
DEFAULT_TARGETS = ("§*.md", "T*.md", "支线*.md")


def load_lexicon(path: Path = LEXICON) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def strip_fences(lines: list[str]) -> list[str]:
    """围栏代码块内不参与（术语/公式里可能出现任意字样）。"""
    out, in_fence = [], False
    for ln in lines:
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else ln)
    return out


def scan_file(path: Path, lex: dict) -> dict:
    raw = path.read_text(encoding="utf-8").split("\n")
    lines = strip_fences(raw)
    fam_hits: dict[str, list[tuple[int, str, str]]] = {}
    for fam in lex["families"]:
        for i, ln in enumerate(lines, 1):
            for v in fam["variants"]:
                if v in ln:
                    fam_hits.setdefault(fam["name"], []).append((i, v, raw[i - 1].strip()))
                    break
    observe_hits: dict[str, int] = {}
    for w in lex.get("observe", []):
        n = sum(1 for ln in lines if w in ln)
        if n:
            observe_hits[w] = n
    return {"fam": fam_hits, "observe": observe_hits}


def collect(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for a in targets:
        if any(ch in a for ch in "*?["):
            files.extend(Path(p) for p in sorted(glob.glob(a)))
        else:
            p = Path(a)
            if p.is_dir():
                files.extend(sorted(p.glob("*.md")))
            elif p.exists():
                files.append(p)
    return files


def run(targets: list[str], out_dir: Path, lex: dict) -> int:
    files = collect(targets)
    rows, warns, total = [], [], 0
    report = ["# 套话候选报表（cliche_scan；只定位不判罚）", "",
              f"> 词表：{LEXICON.relative_to(SERIES.parent)}；判定见校准门与批记录。", ""]
    for f in files:
        res = scan_file(f, lex)
        if not res["fam"] and not res["observe"]:
            continue
        name = f.stem if len(f.stem) <= 24 else f.stem[:22] + "…"
        for fam in lex["families"]:
            hits = res["fam"].get(fam["name"], [])
            if not hits:
                continue
            total += len(hits)
            rows.append((name, fam["name"], len(hits), fam["threshold_per_file"]))
            if len(hits) >= fam["threshold_per_file"]:
                warns.append(f"{name}: 「{fam['name']}」{len(hits)} 处 ≥ 阈值 {fam['threshold_per_file']}")
            report.append(f"## {name} · {fam['name']}（{len(hits)}）")
            report.append("")
            for i, v, txt in hits:
                report.append(f"- L{i}｜{txt[:120]}")
            report.append("")
        if res["observe"]:
            report.append(f"## {name} · 观察词（只计数）")
            report.append("")
            report.append("　" + "；".join(f"{k} {v}" for k, v in res["observe"].items()))
            report.append("")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cliche_scan.md").write_text("\n".join(report), encoding="utf-8")
    print(f"cliche_scan：{len(files)} 文件，套话命中 {total} 处，WARN {len(warns)}")
    for w in warns:
        print(" WARN", w)
    print(f"报表 → {out_dir / 'cliche_scan.md'}（只定位；判定见校准门）")
    return 0


POS = ("收成一句话：方向是学出来的。", "先看现象。", "一句话说尽它的来历。")
NEG = ("收成一句收尾。", "把问题调个头：", "楼梯口有盏灯。")


def selftest(lex: dict) -> int:
    """已知答案对照：正样本必须点燃、非命中不得误报。"""
    pos = Path("/tmp/opencode/_cliche_pos.md")
    pos.parent.mkdir(parents=True, exist_ok=True)
    pos.write_text("\n".join(POS), encoding="utf-8")
    res = scan_file(pos, lex)
    fams = {k: len(v) for k, v in res["fam"].items()}
    assert fams.get("收束印章") == 2, f"正样本未按期望点燃：{fams}"
    assert res["observe"].get("收成一句") == 1, f"观察词未计数：{res['observe']}"
    neg = Path("/tmp/opencode/_cliche_neg.md")
    neg.write_text("\n".join(NEG), encoding="utf-8")
    res2 = scan_file(neg, lex)
    assert not res2["fam"], f"非命中误报：{res2['fam']}"
    print("cliche_scan --selftest PASS（正样本 2/2 点燃；非命中 0 误报）")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="系列套话候选定位（只定位不判罚）")
    ap.add_argument("targets", nargs="*", default=None)
    ap.add_argument("--out-dir", default=str(SERIES / ".tmp"))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    lex = load_lexicon()
    if args.selftest:
        return selftest(lex)
    targets = args.targets or [str(SERIES / p) for p in DEFAULT_TARGETS]
    return run(targets, Path(args.out_dir), lex)


if __name__ == "__main__":
    sys.exit(main())
