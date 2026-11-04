#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从私有 edit 台账导出公开构建数据（series/data）。

`series/edit/` 整体是本地编辑档案，不随公开仓提交；公开构建和 CI 只读
`series/data/`。本脚本在本地维护：

    python3 series/tools/sync_public_data.py           # 重写 series/data/*
    python3 series/tools/sync_public_data.py --check   # 校验公开数据是否过期

术语备注会先用 `build_site._clean_note` 清洗，避免把编辑过程注记带进公开数据。
术语登记提案不导出：只有已并入术语总账的词才进入公开术语表。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERIES = HERE.parent
PRIVATE = SERIES / "edit"
PUBLIC = SERIES / "data"

sys.path.insert(0, str(HERE))
from build_site import _clean_note  # noqa: E402

TERMS = PRIVATE / "术语总账.tsv"
SYMBOLS = PRIVATE / "符号台账.tsv"
RULES = PRIVATE / "术语扫描规则.tsv"
REFERENCES = PRIVATE / "引用一致性.tsv"

SOURCES = (TERMS, SYMBOLS, RULES, REFERENCES)


def _rows(path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        cells = [c.strip() for c in line.split("\t")]
        if len(cells) >= 2 and cells[0] not in ("名词", "符号"):
            rows.append(cells)
    return rows


def _cell(text: str) -> str:
    return text.replace("\t", " ").replace("\n", " ").strip()


def _terms_text() -> str:
    out = [
        "# 公开术语数据：由私有 series/edit/术语总账.tsv 导出；备注已清洗。",
        "# 只读；更新私有台账后运行 series/tools/sync_public_data.py。",
        "名词\t首现章\t备注",
    ]
    for cells in _rows(TERMS):
        name = _cell(cells[0])
        first = _cell(cells[1]) if len(cells) > 1 else ""
        raw_note = "；".join(c for c in cells[2:] if c)
        if (("删除" in raw_note and "档案" in raw_note)
                or "已并入" in raw_note or "撤名退役" in raw_note):
            continue  # 与 build_site.terms_items 一致：废条不进公开术语表
        note = _clean_note(raw_note)
        out.append(f"{name}\t{first}\t{_cell(note)}")
    return "\n".join(out) + "\n"


def _symbols_text() -> str:
    out = [
        "# 公开符号数据：由私有 series/edit/符号台账.tsv 导出。",
        "# 只保留门禁所需字段；完整定义/复用规划留在私有台账。",
        "符号\t名称/读法\t首现章\t状态",
    ]
    for cells in _rows(SYMBOLS):
        vals = [cells[i] if len(cells) > i else "" for i in range(4)]
        out.append("\t".join(_cell(v) for v in vals))
    return "\n".join(out) + "\n"


def _copy_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return text if text.endswith("\n") else text + "\n"


def build_outputs() -> dict[Path, str]:
    return {
        PUBLIC / "术语总账.tsv": _terms_text(),
        PUBLIC / "符号台账.tsv": _symbols_text(),
        PUBLIC / "术语扫描规则.tsv": _copy_text(RULES),
        PUBLIC / "引用一致性.tsv": _copy_text(REFERENCES),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="从私有 edit 导出公开 series/data")
    ap.add_argument("--check", action="store_true", help="只校验，不写文件")
    args = ap.parse_args()

    missing = [p for p in SOURCES if not p.is_file()]
    if missing:
        print("私有 edit 源缺失，无法导出：" + "、".join(str(p) for p in missing), file=sys.stderr)
        return 2

    outputs = build_outputs()
    if args.check:
        stale = []
        for path, text in outputs.items():
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                stale.append(path.name)
        if stale:
            print("公开数据与私有 edit 不同步：" + "、".join(stale), file=sys.stderr)
            print("运行 python3 series/tools/sync_public_data.py", file=sys.stderr)
            return 1
        print(f"公开数据同步：{len(outputs)} 个文件 OK")
        return 0

    for path, text in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    print("已导出：" + "、".join(sorted(p.name for p in outputs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
