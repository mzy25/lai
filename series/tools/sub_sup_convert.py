#!/usr/bin/env python3
"""系列构建期字形转换器：Unicode 上下标 → 原生 HTML `<sub>/<sup>`（引擎中立）。

背景（2026-10-12 字形批）：系列数学体例＝Unicode 记号（波二裁决，源稿不改）。
产物字体对 ₜ ₁ ₂ ₀ ₅ ⁻ 等缺字形（Noto CJK 系实测全缺；DejaVu 系全有）。直接
输出 `<sub>/<sup>` 后由排版层承担，构建不依赖字体，也不依赖任何 Markdown
扩展语法（2026-11-27 M1：取消 pandoc `~x~`/`^x^` 与 ASCII `^`/`~` 转义层，
输出行为不变）。代码段（`…`）与围栏块（```）内一律不动。

用法（在 series/ 任意位置）：
    python3 tools/sub_sup_convert.py                  # 只报计数（dry-run，exit 0）
    python3 tools/sub_sup_convert.py --out DIR        # 写派生副本（镜像文件名）
    python3 tools/sub_sup_convert.py --selftest       # 内置好样/坏样对照
    python3 tools/sub_sup_convert.py --files A.md B.md

默认文件集：§*.md、T*.md、支线导言-*.md、支线补页-*.md、支线附录-*.md。
非目标：不写回源稿；派生副本只喂构建。转换幂等（Unicode 上下标只转一次，
输出已是 HTML；ASCII `^`/`~` 原样保留）。
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

DEFAULT_GLOBS = ("§*.md", "T*.md", "支线导言-*.md", "支线补页-*.md", "支线附录-*.md")


def convert_segment(seg: str, stats: dict) -> str:
    """转换一个非代码段：连续 Unicode 上下标 → 原生 <sub>/<sup>。"""
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
        tag = "sub" if table is SUB else "sup"
        out.append(f"<{tag}>{content}</{tag}>")
        stats[tag] += j - i
        for c in seg[i:j]:
            stats[f"{tag}_chars"][c] += 1
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
    return {"sub": 0, "sup": 0,
            "sub_chars": Counter(), "sup_chars": Counter()}


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
        for k in ("sub", "sup"):
            total[k] += stats[k]
        for k in ("sub_chars", "sup_chars"):
            merge(total[k], stats[k])
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / p.name).write_text(converted, encoding="utf-8")
    print(f"文件 {len(files)}｜下标连续段 {total['sub']} 字｜上标连续段 {total['sup']} 字")
    print(f"  下标字符：{fmt_chars(total['sub_chars'])}")
    print(f"  上标字符：{fmt_chars(total['sup_chars'])}")
    for name, s in rows:
        if s["sub"] or s["sup"]:
            print(f"  {name}: sub {s['sub']} sup {s['sup']}")
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
         "b<sub>t</sub> 与 10<sup>−5</sup> 与 x<sup>2</sup> 与 σ<sup>T</sup>")
    case("代码段不转、段外 ASCII ^ ~ 原样保留",
         _convert_for_test("`QK^T` 与 QK^T 与 e^{−t}"),
         "`QK^T` 与 QK^T 与 e^{−t}")
    case("连续段合并（混合拉丁/Unicode 上标）",
         _convert_for_test("10¹⁰ 与 ⁻⁰⁴ 与 ₊₃"),
         "10<sup>10</sup> 与 <sup>−04</sup> 与 <sub>+3</sub>")
    case("围栏块整块不动",
         _convert_for_test("```\nbₜ 10⁻⁵ QK^T\n```\n正文ₜ\n"),
         "```\nbₜ 10⁻⁵ QK^T\n```\n正文<sub>t</sub>\n")
    case("波浪号原样（不再转义）",
         _convert_for_test("`W ~ U(0,1)` 与 ~ref"),
         "`W ~ U(0,1)` 与 ~ref")
    case("表格行内照转",
         _convert_for_test("| s(1.5) | e^24≈2.65×10¹⁰ |"),
         "| s(1.5) | e^24≈2.65×10<sup>10</sup> |")
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
