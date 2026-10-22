#!/usr/bin/env python3
"""轮次收尾一条龙：改动章检测→first_use/句长→全量总账/规则表→表格/残留→四仪→build 双跑→打勾表。

用法（仓库根；在 series/ 下把前缀换成 tools/）：
  python3 series/tools/finish_round.py                    # 门禁链（句长只打印、不入库）
  python3 series/tools/finish_round.py --stats "抽样 R9"   # 句长随动入库（备注前缀）
  python3 series/tools/finish_round.py --since HEAD~1      # 指定 diff 基线（默认 HEAD）
  python3 series/tools/finish_round.py --files a.md b.md   # 显式文件（跳过 diff 侦测）

规则：
  - 改动章＝git diff 中 series 根目录的章文件（§N[.M]／TN／支线*／导言*，.md）。
  - first_use 有 tracked edit/<文件名第一段>.edit.md 时查档案；v0.3 无档案时走
    --ledger-only（本地忽略的档案不参与自动门禁）。
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


def last_line(r: subprocess.CompletedProcess) -> str:
    """失败取 stderr，成功取 stdout；都没有则报“无输出”。"""
    if r.returncode != 0 and r.stderr.strip():
        text = r.stderr.strip()
    else:
        text = r.stdout.strip() or r.stderr.strip()
    return (text.splitlines() or ["无输出"])[-1]


def tracked_file(path: Path) -> bool:
    """只把版本库里的 edit 档案纳入自动门禁；本地忽略档案不参与。"""
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        return False
    r = subprocess.run(["git", "ls-files", "--error-unmatch", rel],
                       cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0


def digest_dist() -> str:
    h = hashlib.md5()
    for f in sorted((ROOT / "dist").rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(ROOT / "dist")).encode())
            h.update(f.read_bytes())
    return h.hexdigest()


def changed_chapters(since: str) -> list[Path] | None:
    # cwd=series；--relative 让 git 输出相对 series 的路径（根仓/独立仓都适用）。
    r = run(["git", "-c", "core.quotepath=false", "diff", "--relative",
             "--name-only", since])
    if r.returncode != 0:
        err = (r.stderr.strip().splitlines() or ["无输出"])[0]
        print(f"git diff 失败（--since {since}）：{err}", file=sys.stderr)
        return None
    paths = set(r.stdout.splitlines())
    # 新章可能还没 add，git diff 看不到；把未跟踪文件一并纳入。
    r2 = run(["git", "-c", "core.quotepath=false", "ls-files", "--others",
              "--exclude-standard"])
    if r2.returncode == 0:
        paths.update(r2.stdout.splitlines())
    out = []
    for ln in sorted(paths):
        p = Path(ln)
        if "/" in ln or not ln.endswith(".md") or not CH.match(p.name):
            continue
        if (ROOT / p).is_file():
            out.append(ROOT / p)
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
    GATES.clear()

    if args.files:
        chapters = []
        for f in args.files:
            p = Path(f)
            if not p.is_absolute() and not p.exists():
                alt = ROOT / p
                if alt.exists():
                    p = alt
            chapters.append(p.resolve())
    else:
        chapters = changed_chapters(args.since)
        if chapters is None:
            return 2
    print(f"改动章 {len(chapters)}：" + ("、".join(p.stem.split("-")[0] for p in chapters) or "无"))

    # 1) first_use ＋ 句长读数
    for p in chapters:
        key = p.name.split("-")[0] if "-" in p.name else p.stem
        edit = ROOT / "edit" / f"{key}.edit.md"
        cmd = [sys.executable, "tools/first_use_scan.py", str(p)]
        if edit.is_file() and tracked_file(edit):
            cmd += ["--edit", str(edit)]
        else:
            cmd += ["--ledger-only"]
        r = run(cmd)
        last = last_line(r)
        check(f"first_use {key}", r.returncode == 0 and "0 错" in last, last)
        r2 = run([sys.executable, "tools/sentence_stats.py", str(p), "--row"])
        print(f"    句长行：{r2.stdout.strip()[:110]}")

    # 全系列总账硬门禁：首现章＝首次正式处理；规则见 edit/术语扫描规则.tsv。
    r = run([sys.executable, "tools/first_use_scan.py", "--all",
             "--ledger-only", "--strict"])
    check("first_use --all --strict", r.returncode == 0, last_line(r))
    r = run([sys.executable, "tools/first_use_scan.py", "--check-rules"])
    check("first_use 规则表", r.returncode == 0, last_line(r))
    r = run([sys.executable, "tools/first_use_scan.py", "--all",
             "--ledger-only", "--strict", "--no-context-exempt"])
    check("first_use 规则显式化", r.returncode == 0, last_line(r))

    # 2) 表格与残留
    r = run([sys.executable, "tools/table_check.py"])
    last = last_line(r)
    check("table_check", r.returncode == 0, last)

    r = run([sys.executable, "tools/residue_scan.py"])
    last = last_line(r)
    check("residue_scan", r.returncode == 0, last)

    # 3) 句长随动入库（可选）
    if args.stats is not None and chapters:
        r = run([sys.executable, "tools/sentence_stats.py", *map(str, chapters),
                 "--update", "--note", args.stats])
        check("句长随动入库", r.returncode == 0, last_line(r))

    # row_check 必须在 --stats 回写之后跑，否则改稿轮会先红后绿。
    r = run([sys.executable, "tools/row_check.py"])
    last = last_line(r)
    check("row_check", r.returncode == 0, last)

    # 4) 四仪
    r = run([sys.executable, "tools/metaphor_scan.py", "--strict"])
    last = last_line(r)
    check("metaphor_scan --strict", r.returncode == 0, last if "候选" in last else "")

    r = run([sys.executable, "tools/route_lint.py", "--check"])
    last = last_line(r)
    check("route_lint --check", r.returncode == 0 and "后向 0" in last, last[:70])

    # 5) build 先行，series_check 必须对新鲜 dist 跑；再双跑对拍
    r = run([sys.executable, "tools/build_site.py"])
    check("build_site", r.returncode == 0, last_line(r))
    d1 = digest_dist()
    r = run([sys.executable, "tools/series_check.py"])
    ok = r.returncode == 0 and "all checks passed" in r.stdout
    detail = last_line(r)
    if not ok and "anchors 漂移" in r.stdout:
        detail += "（锚门对照 git HEAD：提交前必红属预期，提交后复跑即过）"
    check("series_check", ok, detail)
    r = run([sys.executable, "tools/build_site.py"])
    check("build_site 二跑", r.returncode == 0, last_line(r))
    d2 = digest_dist()
    check("build 双跑逐字节一致", d1 == d2, d1[:12] if d1 == d2 else f"{d1[:8]}≠{d2[:8]}")

    bad = [n for n, ok in GATES if not ok]
    print(f"\n收尾表：{len(GATES) - len(bad)}/{len(GATES)} 通过" +
          ("" if not bad else "　失败：" + "、".join(bad)))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
