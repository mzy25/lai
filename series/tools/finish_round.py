#!/usr/bin/env python3
"""轮次收尾一条龙：改动章检测→first_use→句长（可选入库）→四仪→build 双跑→打勾表。

用法：
  python3 tools/finish_round.py                    # 门禁链（句长只打印、不入库）
  python3 tools/finish_round.py --stats "抽样 R9"   # 句长随动入库（备注前缀）
  python3 tools/finish_round.py --since HEAD~1      # 指定 diff 基线（默认 HEAD）
  python3 tools/finish_round.py --files a.md b.md   # 显式文件（跳过 diff 侦测）

规则：
  - 改动章＝git diff 中根目录的章文件（§N[.M]／TN／支线*／导言*，.md）。
  - first_use 自动配 edit/<文件名第一段>.edit.md（存在才传 --edit）。
  - 任一仪失败 → 退出码 1，末尾打勾表标 ✗。
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CH = re.compile(r"^(§\d+(\.\d+)?|T\d|支线|导言)")
GATES: list[tuple[str, bool]] = []


def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True)


def digest_dist() -> str:
    h = hashlib.md5()
    for f in sorted((ROOT / "dist").rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(ROOT / "dist")).encode())
            h.update(f.read_bytes())
    return h.hexdigest()


def changed_chapters(since: str) -> list[Path]:
    r = run(["git", "-c", "core.quotepath=false", "diff", "--name-only", since])
    out = []
    for ln in r.stdout.splitlines():
        p = Path(ln)
        if "/" in ln or not ln.endswith(".md") or not CH.match(p.name):
            continue
        if (ROOT / p).exists():
            out.append(p)
    return out


def check(name: str, ok: bool, detail: str = "") -> None:
    GATES.append((name, ok))
    print(f"  {'✓' if ok else '✗'} {name}{'：' + detail if detail else ''}")


def main() -> int:
    ap = argparse.ArgumentParser(description="轮次收尾一条龙")
    ap.add_argument("--files", nargs="*", help="显式章文件（跳过 diff 侦测）")
    ap.add_argument("--since", default="HEAD", help="diff 基线（默认 HEAD）")
    ap.add_argument("--stats", default=None, metavar="NOTE",
                    help="句长随动入库，NOTE 为备注前缀（如「抽样 R9」）")
    args = ap.parse_args()

    if args.files:
        chapters = [Path(f) for f in args.files]
    else:
        chapters = changed_chapters(args.since)
    print(f"改动章 {len(chapters)}：" + ("、".join(p.stem.split("-")[0] for p in chapters) or "无"))

    # 1) first_use ＋ 句长读数
    for p in chapters:
        key = p.name.split("-")[0] if "-" in p.name else p.stem
        edit = ROOT / "edit" / f"{key}.edit.md"
        cmd = [sys.executable, "tools/first_use_scan.py", str(p)]
        if edit.exists():
            cmd += ["--edit", str(edit)]
        r = run(cmd)
        last = (r.stdout.strip().splitlines() or ["无输出"])[-1]
        check(f"first_use {key}", "0 错" in last, last)
        r2 = run([sys.executable, "tools/sentence_stats.py", str(p), "--row"])
        print(f"    句长行：{r2.stdout.strip()[:110]}")

    # 2) 句长随动入库（可选）
    if args.stats is not None and chapters:
        r = run([sys.executable, "tools/sentence_stats.py", *map(str, chapters),
                 "--update", "--note", args.stats])
        check("句长随动入库", r.returncode == 0, (r.stdout.strip().splitlines() or [""])[-1])

    # 3) 四仪
    r = run([sys.executable, "tools/metaphor_scan.py", "--strict"])
    tail = (r.stdout.strip().splitlines() or [""])[-1]
    check("metaphor_scan --strict", r.returncode == 0, tail if "候选" in tail else "")

    r = run([sys.executable, "tools/route_lint.py", "--check"])
    last = (r.stdout.strip().splitlines() or [""])[-1]
    check("route_lint --check", r.returncode == 0 and "后向 0" in last, last[:70])

    # 4) build 先行，series_check 必须对新鲜 dist 跑；再双跑对拍
    run([sys.executable, "tools/build_site.py"])
    d1 = digest_dist()
    r = run([sys.executable, "tools/series_check.py"])
    ok = "all checks passed" in r.stdout
    detail = (r.stdout.strip().splitlines() or [""])[-1]
    if not ok and "anchors 漂移" in r.stdout:
        detail += "（锚门对照 git HEAD：提交前必红属预期，提交后复跑即过）"
    check("series_check", ok, detail)
    run([sys.executable, "tools/build_site.py"])
    d2 = digest_dist()
    check("build 双跑逐字节一致", d1 == d2, d1[:12] if d1 == d2 else f"{d1[:8]}≠{d2[:8]}")

    bad = [n for n, ok in GATES if not ok]
    print(f"\n收尾表：{len(GATES) - len(bad)}/{len(GATES)} 通过" +
          ("" if not bad else "　失败：" + "、".join(bad)))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
