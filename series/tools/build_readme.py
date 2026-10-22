#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 series/README.md（GitHub 上的 30 单元阅读入口）。

单一来源：profiles/chapters.json + profiles/routes.json + profiles/release.json。
不新增内容，只把已有结构排成可点的目录。

用法:
    python3 series/tools/build_readme.py            # 写入 series/README.md
    python3 series/tools/build_readme.py --check    # 只比对，不一致退出 1（CI 用）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
SERIES = HERE.parent
PROFILES = SERIES / "profiles"
OUT = SERIES / "README.md"


def load(name: str) -> dict:
    return json.loads((PROFILES / name).read_text(encoding="utf-8"))


def q(s: str) -> str:
    return quote(s, safe="")


def render() -> str:
    chapters = load("chapters.json")
    routes = load("routes.json")
    release = load("release.json")
    parts = {p["id"]: p["label"] for p in chapters["parts"]}
    version = release.get("version", "")
    date = release.get("date", "")

    out: list[str] = []
    out.append(f"# AI 系列读物 · 重写版 v{version}")
    out.append("")
    out.append("> 30 个阅读单元：第〇部 3 节＋第一部 9 章＋支线导言/配方页＋T1–T4＋第二部 5 章＋第三部 7 章。")
    out.append(f"> 构建日期：{date}。旧五篇参考版见根仓 tag `five-books-final`，已停止维护。")
    out.append("")
    out.append("## 在线阅读")
    out.append("")
    out.append("- [目录 / 路线向导](./dist/index.html)")
    out.append("- [全文打印版](./dist/print.html)")
    out.append("- [术语总表](./dist/terms.html)")
    out.append("- [路线与论文清单](./dist/routes.html)")
    out.append("- [环境指南](./dist/env.html)")
    out.append("- [数学自修自测](./dist/selftest.html)")
    out.append("- [资产索引](./dist/assets.html)")
    out.append("")
    out.append("## 30 个单元")
    out.append("")
    out.append("| 部 | 号 | 章题 | 源稿 | 在线 |")
    out.append("| --- | --- | --- | --- | --- |")
    for c in chapters["chapters"]:
        part = parts.get(c["part"], c["part"])
        out.append(
            f"| {part} | {c['label']} | {c['file'].split('-', 1)[1].rsplit('.md', 1)[0]} "
            f"| [md](./{q(c['file'])}) | [读](./dist/{c['slug']}.html) |"
        )
    out.append("")
    out.append("## 九条路线")
    out.append("")
    out.append("| 路线 | 类型 | 适合谁 |")
    out.append("| --- | --- | --- |")
    for r in routes["routes"]:
        out.append(
            f"| [{r['title']}](./dist/routes.html#route-{r['id']}) "
            f"| {r.get('tag', '')} | {r.get('audience', '')} |"
        )
    out.append("")
    out.append("## 构建与门禁")
    out.append("")
    out.append("```bash")
    out.append("python3 series/tools/build_site.py")
    out.append("python3 series/tools/series_check.py")
    out.append("python3 series/tools/build_readme.py --check")
    out.append("python3 series/tools/first_use_scan.py --all --ledger-only --strict")
    out.append("python3 build/check_artifact_fresh.py")
    out.append("```")
    out.append("")
    out.append("改稿收尾：`python3 series/tools/finish_round.py`；工具索引见")
    out.append("`series/tools/README.md`。配图：`figures/`（`generate_figures.py` 单一来源）；")
    out.append("动手实验：`assets/`；术语与符号台账：`edit/*.tsv`；写作规范：`style/`。")
    out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="生成 series/README.md")
    ap.add_argument("--check", action="store_true", help="只比对，不写入")
    args = ap.parse_args()
    text = render()
    if args.check:
        old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if old != text:
            print("series/README.md 与生成结果不一致；运行 build_readme.py 刷新", file=sys.stderr)
            return 1
        print("series/README.md: OK")
        return 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"✓ {OUT.relative_to(SERIES)}（{len(text.splitlines())} 行）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
