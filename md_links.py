#!/usr/bin/env python3
"""md 内链修复：把 `](#anchor)` 改写为 pandoc 实际会生成的标题 id。

HTML/DOCX 两条构建管线共用。源稿里的目录锚点按 GitHub slug 习惯手写
（保留 ——、省略空格连字符），与 pandoc gfm_auto_identifiers 生成的
标题 id 多数一致、但仍有差异。这里不猜 pandoc 的 id 算法，而是用
pandoc 自身（与真实转换**相同的 reader 参数**）只读转一遍 harvest 出
全部标题 id，再把每个锚点按规范化（去标点、小写、保留 ASCII 字母数字
与 CJK）精确匹配到 id。匹配成功 → 改写；失败 → 不改写并告警。

失败策略（调用方只负责打印 warnings）：
- pandoc 不可用 / 非零退出 → 抛 RuntimeError，构建中止。
  内链是内容正确性的一部分，静默降级会产出"看起来正常、点不动"的成品。
- 单个锚点解析不了 → 保留原文 + warning，不中止构建（一个断链不应
  阻塞其他内容构建；但构建日志必须可见，标题改名后即刻暴露）。
- 两个标题 id 规范化后撞车 → 弃用该映射 + warning（宁可留断链，不猜）。

用法:
    text, warnings, id_set = fix_internal_links(md_text, cwd, from_flags)
    # text: 改写后的 md；warnings: 告警列表；id_set: harvest 出的标题 id 集合
    # （HTML 管线在 bump_headings 加 doc-N- 前缀后，用它做纯精确的前缀回写）
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

# 规范化：只保留 ASCII 字母数字 + CJK（常用区 + 扩展 A），全部小写，
# 其余（标点、——、-、空格、$、_ 等）一律丢弃。
_CANON = re.compile(r'[^0-9a-z\u4e00-\u9fff\u3400-\u4dbf]')
_HEADING_ID = re.compile(r'<h[1-6][^>]*\bid="([^"]+)"')
_LINK = re.compile(r'\]\(#([^)\s]+)\)')
_FENCE = re.compile(r'^\s*(```|~~~)')

# pandoc reader 参数：harvest 与两条管线的真实转换共用，保证 id 一字不差。
# gfm_auto_identifiers 让标题 id 按 GitHub slug 规则生成（与源稿目录锚点同源）。
FROM_FLAGS = ("markdown+gfm_auto_identifiers+tex_math_dollars"
              "+raw_tex-yaml_metadata_block")


def canon(s: str) -> str:
    return _CANON.sub('', s.lower())


def harvest_ids(md_text: str, cwd: Path, from_flags: str) -> list[str]:
    """用 pandoc（与真实转换同参数）只读转一遍，harvest 标题 id（文档序）。"""
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                     suffix=".md", delete=False) as f:
        f.write(md_text)
        tmp_path = f.name
    try:
        try:
            r = subprocess.run(
                ["pandoc", tmp_path, "-t", "html", "--wrap=none",
                 f"--from={from_flags}"],
                cwd=cwd, capture_output=True, text=True)
        except FileNotFoundError as e:
            raise RuntimeError(
                "md_links: pandoc 不可用，无法解析内链——请先安装 pandoc") from e
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    if r.returncode != 0:
        raise RuntimeError(
            f"md_links: pandoc harvest 失败（退出码 {r.returncode}）: "
            f"{r.stderr[:500]}")
    return _HEADING_ID.findall(r.stdout)


def _rewrite_segment(text: str, cmap: dict[str, str],
                     warnings: list[str]) -> str:
    """对一段（非围栏）文本改写锚点；解析不了的保留原文并告警。"""

    def repl(m: re.Match) -> str:
        anchor = m.group(1)
        rid = cmap.get(canon(anchor))
        if rid is None:
            warnings.append(f"内链未解析（保留原文）：#{anchor}")
            return m.group(0)
        return f"](#{rid})"

    return _LINK.sub(repl, text)


def fix_internal_links(md_text: str, cwd: Path,
                       from_flags: str) -> tuple[str, list[str], set[str]]:
    """改写内链锚点 → pandoc 实际 id。

    from_flags: 与真实 pandoc 转换完全相同的 reader 参数（如
    'markdown+gfm_auto_identifiers+tex_math_dollars+raw_tex-yaml_metadata_block'），
    保证 harvest 出的 id 与成品里的 id 一字不差。
    """
    warnings: list[str] = []
    raw_ids = harvest_ids(md_text, cwd, from_flags)

    # canon → id 映射；撞车的 canon 弃用（不猜）
    cmap: dict[str, str] = {}
    collided: set[str] = set()
    for rid in raw_ids:
        c = canon(rid)
        if c in collided:
            continue
        if c in cmap:
            collided.add(c)
            del cmap[c]
            warnings.append(f"标题 id 规范化撞车，弃用映射：{rid}")
        else:
            cmap[c] = rid

    # 围栏感知：只改写围栏外的段落（代码块里的 ](#... 是字面内容）
    lines = md_text.split("\n")
    out: list[str] = []
    buf: list[str] = []
    in_fence = False
    for line in lines:
        if _FENCE.match(line):
            out.append(_rewrite_segment("\n".join(buf), cmap, warnings))
            buf = []
            out.append(line)
            in_fence = not in_fence
            continue
        if in_fence:
            out.append(line)
        else:
            buf.append(line)
    out.append(_rewrite_segment("\n".join(buf), cmap, warnings))

    return "\n".join(out), warnings, set(raw_ids)
