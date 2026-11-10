#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_tools：工具自检总入口。

用法：
    python3 series/tools/selftest_tools.py            # 只跑正文审阅工具（快）
    python3 series/tools/selftest_tools.py --all      # 追加核心工具
    python3 series/tools/selftest_tools.py --quiet    # 只打失败
    python3 series/tools/selftest_tools.py --selftest # 检查清单本身

退出码：0 全过；1 有失败；2 清单/文件错误。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

PROSE = [
    ("prose_common.py", []),
    ("reader_packet.py", ["--selftest"]),
    ("prose_diff.py", ["--selftest"]),
    ("section_map.py", ["--selftest"]),
    ("coherence_scan.py", ["--selftest"]),
    ("logic_lint.py", ["--selftest"]),
    ("consistency_scan.py", ["--selftest"]),
    ("phase01.py", ["--selftest"]),
    ("answer_mirror_check.py", ["--selftest"]),
    ("ripple_check.py", ["--selftest"]),
    ("blind_pair.py", ["--selftest"]),
    ("review_log.py", ["--selftest"]),
]
CORE = [
    ("sentence_stats.py", ["--selftest"]),
    ("first_use_scan.py", ["--selftest"]),
    ("metaphor_scan.py", ["--selftest"]),
    ("reference_lint.py", ["--selftest"]),
    ("table_check.py", ["--selftest"]),
    ("cliche_scan.py", ["--selftest"]),
    ("taste_probe.py", ["--selftest"]),
    ("sub_sup_convert.py", ["--selftest"]),
    ("series_check.py", ["--selftest"]),
    ("build_site.py", ["--selftest"]),
]


def run_one(name: str, args: list[str], quiet: bool) -> bool:
    path = HERE / name
    if not path.is_file():
        print(f"FAIL {name}: 文件不存在")
        return False
    try:
        p = subprocess.run([sys.executable, str(path), *args],
                           capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        print(f"FAIL {name}: 超时 120s")
        return False
    out = ((p.stdout or "") + (p.stderr or "")).strip()
    last = next((l for l in reversed(out.splitlines()) if l.strip()), "")
    ok = p.returncode == 0
    if not quiet or not ok:
        print(f"{'PASS' if ok else 'FAIL'} {name}" + (f"  {last}" if last else ""))
    return ok


def selftest() -> int:
    missing = [n for n, _ in PROSE + CORE if not (HERE / n).is_file()]
    if missing:
        print("selftest_tools selftest: FAIL 缺文件 " + ", ".join(missing))
        return 1
    print(f"selftest_tools selftest: PASS（prose {len(PROSE)}，core {len(CORE)}）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true", help="追加核心工具")
    ap.add_argument("--quiet", action="store_true", help="只打失败")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    tools = PROSE + (CORE if args.all else [])
    failed = [name for name, cmd in tools if not run_one(name, cmd, args.quiet)]
    total = len(tools)
    print(f"\n工具自检：{total - len(failed)}/{total} 通过")
    if failed:
        print("失败：" + "、".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
