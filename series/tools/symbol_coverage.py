#!/usr/bin/env python3
"""symbol_coverage：符号纪律的机械核对（方案原则 11"符号纪律"的底座）。

读 edit/符号台账.tsv，四项核对：
  FAIL 缺席   "已立"符号在其首现章文件中一次也没出现
              （台账 "m_t / v_t" 这类复合项按 "/" 拆分逐个查）
  FAIL 越界   第〇部文件（§0.1–§0.3）出现任何"已立"符号（特许边界）
  逐章计数表  每章命中已立符号数 / 已立符号总数，附命中清单
  WARN 孤立重现  已立符号出现在非首现章、且该章已立符号命中总数 ≤1
              （孤立出现、上下文没有记号群）——提示人工判断：
              是否需回指，或正被无解释重释

匹配口径：ASCII 字母数字符号（x、f(x)、g_t、L 等）用词边界正则，
防 "ax" 里的 x 误命中；含数学记号（η、∇f、σ² 等）的按字面查。
复合项拆分后去重（如 "μ / σ²" 与 "N(μ, σ²)" 各自独立计）。

退出码：恒 0（本器只打屏报告，不绊流水线；FAIL 由人工裁决）。
报告文件：first_use_scan 无写报告惯例，本器同样只打屏。

用法：
  python series/tools/symbol_coverage.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # series/
LEDGER = ROOT / "edit" / "符号台账.tsv"

ASCII_SYM = re.compile(r"^[A-Za-z0-9_]+$|^[A-Za-z0-9_]+[\(\)]")


def split_atoms(symbol: str) -> list[str]:
    """台账符号列拆成原子符号："m_t / v_t" → ["m_t", "v_t"]。"""
    return [s.strip() for s in re.split(r"[／/]", symbol) if s.strip()]


def matcher(symbol: str):
    """ASCII 符号给词边界，其余字面查。"""
    core = re.escape(symbol)
    if ASCII_SYM.match(symbol):
        return re.compile(rf"(?<![A-Za-z0-9_]){core}(?![A-Za-z0-9_])")
    if re.match(r"^[A-Za-z]", symbol):  # N(μ, σ²) 这类：守头边界即可
        return re.compile(rf"(?<![A-Za-z0-9_]){core}")
    return re.compile(core)


def chapter_files(uid: str) -> list[Path]:
    """§2 → series/§2-*.md；§0.1 → series/§0.1-*.md。"""
    return sorted(ROOT.glob(f"{uid}-*.md"))


def load_ledger() -> list[dict]:
    rows = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("符号") or line.startswith("#"):
            continue
        cells = line.split("\t")
        if len(cells) >= 3 and cells[0].strip():
            rows.append({"symbol": cells[0].strip(), "uid": cells[2].strip(),
                         "status": cells[3].strip() if len(cells) > 3 else ""})
    return rows


def main() -> int:
    if not LEDGER.exists():
        print(f"ERROR 台账不存在：{LEDGER}")
        return 0
    rows = load_ledger()
    standing = [r for r in rows if r["status"] == "已立"]

    # 原子符号清单（复合拆分、去重、保序）
    atoms: list[str] = []
    for r in standing:
        for a in split_atoms(r["symbol"]):
            if a not in atoms:
                atoms.append(a)
    pats = {a: matcher(a) for a in atoms}

    fails: list[str] = []
    print(f"symbol_coverage：台账已立 {len(standing)} 行 → 原子符号 {len(atoms)} 个")

    # 检查 1：已立符号在其首现章至少出现一次
    print("\n-- 检查 1：首现章在场 --")
    for r in standing:
        files = chapter_files(r["uid"])
        if not files:
            fails.append(f"首现章无文件：{r['uid']}（{r['symbol']}）")
            print(f"FAIL  {r['uid']}：找不到 {r['uid']}-*.md")
            continue
        text = "\n".join(f.read_text(encoding="utf-8") for f in files)
        missing = [a for a in split_atoms(r["symbol"])
                   if not pats[a].search(text)]
        if missing:
            fails.append(f"缺席：{'/'.join(missing)} 不在 {r['uid']}")
            print(f"FAIL  {r['symbol']}：{'/'.join(missing)} 未在 {r['uid']} 出现")
        else:
            print(f"PASS  {r['symbol']}：{r['uid']} 在场")

    # 检查 2：第〇部（§0.1–§0.3）零已立符号
    print("\n-- 检查 2：第〇部特许边界 --")
    for uid in ("§0.1", "§0.2", "§0.3"):
        files = chapter_files(uid)
        if not files:
            print(f"PASS  {uid}：无文件（跳过）")
            continue
        text = "\n".join(f.read_text(encoding="utf-8") for f in files)
        hits = [a for a in atoms if pats[a].search(text)]
        if hits:
            fails.append(f"越界：{uid} 出现已立符号 {'/'.join(hits)}")
            print(f"FAIL  {uid}：出现已立符号 {'/'.join(hits)}")
        else:
            print(f"PASS  {uid}：零已立符号")

    # 检查 3：逐章符号计数表
    print("\n-- 检查 3：逐章已立符号计数 --")
    print(f"{'章':<8}{'命中':>4} / {len(atoms)}   命中清单")
    chapters = sorted(p for p in ROOT.glob("§*.md"))
    for ch in chapters:
        uid = ch.stem.split("-")[0]
        text = ch.read_text(encoding="utf-8")
        hits = [a for a in atoms if pats[a].search(text)]
        mark = "  ← 首现章" if uid in {r["uid"] for r in standing} else ""
        print(f"{uid:<8}{len(hits):>4} / {len(atoms)}   {'、'.join(hits) or '—'}{mark}")

    # 检查 4：孤立重现 WARN——非首现章里已立符号 lone 出现（该章命中总数 ≤1）
    print("\n-- 检查 4：孤立重现 WARN --")
    first_uids = {r["uid"] for r in standing}
    warns = 0
    for ch in chapters:
        uid = ch.stem.split("-")[0]
        if uid in first_uids:
            continue  # 首现章豁免：新符号集中首现，本就"没有记号群"
        text = ch.read_text(encoding="utf-8")
        hits = [a for a in atoms if pats[a].search(text)]
        if 1 <= len(hits) <= 1:
            for a in hits:
                print(f"WARN  {uid}：{a} 孤立出现（全章已立符号仅 {len(hits)} 个，"
                      f"上下文没有记号群）——人工判断：是否需回指，或被无解释重释")
                warns += 1
    if warns == 0:
        print("（无孤立重现）")

    print()
    for f in fails:
        print(f"FAIL {f}")
    print(f"symbol_coverage：{len(fails)} 项 FAIL / {warns} 项 WARN / 退出码恒 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
