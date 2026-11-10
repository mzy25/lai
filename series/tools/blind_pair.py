#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""blind_pair：把“原文/改写”候选做成随机 A/B 盲评表。

用法：
    python3 series/tools/blind_pair.py series/.tmp/§N.pairs.tsv
    python3 series/tools/blind_pair.py series/.tmp/§N.pairs.tsv --out-dir series/.tmp/blind/§N --seed 7
    python3 series/tools/blind_pair.py --selftest

输入 TSV 表头：id<TAB>original<TAB>revised
输出：
  review.md  随机 A/B，不标哪个是改写
  key.json    id → 改写所在侧（评审后再看）
  votes.tsv   投票模板：id<TAB>choice(A/B/tie)<TAB>worse(A/B/none)<TAB>note

采纳线（人工 tally）：改写胜率 ≥60%，且“更差”为 0；分歧且无硬缺陷保留原样。
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import review_log


def read_pairs(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return []
    head = lines[0].split("\t")
    out = []
    for ln in lines[1:]:
        if not ln.strip():
            continue
        cells = ln.split("\t")
        row = dict(zip(head, cells))
        if row.get("id") and row.get("original") and row.get("revised"):
            out.append(row)
    return out


def build(pairs: list[dict], out_dir: Path, seed: int) -> dict:
    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    key = {}
    review = ["# 盲评表", "",
              "逐条选：A 更好 / B 更好 / 持平；再标是否有一侧明显更差。",
              "不要看 `key.json`，评完再对。", ""]
    votes = ["id\tchoice\tworse\tnote"]
    for p in pairs:
        revised_is_a = rng.random() < 0.5
        a, b = (p["revised"], p["original"]) if revised_is_a else (p["original"], p["revised"])
        key[p["id"]] = {"revised": "A" if revised_is_a else "B"}
        review += [f"## {p['id']}", "", f"**A**：{a}", "", f"**B**：{b}", ""]
        votes.append(f"{p['id']}\t\t\t")
    (out_dir / "review.md").write_text("\n".join(review).rstrip() + "\n",
                                      encoding="utf-8", newline="\n")
    (out_dir / "key.json").write_text(json.dumps(key, ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8", newline="\n")
    (out_dir / "votes.tsv").write_text("\n".join(votes) + "\n",
                                       encoding="utf-8", newline="\n")
    return key


def read_votes(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return []
    head = lines[0].split("\t")
    return [dict(zip(head, ln.split("\t"))) for ln in lines[1:] if ln.strip()]


def score_rows(votes: list[dict], key: dict) -> dict:
    rows = []
    wins = losses = ties = worse = 0
    for v in votes:
        cid = v.get("id", "")
        revised = key.get(cid, {}).get("revised")
        if revised not in {"A", "B"}:
            continue
        choice = v.get("choice", "").strip().upper()
        w = v.get("worse", "").strip().upper()
        if choice == revised:
            outcome = "revised"
            wins += 1
        elif choice in {"A", "B"}:
            outcome = "original"
            losses += 1
        else:
            outcome = "tie"
            ties += 1
        bad = (w == revised)
        worse += int(bad)
        rows.append({"id": cid, "revised": revised, "choice": choice or "—",
                     "outcome": outcome, "worse": "yes" if bad else ""})
    rate = (wins / (wins + losses) * 100) if (wins + losses) else None
    accept = rate is not None and rate >= 60 and worse == 0
    return {"rows": rows, "wins": wins, "losses": losses, "ties": ties,
            "worse": worse, "rate": rate, "accept": accept}


def render_score(result: dict) -> str:
    lines = ["| id | 改写侧 | 选择 | 结果 | 改写更差 |",
             "| --- | --- | --- | --- | --- |"]
    for r in result["rows"]:
        lines.append(f"| {r['id']} | {r['revised']} | {r['choice']} | "
                     f"{r['outcome']} | {r['worse']} |")
    rate = "—" if result["rate"] is None else f"{result['rate']:.0f}%"
    lines += ["", f"改写胜 {result['wins']}｜原胜 {result['losses']}｜"
                  f"平 {result['ties']}｜改写更差 {result['worse']}｜胜率 {rate}",
              f"判定：{'采纳' if result['accept'] else '不采纳/继续评'}"
              "（线：胜率 ≥60% 且更差 = 0）"]
    return "\n".join(lines)


def score_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="盲评记分")
    ap.add_argument("--votes", required=True, help="votes.tsv")
    ap.add_argument("--key", required=True, help="key.json")
    ap.add_argument("--chapter", help="写入 review_log 时的章名")
    ap.add_argument("--pass", dest="pass_", default="prose",
                    choices=["structure", "prose", "audit", "closeout"])
    ap.add_argument("--log", help="review_log.tsv 路径（给了才写）")
    ap.add_argument("--commit", default="")
    ap.add_argument("--strict", action="store_true", help="不采纳时退出 1")
    args = ap.parse_args(argv)
    votes = read_votes(Path(args.votes))
    key = json.loads(Path(args.key).read_text(encoding="utf-8"))
    result = score_rows(votes, key)
    print(render_score(result))
    if args.log:
        if not args.chapter:
            print("--log 需要 --chapter", file=sys.stderr)
            return 2
        for r in result["rows"]:
            decision = {"revised": "accept", "original": "reject",
                        "tie": "defer"}[r["outcome"]]
            review_log.append_row(Path(args.log), {
                "date": __import__("datetime").date.today().isoformat(),
                "chapter": args.chapter,
                "pass": args.pass_,
                "candidate": r["id"],
                "location": "",
                "decision": decision,
                "reason": f"blind: {r['outcome']}, worse={r['worse'] or 'no'}",
                "commit": args.commit,
            })
        print(f"wrote {args.log}")
    return 1 if (args.strict and not result["accept"]) else 0


def selftest() -> int:
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="blind_"))
    pairs = tmp / "pairs.tsv"
    pairs.write_text("id\toriginal\trevised\nC-1\t旧句。\t新句。\nC-2\t旧二。\t新二。\n",
                     encoding="utf-8")
    out = tmp / "out"
    key = build(read_pairs(pairs), out, 7)
    review = (out / "review.md").read_text(encoding="utf-8")
    votes = [
        {"id": "C-1", "choice": "A", "worse": "none", "note": ""},
        {"id": "C-2", "choice": "A", "worse": "none", "note": ""},
    ]
    key2 = {"C-1": {"revised": "A"}, "C-2": {"revised": "B"}}
    scored = score_rows(votes, key2)
    ok = (len(key) == 2 and "C-1" in review and "旧句。" in review
          and "新句。" in review and (out / "votes.tsv").exists()
          and scored["wins"] == 1 and scored["losses"] == 1
          and scored["rate"] == 50 and not scored["accept"])
    print("blind_pair selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "score":
        return score_main(sys.argv[2:])
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pairs", nargs="?", help="候选 TSV")
    ap.add_argument("--out-dir", help="输出目录（默认 pairs 同目录的 blind/）")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.pairs:
        ap.print_help()
        return 2
    p = Path(args.pairs)
    if not p.is_file():
        print(f"候选表不存在：{p}", file=sys.stderr)
        return 2
    pairs = read_pairs(p)
    if not pairs:
        print("候选表为空或表头不是 id/original/revised。", file=sys.stderr)
        return 2
    out = Path(args.out_dir) if args.out_dir else p.parent / "blind" / p.stem
    build(pairs, out, args.seed)
    print(f"wrote {out}/review.md, key.json, votes.tsv（{len(pairs)} 对）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
