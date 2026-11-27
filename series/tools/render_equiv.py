#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_equiv：渲染层黄金夹具回归（renderer_mdit 的常驻验收）。

`render_golden/` 下成对的 `.md`/`.html` 是渲染契约的黄金样本（M2 双引擎对拍
通过后固化；覆盖行内、列表、引用、代码块、表格 colgroup、raw HTML、软换行）。
本工具用 renderer_mdit 重渲染并逐字节比对；不一致退出 1。

更新黄金样本必须人工审 diff：先 `--update`，再逐对复核 `.html` 变化。

用法：
    python3 series/tools/render_equiv.py            # 校验
    python3 series/tools/render_equiv.py --update   # 重写黄金样本（审后提交）
    python3 series/tools/render_equiv.py --selftest # 校验器自测
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLDEN = HERE / "render_golden"

sys.path.insert(0, str(HERE))
import renderer_mdit  # noqa: E402


def pairs() -> list[tuple[Path, Path]]:
    return [(p, p.with_suffix(".html")) for p in sorted(GOLDEN.glob("*.md"))]


def first_diff(got: str, want: str) -> str:
    n = min(len(got), len(want))
    i = 0
    while i < n and got[i] == want[i]:
        i += 1
    ctx = 60
    return (f"第 {i} 字符：\n  got : {got[max(0, i - ctx):i + ctx]!r}\n"
            f"  want: {want[max(0, i - ctx):i + ctx]!r}")


def check(update: bool) -> int:
    bad = 0
    ps = pairs()
    if not ps:
        print("render_equiv：render_golden/ 为空", file=sys.stderr)
        return 2
    for md_path, html_path in ps:
        got = renderer_mdit.render(md_path.read_text(encoding="utf-8"))
        if update:
            html_path.write_text(got, encoding="utf-8")
            print(f"更新 {html_path.name}")
            continue
        want = html_path.read_text(encoding="utf-8")
        if got != want:
            bad += 1
            print(f"FAIL {md_path.name}")
            print(first_diff(got, want))
    if update:
        print(f"render_equiv：已更新 {len(ps)} 个黄金样本（请人工复核 diff）")
        return 0
    print(f"render_equiv：{len(ps)} 个样本，" + ("全部一致" if not bad else f"{bad} 个不一致"))
    return 0 if bad == 0 else 1


def selftest() -> int:
    ok = True
    # 1) 样本齐全
    if not pairs():
        print("FAIL 黄金样本缺失")
        return 1
    # 2) 现实校验应通过
    if check(update=False) != 0:
        ok = False
    # 3) 对照器能抓到差异
    a = "<p>甲</p>\n"
    b = "<p>乙</p>\n"
    if a == b or not first_diff(a, b):
        print("FAIL 差异定位器")
        ok = False
    print("render_equiv 自测：" + ("all pass" if ok else "FAILED"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--update", action="store_true", help="重写黄金样本（审后提交）")
    ap.add_argument("--selftest", action="store_true", help="校验器自测")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    return check(update=args.update)


if __name__ == "__main__":
    sys.exit(main())
