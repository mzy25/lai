#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prose_diff：改动感知的正文审阅报告（摘要 + 上下文 + 影响分类）。

用法：
    python3 series/tools/prose_diff.py "series/§N-….md"
    python3 series/tools/prose_diff.py "series/§N-….md" --since HEAD~1 --context 2
    python3 series/tools/prose_diff.py "series/§N-….md" --summary-only
    python3 series/tools/prose_diff.py "series/§N-….md" --only edit,claim,term,number,structure,table
    python3 series/tools/prose_diff.py "series/§N-….md" --untracked
    python3 series/tools/prose_diff.py --selftest

输出：
  - 顶部摘要表：行、节、影响分类、改动摘要；
  - 每个段落/折叠块只出现一次（同段多 hunk 合并）；
  - 详情：改动行、改前/改后整段或整块、前后上下文、上下文半径、ripple checks。

只读，不判语义；默认 stdout。退出码 0（无改动也 0）。
"""
from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
from pathlib import Path

from prose_common import (impact_type, measure_text, paragraph_at, paragraphs,
                          prefix_of, read_lines, section_for_line, sections)

ROOT = Path(__file__).resolve().parents[2]
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
IMPACT_ORDER = ["structure", "table", "term", "number", "claim", "edit",
                "wording", "trivial"]

RADIUS = {
    "trivial": "无需展开：仅引号/空白变化",
    "edit": "本节 + 章末 + 答案（删掉的是否是读者需要的路标）",
    "wording": "邻段：上一段末两句 + 本段 + 下一段首两句",
    "claim": "本节 + 章末回顾 + 答案块",
    "term": "本章 + 术语总账 + 跨章引用 + 答案块",
    "number": "本节 + 所有依赖计算 + 表格/答案/图注",
    "structure": "整节 + 相邻节 + 系列引用 + 路线/README",
    "table": "本节 + 表格 + 引用/答案",
}
RIPPLE = {
    "trivial": [],
    "edit": ["answer_mirror_check.py", "reference_lint.py --strict",
             "coherence_scan.py"],
    "wording": ["朗读改动段与前后各一段", "coherence_scan.py"],
    "claim": ["answer_mirror_check.py", "同章 grep 旧断言", "reference_lint.py --strict"],
    "term": ["first_use_scan.py --ledger-only", "symbol_coverage.py --strict",
             "reference_lint.py --strict", "answer_mirror_check.py"],
    "number": ["answer_mirror_check.py", "grep 旧数字/旧表格", "row_check.py（句长变时）"],
    "structure": ["reference_lint.py --strict", "series_check.py（build 后）",
                  "route_lint.py --check", "anchors 漂移门"],
    "table": ["table_check.py", "answer_mirror_check.py", "reference_lint.py --strict"],
}


def parse_hunks(diff_text: str) -> list[dict]:
    hunks: list[dict] = []
    cur: dict | None = None
    for line in diff_text.splitlines():
        m = HUNK_RE.match(line)
        if m:
            if cur:
                hunks.append(cur)
            old_count = int(m.group(2)) if m.group(2) is not None else 1
            new_count = int(m.group(4)) if m.group(4) is not None else 1
            cur = {"old_start": int(m.group(1)), "old_count": old_count,
                   "new_start": int(m.group(3)), "new_count": new_count,
                   "old": [], "new": []}
            continue
        if cur is None:
            continue
        if line.startswith(("---", "+++")):
            continue
        if line.startswith("-"):
            cur["old"].append(line[1:])
        elif line.startswith("+"):
            cur["new"].append(line[1:])
    if cur:
        hunks.append(cur)
    return hunks


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def block_text(lines: list[str], start: int, end: int) -> str:
    if not lines:
        return ""
    lo = max(1, start)
    hi = min(len(lines), max(lo, end))
    return "\n".join(lines[lo - 1:hi])


def para_stats(text: str) -> str:
    m = measure_text(text)
    if not m["n"]:
        return "无正文句"
    return (f"{m['n']} 句｜均值 {m['mean']:.1f}｜P90 {m['p90']}｜"
            f"破折号 {m['dashes']}｜短句 run {m['run']}")


def trim(text: str, limit: int) -> str:
    text = text.strip()
    if limit > 0 and len(text) > limit:
        return text[:limit].rstrip() + "…"
    return text


def details_bounds(lines: list[str], lineno: int) -> tuple[int, int] | None:
    """若 lineno 落在 <details>...</details> 内，返回块的行范围。"""
    if not lines:
        return None
    idx = min(max(lineno, 1), len(lines)) - 1
    start = None
    for i in range(idx, -1, -1):
        if "</details>" in lines[i]:
            return None
        if "<details>" in lines[i]:
            start = i
            break
    if start is None:
        return None
    for j in range(start, len(lines)):
        if "</details>" in lines[j]:
            return (start + 1, j + 1)
    return (start + 1, len(lines))


def context_around(lines: list[str], start: int, end: int,
                   n: int) -> tuple[list[dict], list[dict]]:
    paras = paragraphs(lines)
    prev = [p for p in paras if p["end"] < start][-n:] if n else []
    nxt = [p for p in paras if p["start"] > end][:n] if n else []
    return prev, nxt


def group_key(lines: list[str], start: int, end: int) -> tuple:
    db = details_bounds(lines, start)
    if db:
        return ("details", db[0], db[1])
    p = paragraph_at(lines, start)
    if p:
        return ("para", p["start"], p["end"])
    return ("line", start, max(start, end))


def impact_rank(kind: str) -> int:
    return IMPACT_ORDER.index(kind) if kind in IMPACT_ORDER else len(IMPACT_ORDER)


def merge_kind(kinds: list[str]) -> str:
    return min(kinds, key=impact_rank) if kinds else "wording"


def group_hunks(hunks: list[dict], old_lines: list[str],
                new_lines: list[str]) -> list[dict]:
    groups: list[dict] = []
    index: dict[tuple, dict] = {}
    for h in hunks:
        n_start = h["new_start"]
        n_end = n_start + max(h["new_count"], 1) - 1
        o_start = h["old_start"]
        o_end = o_start + max(h["old_count"], 1) - 1
        if h["new_count"] == 0 and old_lines:
            key = group_key(old_lines, o_start, o_end)
            bounds = details_bounds(old_lines, o_start)
            if bounds:
                o_start, o_end = bounds
            else:
                p = paragraph_at(old_lines, o_start)
                if p:
                    o_start, o_end = p["start"], p["end"]
        else:
            key = group_key(new_lines, n_start, n_end)
            bounds = details_bounds(new_lines, n_start)
            if bounds:
                n_start, n_end = bounds
            else:
                p = paragraph_at(new_lines, n_start)
                if p:
                    n_start, n_end = p["start"], p["end"]
        g = index.get(key)
        if not g:
            g = {"key": key, "hunks": [], "old": [], "new": [],
                 "old_start": o_start, "old_end": o_end,
                 "new_start": n_start, "new_end": n_end}
            index[key] = g
            groups.append(g)
        g["hunks"].append(h)
        g["old"].extend(h["old"])
        g["new"].extend(h["new"])
        g["old_start"] = min(g["old_start"], o_start)
        g["old_end"] = max(g["old_end"], o_end)
        g["new_start"] = min(g["new_start"], n_start)
        g["new_end"] = max(g["new_end"], n_end)
    for g in groups:
        kinds = [impact_type("\n".join(h["old"]), "\n".join(h["new"]))[0]
                 for h in g["hunks"]]
        combined_kind, combined_why = impact_type("\n".join(g["old"]),
                                                   "\n".join(g["new"]))
        g["kind"] = merge_kind([combined_kind] + kinds)
        g["why"] = combined_why
    return groups


def compact(text: str, limit: int = 90) -> str:
    text = text.replace("|", "／").replace("**", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def _quote_only(a: str, b: str) -> bool:
    norm = lambda s: re.sub(r'[\s"“”\'‘’]', "", s)
    return norm(a) == norm(b)


def change_snippet(old: str, new: str, width: int = 32) -> str:
    old = re.sub(r"\s+", " ", old).strip()
    new = re.sub(r"\s+", " ", new).strip()
    sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        pre = old[max(0, i1 - 10):i1]
        o = old[max(0, i1 - 4):min(len(old), i2 + 14)].strip()
        n = new[max(0, j1 - 4):min(len(new), j2 + 14)].strip()
        if _quote_only(o, n):
            continue
        if tag == "insert":
            return f"{pre}…[+{n[:width]}]"
        if tag == "delete":
            return f"{pre}…[-{o[:width]}]"
        return f"{pre}…[{o[:width]} → {n[:width]}]"
    return ""


def summary_text(g: dict) -> str:
    text = "\n".join(g["new"] or g["old"])
    for line in text.splitlines():
        if "<summary>" in line:
            s = line.split("<summary>", 1)[1].split("</summary>", 1)[0]
            return compact(s)
    snippet = change_snippet("\n".join(g["old"]), "\n".join(g["new"]))
    if snippet:
        s = compact(snippet)
    else:
        first = next((l for l in text.splitlines() if l.strip()), "")
        s = compact(first)
    if len(g["hunks"]) > 1:
        s = f"{len(g['hunks'])} 处｜{s}"
    return s


def render_group(idx: int, g: dict, old_lines: list[str], new_lines: list[str],
                 ctx: int, max_chars: int) -> list[str]:
    kind = g["kind"]
    why = g["why"]
    sec = section_for_line(sections(new_lines), g["new_start"])
    out = [f"## {idx} · L{g['new_start']}"
           + (f"–{g['new_end']}" if g["new_end"] > g["new_start"] else "")
           + (f" · {sec}" if sec else ""), ""]
    out.append(f"- 影响分类：**{kind}**（{why}）")
    out.append(f"- 上下文半径：{RADIUS[kind]}")
    out.append("- Ripple checks：" + ("；".join(RIPPLE[kind]) or "无"))
    if g["old"] or g["new"]:
        out += ["", "**改动行**", "", "```diff"]
        for l in g["old"][:60]:
            out.append("- " + l)
        for l in g["new"][:60]:
            out.append("+ " + l)
        if len(g["old"]) > 60 or len(g["new"]) > 60:
            out.append(f"…（旧 {len(g['old'])} 行 / 新 {len(g['new'])} 行，已截断）")
        out += ["```", ""]

    key = g["key"][0]
    if key == "details":
        old_para = block_text(old_lines, g["old_start"], g["old_end"])
        new_para = block_text(new_lines, g["new_start"], g["new_end"])
        label = "整块"
    else:
        old_p = paragraph_at(old_lines, g["old_start"]) if old_lines else None
        new_p = paragraph_at(new_lines, g["new_start"])
        old_para = old_p["text"] if old_p else block_text(old_lines, g["old_start"], g["old_end"])
        new_para = new_p["text"] if new_p else block_text(new_lines, g["new_start"], g["new_end"])
        label = "整段"
    out += ["", f"**改前{label}**（{para_stats(old_para)}）", "",
            "```text", trim(old_para, max_chars), "```", ""]
    out += [f"**改后{label}**（{para_stats(new_para)}）", "",
            "```text", trim(new_para, max_chars), "```", ""]

    old_prev, old_next = context_around(old_lines, g["old_start"], g["old_end"], ctx)
    new_prev, new_next = context_around(new_lines, g["new_start"], g["new_end"], ctx)
    if old_prev or old_next:
        out += ["**改前上下文**", ""]
        for p in old_prev:
            out += [f"- L{p['start']} 前文：{trim(p['text'], 220)}"]
        for p in old_next:
            out += [f"- L{p['start']} 后文：{trim(p['text'], 220)}"]
        out.append("")
    if new_prev or new_next:
        out += ["**改后上下文**", ""]
        for p in new_prev:
            out += [f"- L{p['start']} 前文：{trim(p['text'], 220)}"]
        for p in new_next:
            out += [f"- L{p['start']} 后文：{trim(p['text'], 220)}"]
        out.append("")
    return out


def render(path: Path, ref: str, ctx: int, max_chars: int,
           all_kinds: bool = False, only: set[str] | None = None,
           summary_only: bool = False, max_summary: int = 40,
           untracked: bool = False) -> str:
    rel = path.resolve().relative_to(ROOT).as_posix()
    if untracked:
        new_lines = read_lines(path)
        hunk = {"old_start": 1, "old_count": 0,
                "new_start": 1, "new_count": len(new_lines),
                "old": [], "new": new_lines}
        hunks = [hunk]
        old_lines: list[str] = []
    else:
        d = git("diff", "--no-color", "--no-ext-diff", "--unified=0", ref, "--", rel)
        if d.returncode != 0:
            return f"git diff 失败：{d.stderr.strip()}\n"
        hunks = parse_hunks(d.stdout)
        new_lines = read_lines(path)
        old = git("show", f"{ref}:{rel}")
        old_lines = old.stdout.splitlines() if old.returncode == 0 else []

    selected = []
    for h in hunks:
        kind, why = impact_type("\n".join(h["old"]), "\n".join(h["new"]))
        if only is not None and kind not in only:
            continue
        if not all_kinds and kind == "trivial" and only is None:
            continue
        selected.append(h)

    groups = group_hunks(selected, old_lines, new_lines)
    lines = [f"# {path.stem} · prose diff（since {ref}）", ""]
    lines.append(f"改动 hunk：{len(hunks)} 个；展示：{len(groups)} 个段落/块；"
                 f"上下文：前后各 {ctx} 段。")
    if not all_kinds and only is None:
        lines.append("（默认跳过仅引号/空白变化的 trivial hunk；`--all` 全看。）")
    if not groups:
        lines.append("")
        lines.append("没有符合过滤条件的 hunk。")
        return "\n".join(lines) + "\n"

    lines += ["", "## 摘要", "",
              "| # | 行 | 节 | 影响 | 改动摘要 |",
              "| --- | --- | --- | --- | --- |"]
    for i, g in enumerate(groups[:max_summary], 1):
        sec = section_for_line(sections(new_lines), g["new_start"]) or "—"
        line_label = (str(g["new_start"]) if g["new_end"] == g["new_start"]
                      else f"{g['new_start']}–{g['new_end']}")
        lines.append(f"| {i} | {line_label} | {sec} | "
                     f"{g['kind']} | {summary_text(g)} |")
    if len(groups) > max_summary:
        lines.append(f"| … |  |  |  | 另有 {len(groups) - max_summary} 个，未列出 |")
    if summary_only:
        return "\n".join(lines) + "\n"

    lines += ["", "## 详情", ""]
    for i, g in enumerate(groups, 1):
        lines += render_group(i, g, old_lines, new_lines, ctx, max_chars)
    return "\n".join(lines).rstrip() + "\n"


def selftest() -> int:
    diff = (
        "diff --git a/t.md b/t.md\n"
        "--- a/t.md\n+++ b/t.md\n"
        "@@ -10,1 +10,1 @@\n"
        "-旧句 3.2。\n"
        "+新句 3.4。\n"
        "@@ -12,0 +13,1 @@\n"
        "+同段新增。\n"
        "@@ -20,0 +22,2 @@\n"
        "+<details>\n"
        "+<summary>块</summary>\n"
    )
    hunks = parse_hunks(diff)
    lines = ["# T", "", "第一段。", "第二段。", "", "第三段。"]
    groups = group_hunks(hunks[:2], lines, lines)
    details_lines = ["# T", "", "<details>", "<summary>块</summary>", "",
                     "内容。", "", "</details>", "", "后文。"]
    dgroups = group_hunks(hunks[2:], details_lines, details_lines)
    ok = (len(hunks) == 3 and len(groups) == 2
          and len(dgroups) == 1
          and impact_type("旧句 3.2。", "新句 3.4。")[0] == "number"
          and impact_type("旧句。", "新句。")[0] == "wording")
    print("prose_diff selftest:", "PASS" if ok else f"FAIL {len(hunks)}/{len(groups)}/{len(dgroups)}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", nargs="?", help="章文件")
    ap.add_argument("--since", default="HEAD", help="git 基线（默认 HEAD）")
    ap.add_argument("--context", type=int, default=1, help="前后各几段（默认 1）")
    ap.add_argument("--max-chars", type=int, default=1200, help="单段显示上限")
    ap.add_argument("--all", action="store_true", help="包含 trivial（仅引号/空白）hunk")
    ap.add_argument("--only", help="只看这些类型，逗号分隔：wording,edit,claim,term,number,structure,table,trivial")
    ap.add_argument("--summary-only", action="store_true", help="只输出摘要表")
    ap.add_argument("--max-summary", type=int, default=40, help="摘要表最多几行")
    ap.add_argument("--untracked", action="store_true", help="把未跟踪文件当整文件新增")
    ap.add_argument("--out", help="输出文件（默认 stdout）")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.target:
        ap.print_help()
        return 2
    p = Path(args.target)
    if not p.is_file():
        print(f"章文件不存在：{p}", file=sys.stderr)
        return 2
    only = None
    if args.only:
        only = {x.strip() for x in args.only.split(",") if x.strip()}
        bad = only - {"wording", "claim", "term", "number", "structure",
                      "table", "trivial", "edit"}
        if bad:
            print(f"未知类型：{', '.join(sorted(bad))}", file=sys.stderr)
            return 2
    try:
        rel = p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        print("目标不在仓库根目录内，无法取 git diff。", file=sys.stderr)
        return 2
    if not args.untracked:
        tracked = git("ls-files", "--error-unmatch", rel)
        if tracked.returncode != 0:
            print("未跟踪文件：先 `git add -N <file>` 或提交后再跑；"
                  "新章请先用 section_map/coherence_scan，或加 --untracked。",
                  file=sys.stderr)
            return 2
    try:
        text = render(p, args.since, max(0, args.context), args.max_chars,
                      args.all, only, args.summary_only, args.max_summary,
                      args.untracked)
    except ValueError:
        print("目标不在仓库根目录内，无法取 git diff。", file=sys.stderr)
        return 2
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {out}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
