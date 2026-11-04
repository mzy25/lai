#!/usr/bin/env python3
"""系列构建期字形转换器：Unicode 上下标 → pandoc 原生 ~x~ / ^x^；转义正文 ^ ~ 字面量。

背景（2026-10-12 字形批）：系列数学体例＝Unicode 记号（波二裁决，源稿不改）。
产物字体对 ₜ ₁ ₂ ₀ ₅ ⁻ 等缺字形（Noto CJK 系实测全缺；DejaVu 系全有）。转成
pandoc 原生上下标后由排版层承担，双产物均不依赖字体（html → <sub>/<sup>；
docx → vertAlign），且 ² ³ ¹ ᵀ 一并匀速化（用户裁决：一次到位）。

正文（代码段外）残存的 ASCII ^ ~ 字面量（QK^T、e^{−t}、P^→、d_h^R）先转义
为 \\^ \\~，防止与本次生成的新 ^…^ / ~…~ 配对错乱（§5/§8/T1/T3 实测存在）。
代码段（`…`）与围栏块（```）内一律不动——pandoc 对代码内字符本来就不解析。

用法（在 series/ 任意位置）：
    python3 tools/sub_sup_convert.py                  # 只报计数（dry-run，exit 0）
    python3 tools/sub_sup_convert.py --out DIR        # 写派生副本（镜像文件名）
    python3 tools/sub_sup_convert.py --selftest       # 内置好样/坏样对照
    python3 tools/sub_sup_convert.py --files A.md B.md

默认文件集：§*.md、T*.md、支线导言-*.md、支线附录-*.md（plan/方案/清单/AGENTS 不在内）。
非目标：不写回源稿；派生副本只喂 pandoc，不做幂等转换（重复转换会转义已有 ~…~）。
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERIES = HERE.parent

SUB: dict[str, str] = {
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
    "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
    "₊": "+", "₋": "-", "₌": "=", "₍": "(", "₎": ")",
    "ₐ": "a", "ₑ": "e", "ₒ": "o", "ₓ": "x", "ₕ": "h",
    "ₖ": "k", "ₗ": "l", "ₘ": "m", "ₙ": "n", "ₚ": "p",
    "ₛ": "s", "ₜ": "t",
}
SUP: dict[str, str] = {
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
    "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
    "⁺": "+", "⁻": "−", "ᵀ": "T",
}
# ᵀ＝MODIFIER LETTER CAPITAL T（§8 V_rᵀ 转置记号）；− 用 U+2212 对齐全系列减号。

INLINE_CODE = re.compile(r"(`[^`]*`)")
FENCE = re.compile(r"^\s*```")

DEFAULT_GLOBS = ("§*.md", "T*.md", "支线导言-*.md", "支线附录-*.md")


def convert_segment(seg: str, stats: dict) -> str:
    """转换一个非代码段：先转义既有 ^ ~，再合并连续上下标为单对定界符。"""
    if "^" in seg or "~" in seg:
        stats["escape"] += seg.count("^") + seg.count("~")
        stats["escape_chars"]["^" if "^" in seg else "~"] += 0
        for c in seg:
            if c in "^~":
                stats["escape_chars"][c] += 1
        seg = seg.replace("^", r"\^").replace("~", r"\~")
    out: list[str] = []
    i, n = 0, len(seg)
    while i < n:
        ch = seg[i]
        table = SUB if ch in SUB else (SUP if ch in SUP else None)
        if table is None:
            out.append(ch)
            i += 1
            continue
        j = i
        while j < n and seg[j] in table:
            j += 1
        content = "".join(table[c] for c in seg[i:j])
        delim = "~" if table is SUB else "^"
        out.append(f"{delim}{content}{delim}")
        kind = "sub" if table is SUB else "sup"
        stats[kind] += j - i
        for c in seg[i:j]:
            stats[f"{kind}_chars"][c] += 1
        i = j
    return "".join(out)


def convert_text(text: str, stats: dict) -> str:
    """整篇转换：围栏块跳过、行内代码段跳过。"""
    out: list[str] = []
    in_fence = False
    for ln in text.splitlines(keepends=True):
        if FENCE.match(ln):
            in_fence = not in_fence
            out.append(ln)
            continue
        if in_fence:
            out.append(ln)
            continue
        parts = INLINE_CODE.split(ln)
        for idx, part in enumerate(parts):
            out.append(part if idx % 2 else convert_segment(part, stats))
    return "".join(out)


def new_stats() -> dict:
    return {"sub": 0, "sup": 0, "escape": 0,
            "sub_chars": Counter(), "sup_chars": Counter(), "escape_chars": Counter()}


def merge(dst: Counter, src: Counter) -> None:
    for k, v in src.items():
        dst[k] += v


def fmt_chars(c: Counter) -> str:
    return " ".join(f"{ch}×{n}" for ch, n in c.most_common()) or "—"


def default_files() -> list[Path]:
    files: list[Path] = []
    for g in DEFAULT_GLOBS:
        files.extend(sorted(SERIES.glob(g)))
    return files


def run(files: list[Path], out_dir: Path | None) -> int:
    total = new_stats()
    rows: list[tuple[str, dict]] = []
    for p in files:
        text = p.read_text(encoding="utf-8")
        stats = new_stats()
        converted = convert_text(text, stats)
        rows.append((p.name, stats))
        for k in ("sub", "sup", "escape"):
            total[k] += stats[k]
        for k in ("sub_chars", "sup_chars", "escape_chars"):
            merge(total[k], stats[k])
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / p.name).write_text(converted, encoding="utf-8")
    print(f"文件 {len(files)}｜下标连续段 {total['sub']} 字｜上标连续段 {total['sup']} 字"
          f"｜转义 ^/~ {total['escape']} 处")
    print(f"  下标字符：{fmt_chars(total['sub_chars'])}")
    print(f"  上标字符：{fmt_chars(total['sup_chars'])}")
    print(f"  转义字符：{fmt_chars(total['escape_chars'])}")
    for name, s in rows:
        if s["sub"] or s["sup"] or s["escape"]:
            print(f"  {name}: sub {s['sub']} sup {s['sup']} escape {s['escape']}")
    if out_dir:
        print(f"派生副本 → {out_dir}/")
    return 0


def _convert_for_test(text: str) -> str:
    return convert_text(text, new_stats())


def selftest() -> int:
    ok = True

    def case(name: str, got: str, want: str) -> None:
        nonlocal ok
        good = got == want
        ok = ok and good
        print(("PASS " if good else "FAIL ") + name)
        if not good:
            print(f"  got : {got!r}\n  want: {want!r}")

    case("下标／上标／拉丁上标／ᵀ 基本转换",
         _convert_for_test("bₜ 与 10⁻⁵ 与 x² 与 σᵀ"),
         "b~t~ 与 10^−5^ 与 x^2^ 与 σ^T^")
    case("代码段不转、段外 ^ 转义",
         _convert_for_test("`QK^T` 与 QK^T 与 e^{−t}"),
         "`QK^T` 与 QK\\^T 与 e\\^{−t}")
    case("连续段合并（混合拉丁/Unicode 上标）",
         _convert_for_test("10¹⁰ 与 ⁻⁰⁴ 与 ₊₃"),
         "10^10^ 与 ^−04^ 与 ~+3~")
    case("围栏块整块不动",
         _convert_for_test("```\nbₜ 10⁻⁵ QK^T\n```\n正文ₜ\n"),
         "```\nbₜ 10⁻⁵ QK^T\n```\n正文~t~\n")
    case("波浪号转义（代码外）",
         _convert_for_test("`W ~ U(0,1)` 与 ~ref"),
         "`W ~ U(0,1)` 与 \\~ref")
    case("表格行内照转",
         _convert_for_test("| s(1.5) | e^24≈2.65×10¹⁰ |"),
         "| s(1.5) | e\\^24≈2.65×10^10^ |")
    print("sub/sup 转换器自测：" + ("all pass" if ok else "FAILED"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", metavar="DIR", help="写派生副本到 DIR（镜像文件名）")
    ap.add_argument("--files", nargs="*", metavar="MD", help="显式文件清单（默认全系列）")
    ap.add_argument("--selftest", action="store_true", help="内置对照自测")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    files = [Path(f) for f in args.files] if args.files else default_files()
    missing = [str(p) for p in files if not p.exists()]
    if missing:
        print("文件不存在：" + "，".join(missing), file=sys.stderr)
        return 2
    return run(files, Path(args.out) if args.out else None)


if __name__ == "__main__":
    sys.exit(main())
