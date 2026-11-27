#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 series/README.md（GitHub 上的阅读入口）。

结构单一来源：profiles/chapters.json + profiles/routes.json + profiles/release.json。
章题单一来源：各单元 md 的 H1（display_title 去读法标记与号前缀），文件名只作路径。
--check 另验根 README 的六个组标签与版本号在位。

用法:
    python3 series/tools/build_readme.py            # 写入 series/README.md
    python3 series/tools/build_readme.py --check    # 只比对，不一致退出 1（CI 用）
    python3 series/tools/build_readme.py --selftest # 纯函数自检
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
SERIES = HERE.parent
PROFILES = SERIES / "profiles"
OUT = SERIES / "README.md"
ROOT_README = SERIES.parent / "README.md"

sys.path.insert(0, str(HERE))
from prose_common import display_title  # noqa: E402


def load(name: str) -> dict:
    return json.loads((PROFILES / name).read_text(encoding="utf-8"))


def q(s: str) -> str:
    return quote(s, safe="")


def norm_label(s: str) -> str:
    """组标签比对口径：去掉空白与间隔号（根 README 的流程图不带「·」）。"""
    return re.sub(r"[\s·]+", "", s)


def root_issues(root_text: str, parts: list[dict], version: str) -> list[str]:
    """根 README 与 chapters/release 的对账：六个组标签 + 版本号。"""
    flat = norm_label(root_text)
    issues = [f"根 README 缺组标签：{p['label']}" for p in parts
              if norm_label(p["label"]) not in flat]
    if version and f"v{version}" not in root_text:
        issues.append(f"根 README 缺版本号：v{version}")
    return issues


def unit_headline(chapters: dict) -> tuple[str, str]:
    """按 chapters.json 的实际组成生成单元总数行与小节标题。

    旧版把「32 个阅读单元：开篇 5 节」写死在 render 里，chapters.json 改成 31/4
    后表体随数据走、头部不动，--check 仍全绿。这里改为同源计数，并断言总数与
    分篇数对得上；支线固定为 导言＋T1–T4＋补页 六项。
    """
    rows = chapters["chapters"]
    counts = Counter(c["part"] for c in rows)
    total = len(rows)
    if total != sum(counts.values()):
        raise ValueError(f"单元总数 {total} ≠ 分篇计数之和 {sum(counts.values())}")
    if counts.get("branch") != 6:
        raise ValueError(f"支线单元数 {counts.get('branch')} ≠ 6（导言＋T1–T4＋补页）")
    detail = (
        f"开篇 {counts.get('zero', 0)} 节＋第一篇 {counts.get('build', 0)} 章＋"
        f"支线导言＋T1–T4＋补页＋第二篇 {counts.get('law', 0)} 章＋"
        f"第三篇 {counts.get('drive', 0)} 章＋终篇 {counts.get('frontier', 0)} 章"
    )
    return f"> {total} 个阅读单元：{detail}。", f"## {total} 个单元"


def render() -> str:
    chapters = load("chapters.json")
    routes = load("routes.json")
    release = load("release.json")
    parts = {p["id"]: p["label"] for p in chapters["parts"]}
    version = release.get("version", "")
    date = release.get("date", "")
    headline, section_title = unit_headline(chapters)

    out: list[str] = []
    out.append(f"# AI 系列读物 · v{version}")
    out.append("")
    out.append(headline)
    out.append("")
    out.append("## 在线阅读")
    out.append("")
    out.append("- [目录 / 路线向导](./dist/index.html)")
    out.append("- [术语总表](./dist/terms.html)")
    out.append("- [路线与论文清单](./dist/routes.html)")
    out.append("- [环境指南](./dist/env.html)")
    out.append("- [数学自修自测](./dist/selftest.html)")
    out.append("- [资产索引](./dist/assets.html)")
    out.append("")
    out.append(section_title)
    out.append("")
    out.append("| 篇 | 号 | 章题 | 源稿 | 在线 |")
    out.append("| --- | --- | --- | --- | --- |")
    for c in chapters["chapters"]:
        part = parts.get(c["part"], c["part"])
        title = display_title(SERIES / c["file"], c["label"])
        out.append(
            f"| {part} | {c['label']} | {title} "
            f"| [md](./{q(c['file'])}) | [读](./dist/{c['slug']}.html) |"
        )
    out.append("")
    out.append("## 路线目标")
    out.append("")
    out.append("| 目标 | 组内走法 |")
    out.append("| --- | --- |")
    by_id = {r["id"]: r for r in routes["routes"]}
    for g in routes.get("groups", []):
        labels = []
        for rid in g["routes"]:
            r = by_id[rid]
            label = r["title"]
            if r.get("tag") and r["tag"] not in label:
                label += f"（{r['tag']}）"
            labels.append(f"[{label}](./dist/routes.html#route-{rid})")
        out.append(f"| {g['title']} | {'、'.join(labels)} |")
    out.append("")
    out.append("## 构建与门禁")
    out.append("")
    out.append("```bash")
    out.append("python3 -m pip install -r build/requirements-build.txt")
    out.append("python3 series/tools/build_site.py")
    out.append("python3 series/tools/series_check.py")
    out.append("python3 series/tools/build_readme.py --check")
    out.append("python3 series/tools/first_use_scan.py --all --ledger-only --strict")
    out.append("```")
    out.append("")
    out.append("改稿收尾：`python3 series/tools/finish_round.py`；工具索引见")
    out.append("`series/tools/README.md`。配图：`figures/`（`generate_figures.py` 单一来源）；")
    out.append("动手实验：`assets/`；术语与符号数据：`data/*.tsv`；写作规范：`style/`。")
    out.append("")
    return "\n".join(out)


def _fake_chapters(counts: dict[str, int]) -> dict:
    rows: list[dict] = []
    for part, n in counts.items():
        rows.extend({"part": part} for _ in range(n))
    return {"chapters": rows}


def selftest() -> int:
    parts = [{"label": "开篇 · 总览与读法"}, {"label": "支线 · 扩散专题"}]
    good = "开篇 总览与读法（3 节）\n支线 扩散专题（导言＋T1–T4）\nv0.3.6\n"
    bad = "开篇 总览与读法\nv0.3.6\n"
    root_ok = (root_issues(good, parts, "0.3.6") == []
               and root_issues(bad, parts, "0.3.6")
               == ["根 README 缺组标签：支线 · 扩散专题"]
               and root_issues("支线扩散专题", parts, "0.3.6")
               == ["根 README 缺组标签：开篇 · 总览与读法", "根 README 缺版本号：v0.3.6"])
    headline, title = unit_headline(_fake_chapters(
        {"zero": 4, "build": 9, "law": 5, "drive": 5, "frontier": 2, "branch": 6}))
    count_ok = (headline.startswith("> 31 个阅读单元：开篇 4 节")
                and title == "## 31 个单元")
    bad_ok = False
    try:
        unit_headline(_fake_chapters(
            {"zero": 4, "build": 9, "law": 5, "drive": 5, "frontier": 2, "branch": 5}))
    except ValueError:
        bad_ok = True
    ok = root_ok and count_ok and bad_ok
    print("build_readme selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="生成 series/README.md")
    ap.add_argument("--check", action="store_true", help="只比对，不写入")
    ap.add_argument("--selftest", action="store_true", help="纯函数自检")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    text = render()
    if args.check:
        old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if old != text:
            print("series/README.md 与生成结果不一致；运行 build_readme.py 刷新", file=sys.stderr)
            return 1
        print("series/README.md: OK")
        if not ROOT_README.is_file():
            print(f"根 README 缺失：{ROOT_README}", file=sys.stderr)
            return 1
        issues = root_issues(ROOT_README.read_text(encoding="utf-8"),
                             load("chapters.json")["parts"],
                             load("release.json").get("version", ""))
        if issues:
            for x in issues:
                print(x, file=sys.stderr)
            return 1
        print("根 README 组标签与版本号: OK")
        return 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"✓ {OUT.relative_to(SERIES)}（{len(text.splitlines())} 行）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
