#!/usr/bin/env python3
"""md 内链修复：把 `](#anchor)` 改写为 pandoc 实际会生成的标题 id。
另含 `normalize_citations`：统一引用标记（`^[N]^` / `<sup>[N]</sup>`）为版本无关的转义上标。

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
- 两个标题 id 规范化后撞车 → 保留文档序第一个映射 + warning（章节正文
  标题总在自检附录的复述标题之前，锚点指向的必是前者，非猜测）。

用法:
    text, warnings, id_set = fix_internal_links(md_text, cwd, from_flags)
    # text: 改写后的 md；warnings: 告警列表；id_set: harvest 出的标题 id 集合
    # （HTML 管线在 bump_headings 加 doc-N- 前缀后，用它做纯精确的前缀回写）
"""
from __future__ import annotations

import html as H
import re
import subprocess
import tempfile
from pathlib import Path

# 规范化：只保留 ASCII 字母数字 + CJK（常用区 + 扩展 A），全部小写，
# 其余（标点、——、-、空格、$、_ 等）一律丢弃。
_CANON = re.compile(r'[^0-9a-z\u4e00-\u9fff\u3400-\u4dbf]')
_HEADING_ID = re.compile(r'<h[1-6][^>]*\bid="([^"]+)"')
# 标题文字：id 之外的第二把钥匙。pandoc 把 `{#sec-…}`／`{#ch-N}` 放进 id 属性后，
# 源稿里手写的文本型锚点（如 `#第1章后训练从有用到可用`）会失去对应关系；
# 2026-09-28 五篇共 39 处篇首问题链锚点因此不可达。按标题文字兜底可让内链
# 对任意 id 方案都健壮，而不是每次改 id 规则就去改 39 处锚点。
_HEADING_BLOCK = re.compile(r'<h[1-6][^>]*\bid="([^"]+)"[^>]*>(.*?)</h[1-6]>', re.S)
_LINK = re.compile(r'\]\(#([^)\s]+)\)')
_FENCE = re.compile(r'^\s*(```|~~~)')

# pandoc reader 参数：harvest 与两条管线的真实转换共用，保证 id 一字不差。
# gfm_auto_identifiers 让标题 id 按 GitHub slug 规则生成（与源稿目录锚点同源）。
FROM_FLAGS = ("markdown+mark+gfm_auto_identifiers+tex_math_dollars"
              "+raw_tex-yaml_metadata_block")

# 引用标记两种写法：^[N]^ 与 <sup>[N]</sup>。前者在 pandoc 版本间有歧义
# （3.11 起优先按行内脚注解析，产物出现真脚注 + 跨篇重复 fn id）；后者在
# DOCX 下被剥成纯文本、丢失上标。统一转义为 ^\[N\]^：两版 pandoc、两条
# 管线都按上标渲染，且与版本无关。相邻引用（如 [81][82] 组）显式折叠成
# ^\[81\]\[82\]^ 一个上标 token，不依赖 pandoc 的隐式合并行为。
_CITATION = re.compile(r'\^\[(\d+)\]\^|<sup>\[(\d+)\]</sup>')
_MULTI_SUP = re.compile(r'<sup>((?:\[\d+\])+)</sup>')
_ADJACENT = re.compile(r'\^\\\[\d+\\\]\^(?:\^\\\[\d+\\\]\^)+')


def normalize_citations(text: str) -> str:
    """把 ^[N]^ / <sup>[N]</sup> 统一成转义形式 ^\\[N\\]^；相邻组折叠为 ^\\[81\\]\\[82\\]^。

    2026-10-02 补 <sup>[81][82]</sup> 多号形（此前漏网，产物会留字面 [82]）。"""
    def _multi(m):
        return '^' + ''.join('\\[' + n + '\\]' for n in re.findall(r'\d+', m.group(1))) + '^'
    text = _MULTI_SUP.sub(_multi, text)
    text = _CITATION.sub(lambda m: '^\\[' + (m.group(1) or m.group(2)) + '\\]^', text)
    return _ADJACENT.sub(
        lambda m: '^' + ''.join('\\[' + n + '\\]' for n in re.findall(r'\d+', m.group(0))) + '^',
        text)


def canon(s: str) -> str:
    return _CANON.sub('', s.lower())


def _pandoc_html(md_text: str, cwd: Path, from_flags: str) -> str:
    """用 pandoc（与真实转换同参数）只读转一遍 HTML 片段。"""
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
    return r.stdout


def harvest_ids(md_text: str, cwd: Path, from_flags: str) -> list[str]:
    """harvest 标题 id（文档序）。"""
    return _HEADING_ID.findall(_pandoc_html(md_text, cwd, from_flags))


def harvest_id_text(md_text: str, cwd: Path, from_flags: str) -> list[tuple[str, str]]:
    """harvest 标题的 (id, 文字) 对（文档序），供 fix_internal_links 建兜底映射。"""
    out = []
    for hid, inner in _HEADING_BLOCK.findall(_pandoc_html(md_text, cwd, from_flags)):
        text = H.unescape(re.sub(r'<[^>]+>', '', inner)).strip()
        out.append((hid, text))
    return out


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
    pairs = harvest_id_text(md_text, cwd, from_flags)

    # canon → id 映射；撞车时保留文档序第一个 id（章节正文标题总在自检附录的
    # 复述标题之前，锚点指向的必是前者），仍告警以便发现异常重复标题。
    # 键有两把：id 自身（显式 `{#…}` 或 auto id）与标题文字（id 变了也能解析）。
    cmap: dict[str, str] = {}
    seen: set[str] = set()      # 任何键占位（先到先得）
    seen_id: set[str] = set()   # id 键专属：只有两个 id 撞车才值得告警
    for rid, text in pairs:
        ck = canon(rid)
        keys = [ck] if canon(text) == ck else [ck, canon(text)]
        for c in keys:
            if not c:
                continue
            if c in seen:
                # 标题文字天然重复（每章都有「常见误解」、附录复述章标题），
                # 撞了就取首个（文档序靠前者是正文标题，锚点指向的必是它）。
                # 只有 id 键互撞才是真问题——那意味着两个标题的 id 规范化后相同。
                if c == ck and c in seen_id:
                    warnings.append(f"标题 id 规范化撞车，保留首个映射：{rid}")
                continue
            seen.add(c)
            if c == ck:
                seen_id.add(c)
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

    return "\n".join(out), warnings, {rid for rid, _ in pairs}
