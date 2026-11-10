#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prose_common：正文审阅工具的共用切分与测量。

只做可计算子集；不判断语义，不写文件。供 section_map / coherence_scan /
answer_mirror_check / prose_diff / ripple_check 复用。
"""
from __future__ import annotations

import math
import re
import statistics
from pathlib import Path

SENT_END = re.compile(r"[。！？]")
DASH = "——"
SKIP_PREFIX = ("#", "|", "〔")
SHORT = 20

# 断言/评价词。只用于提示“这句可能改变了断言强度”，不判对错。
CLAIM_WORDS = (
    "更", "最", "必然", "一定", "所有", "从不", "证明", "显然",
    "毫无疑问", "唯一", "根本", "只有", "总是", "绝不", "完全", "无法",
)
# 编辑过程/体例声明词。命中只提示“这不是内容改动”，上下文半径按节看。
EDIT_WORDS = (
    "旧结论", "推倒重来", "加盖", "整理成", "最值钱", "最锋利", "最值得",
    "更值钱", "补一句", "补三笔", "记号一行", "行文叫", "落地三句",
    "逐条说清", "整章的账", "收成一句话", "三题自查", "每个代表一行",
    "这一段的误解", "其余误解", "收束", "报幕", "只有一句", "先说清",
    "更年轻",
)
TRANSITIONS = (
    "因此", "所以", "于是", "但", "然而", "不过", "而", "同时", "此外",
    "另外", "接下来", "首先", "其次", "最后", "总之", "换句话说",
    "也就是说", "具体来说", "例如", "比如", "这意味着", "这说明",
)
PRONOUN_STARTS = (
    "这", "那", "它", "其", "该", "此", "这些", "那些", "这种", "那种",
    "上述", "以上",
)
NUM_RE = re.compile(r"(?<![A-Za-z0-9_.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?%?|\d+(?:\.\d+)?%?)(?![A-Za-z0-9_])")
BOLD_RE = re.compile(r"\*\*([^*\n]+)\*\*")
QUOTE_RE = re.compile(r"[“\"]([^”\"\n]{2,40})[”\"]")


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def fence_mask(lines: list[str]) -> list[bool]:
    """True＝该行在围栏代码块内，或是围栏标记行。"""
    mask: list[bool] = []
    in_fence = False
    for line in lines:
        if line.lstrip().startswith("```"):
            mask.append(True)
            in_fence = not in_fence
            continue
        mask.append(in_fence)
    return mask


def is_skippable(line: str) -> bool:
    s = line.strip()
    return (not s) or s.startswith(SKIP_PREFIX)


def prose_items(lines: list[str]) -> list[tuple[int, str]]:
    """(1-based 行号, 正文行)，跳过围栏、标题、表格、图注与空行。"""
    mask = fence_mask(lines)
    out: list[tuple[int, str]] = []
    for i, (line, skip) in enumerate(zip(lines, mask), 1):
        if skip or is_skippable(line):
            continue
        out.append((i, line.rstrip()))
    return out


def paragraphs(lines: list[str]) -> list[dict]:
    """正文段落。空行/标题/表格/图注/围栏处断开；返回 start/end/text。"""
    mask = fence_mask(lines)
    paras: list[dict] = []
    cur: list[str] = []
    start = 0

    def flush() -> None:
        nonlocal cur
        if cur:
            paras.append({"start": start, "end": start + len(cur) - 1,
                          "text": "\n".join(cur)})
            cur = []

    for i, (line, skip) in enumerate(zip(lines, mask), 1):
        if skip or is_skippable(line):
            flush()
            continue
        if not cur:
            start = i
        cur.append(line.rstrip())
    flush()
    return paras


def sections(lines: list[str], level: int = 2) -> list[dict]:
    """H2 节。返回 start/end/title；首个 H2 之前的内容归入空标题节。"""
    mask = fence_mask(lines)
    marker = "#" * level + " "
    heads: list[tuple[int, str]] = []
    for i, (line, skip) in enumerate(zip(lines, mask), 1):
        if skip:
            continue
        if line.startswith(marker) and not line.startswith("#" * (level + 1) + " "):
            heads.append((i, line[len(marker):].strip()))
    out: list[dict] = []
    for idx, (i, title) in enumerate(heads):
        end = heads[idx + 1][0] - 1 if idx + 1 < len(heads) else len(lines)
        out.append({"start": i, "end": end, "title": title})
    if not out:
        return [{"start": 1, "end": len(lines), "title": ""}]
    if out[0]["start"] > 1:
        out.insert(0, {"start": 1, "end": out[0]["start"] - 1, "title": ""})
    return out


def section_for_line(secs: list[dict], lineno: int) -> str:
    for s in secs:
        if s["start"] <= lineno <= s["end"]:
            return s["title"]
    return ""


def split_sentences(text: str) -> list[str]:
    plain = text.replace("**", "").replace("{#", "")
    plain = re.sub(r"\{#[^}]*\}", "", plain)
    return [s.strip() for s in SENT_END.split(plain) if s.strip()]


def sentence_lengths(text: str) -> list[int]:
    return [len(re.sub(r"\s", "", s)) for s in split_sentences(text)]


def short_run(lens: list[int]) -> tuple[int, int]:
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


def measure_text(text: str) -> dict:
    lens = sentence_lengths(text)
    dashes = text.count(DASH)
    n = len(lens)
    if n == 0:
        return {"n": 0, "mean": 0.0, "med": 0, "p90": 0,
                "dashes": dashes, "dens": 0.0, "run": 0, "run_start": -1}
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


def paragraph_at(lines: list[str], lineno: int) -> dict | None:
    for p in paragraphs(lines):
        if p["start"] <= lineno <= p["end"]:
            return p
    return None


def surrounding_paragraphs(lines: list[str], start: int, end: int,
                           n: int = 1) -> tuple[list[dict], dict | None, list[dict]]:
    """改动位置前后的各 n 段，以及包含改动的段落。"""
    paras = paragraphs(lines)
    idx = None
    for j, p in enumerate(paras):
        if p["start"] <= start <= p["end"] or p["start"] <= end <= p["end"]:
            idx = j
            break
    if idx is None:
        before = [p for p in paras if p["end"] < start]
        idx = max(0, len(before) - 1) if before else 0
    prev = paras[max(0, idx - n):idx]
    nxt = paras[idx + 1:idx + 1 + n]
    target = paras[idx] if 0 <= idx < len(paras) else None
    return prev, target, nxt


def significant_numbers(text: str) -> set[str]:
    out: set[str] = set()
    for m in NUM_RE.finditer(text):
        s = m.group(1)
        if len(s) >= 2 or "." in s or "%" in s:
            out.add(s)
    return out


def normalize_number(s: str) -> str:
    """数字比较口径：去千分位/空格/尾零；百分比保留后缀。"""
    s = s.strip().replace(",", "").replace(" ", "")
    pct = s.endswith("%")
    if pct:
        s = s[:-1]
    try:
        from decimal import Decimal, InvalidOperation
        d = Decimal(s).normalize()
        out = "0" if d == 0 else format(d, "f")
    except (InvalidOperation, ValueError):
        out = s
    return out + ("%" if pct else "")


def bold_terms(text: str) -> set[str]:
    return {m.group(1).strip() for m in BOLD_RE.finditer(text)}


def quoted_terms(text: str) -> set[str]:
    return {m.group(1).strip() for m in QUOTE_RE.finditer(text)}


def claim_words(text: str) -> set[str]:
    return {w for w in CLAIM_WORDS if w in text}


def _strip_quotes_ws(text: str) -> str:
    return re.sub(r'[\s"“”\'‘’]', "", text)


def impact_type(old_text: str, new_text: str) -> tuple[str, str]:
    """改动类型：structure / table / edit / number / term / claim / wording / trivial。

    只根据字面变化做保守分类，供“上下文半径”提示，不判语义。
    """
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    if _strip_quotes_ws(old_text) == _strip_quotes_ws(new_text):
        return "trivial", "仅引号/空白变化"
    if any(l.lstrip().startswith(("#", "<details", "<summary"))
           for l in old_lines + new_lines):
        return "structure", "标题/折叠块/层级变化"
    old_rows = sum(1 for l in old_lines if l.lstrip().startswith("|"))
    new_rows = sum(1 for l in new_lines if l.lstrip().startswith("|"))
    if old_rows != new_rows:
        return "table", "表格行变化"
    old_edits = {w for w in EDIT_WORDS if w in old_text}
    new_edits = {w for w in EDIT_WORDS if w in new_text}
    if old_edits != new_edits:
        return "edit", "编辑痕迹/体例声明变化"
    if significant_numbers(old_text) != significant_numbers(new_text):
        return "number", "数字变化"
    if bold_terms(old_text) != bold_terms(new_text):
        return "term", "加粗术语变化"
    if claim_words(old_text) != claim_words(new_text):
        return "claim", "断言/评价词变化"
    return "wording", "措辞变化"


def prefix_of(sentence: str, width: int = 40) -> str:
    s = re.sub(r"\s", "", sentence)
    return s[:width] + ("…" if len(s) > width else "")


def contains_text(term: str, text: str) -> bool:
    """术语/短语是否在正文中作为字面出现（去加粗/反引号后）。"""
    t = term.replace("**", "").replace("`", "").strip()
    return bool(t) and t in text


if __name__ == "__main__":
    # 轻量自检：只测切分与测量，不写文件。
    sample = (
        "# 标题\n\n"
        "第一段第一句。第一段第二句，长一点。\n\n"
        "## 小节\n\n"
        "第二段：这是第三句。\n\n"
        "| 表格 | 不计 |\n\n"
        "〔图 1：不计。〕\n"
    )
    lines = sample.splitlines()
    ps = paragraphs(lines)
    ss = sections(lines)
    m = measure_text("\n".join(p["text"] for p in ps))
    ok = (len(ps) == 2 and len(ss) == 2 and ss[1]["title"] == "小节"
          and m["n"] == 3 and m["dashes"] == 0
          and impact_type("他更强。", "他更稳。")[0] == "wording"
          and impact_type("得分 3.2。", "得分 3.4。")[0] == "number"
          and impact_type("**术语**在这里。", "另一个词在这里。")[0] == "term")
    print("prose_common selftest:", "PASS" if ok else "FAIL")
    raise SystemExit(0 if ok else 1)
