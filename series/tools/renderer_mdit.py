#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""renderer_mdit：markdown-it-py 渲染层（站点 HTML 形状契约，与 pandoc 对齐）。

M2 起用于双引擎对拍；M3 起成为站点唯一 md→HTML 引擎。

契约（2026-11-27 M1/M2 固化）：
- CommonMark ＋ GFM 管道表；raw HTML 直通；无脚注/任务列表/引用式链接。
- 上下标在输入层已是 `<sub>/<sup>`（sub_sup_convert 直出），本层不处理。
- 标题 id 由 build_site 后处理赋（assign_heading_ids），本层不产 id。
- 代码块不做语法高亮；语言标注只作 `<pre>` 的 class（同 pandoc --no-highlight）。
- 正文只转义 `& < >`（引号原样）；软换行输出一个空格（同 pandoc）。
- 表格复刻 pandoc 判定：max(分隔段总长, 各行单元格显示宽之和) + 列数 + 1 > 72
  才发 colgroup，列宽比例＝分隔段长度占比（百分比向下取整）；列宽比例之和为
  浮点 <1 时给 table 加 style="width:N%;"（与 pandoc 的 IEEE 求和一致）。

用法：
    python3 series/tools/renderer_mdit.py --selftest
"""
from __future__ import annotations

import argparse
import sys
import unicodedata

from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml

COLUMNS = 72


def _escape_code(s: str) -> str:
    """代码内容转义，逐字符对齐 pandoc（含单引号）。"""
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&#39;"))


def _real_len(s: str) -> int:
    """显示宽度：东亚宽字符 2，组合/格式字符 0，其余 1（同 pandoc realLength）。"""
    n = 0
    for c in s:
        if unicodedata.category(c) in ("Mn", "Me", "Cf"):
            continue
        n += 2 if unicodedata.east_asian_width(c) in ("W", "F") else 1
    return n


def _strip_outer_pipes(s: str) -> str:
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        # 末尾竖线前若为奇数个反斜杠，则它是转义字符而非分隔符
        k = 0
        j = len(s) - 2
        while j >= 0 and s[j] == "\\":
            k += 1
            j -= 1
        if k % 2 == 0:
            s = s[:-1]
    return s


def _split_row(line: str) -> list[str]:
    r"""按未转义竖线切分（`\|` 属单元格内容，与 GFM/表格解析一致）。"""
    s = _strip_outer_pipes(line.strip())
    cells: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            buf.append(c)
            buf.append(s[i + 1])
            i += 2
            continue
        if c == "|":
            cells.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    cells.append("".join(buf))
    return cells


def _table_metrics(src_lines: list[str], token) -> list[float] | None:
    """复刻 pandoc 管道表宽度判定：返回列宽比例（无 colgroup 时 None）。"""
    if not token.map:
        return None
    start, end = token.map
    block = src_lines[start:end]
    if len(block) < 2:
        return None
    seplens: list[int] = []
    for cell in _split_row(block[1]):
        cell = cell.strip()
        dashes = cell.count("-")
        if dashes == 0:
            return None
        seplens.append(dashes + (1 if cell.startswith(":") else 0)
                       + (1 if cell.endswith(":") else 0))
    n = len(seplens)
    total_sep = sum(seplens)
    row_widths = []
    for ln in block:
        cells = _split_row(ln)
        # 单元格按原始片段计量（含两侧空格；pandoc 对未 trim 的 cell 取 realLength）
        row_widths.append(sum(_real_len(c) for c in cells[:n]))
    if max([total_sep] + row_widths) + (n + 1) <= COLUMNS:
        return None
    return [l / total_sep for l in seplens]


def _cell_open(tag: str):
    def rule(self, tokens, idx, options, env):
        style = tokens[idx].attrGet("style")
        if style:
            return f'<{tag} style="{style.replace("text-align:", "text-align: ")};">'
        return f"<{tag}>"
    return rule


def _table_open(self, tokens, idx, options, env):
    out = ["<table>\n"]
    fracs = _table_metrics(env.get("_src_lines", []), tokens[idx])
    if fracs:
        out.append("<colgroup>\n")
        out.extend(f'<col style="width: {int(f * 100)}%" />\n' for f in fracs)
        out.append("</colgroup>\n")
    env["_tbl_head"] = False
    env["_tbl_row"] = 0
    return "".join(out)


def _thead_open(self, tokens, idx, options, env):
    env["_tbl_head"] = True
    return "<thead>\n"


def _tbody_open(self, tokens, idx, options, env):
    env["_tbl_head"] = False
    env["_tbl_row"] = 0
    return "<tbody>\n"


def _tr_open(self, tokens, idx, options, env):
    if env.get("_tbl_head"):
        return '<tr class="header">\n'
    n = env.get("_tbl_row", 0)
    env["_tbl_row"] = n + 1
    return f'<tr class="{"odd" if n % 2 == 0 else "even"}">\n'


def _fence(self, tokens, idx, options, env):
    tok = tokens[idx]
    info = tok.info.strip().split()[0] if tok.info.strip() else ""
    content = tok.content[:-1] if tok.content.endswith("\n") else tok.content
    cls = f' class="{escapeHtml(info)}"' if info else ""
    return f"<pre{cls}><code>{_escape_code(content)}</code></pre>\n"


def _code_block(self, tokens, idx, options, env):
    content = tokens[idx].content
    content = content[:-1] if content.endswith("\n") else content
    return f"<pre><code>{_escape_code(content)}</code></pre>\n"


def _text(self, tokens, idx, options, env):
    s = tokens[idx].content
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _code_inline(self, tokens, idx, options, env):
    s = tokens[idx].content
    esc = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"<code>{esc}</code>"


def _softbreak(self, tokens, idx, options, env):
    return " "


def _ordered_open(self, tokens, idx, options, env):
    start = tokens[idx].attrGet("start")
    attrs = f' start="{start}"' if start else ""
    return f'<ol{attrs} type="1">\n'


def make() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])
    md.add_render_rule("fence", _fence)
    md.add_render_rule("code_block", _code_block)
    md.add_render_rule("ordered_list_open", _ordered_open)
    md.add_render_rule("table_open", _table_open)
    md.add_render_rule("thead_open", _thead_open)
    md.add_render_rule("tbody_open", _tbody_open)
    md.add_render_rule("tr_open", _tr_open)
    md.add_render_rule("th_open", _cell_open("th"))
    md.add_render_rule("td_open", _cell_open("td"))
    md.add_render_rule("text", _text)
    md.add_render_rule("code_inline", _code_inline)
    md.add_render_rule("softbreak", _softbreak)
    return md


_MD = make()


def render(text: str) -> str:
    return _MD.render(text, {"_src_lines": text.splitlines()})


def selftest() -> int:
    ok = True

    def case(name: str, got: str, want: str) -> None:
        nonlocal ok
        good = got == want
        ok = ok and good
        print(("PASS " if good else "FAIL ") + name)
        if not good:
            print(f"  got : {got!r}\n  want: {want!r}")

    case("代码块：无高亮、尾换行剥离、单引号转义",
         render("```\na & b < c > d \"q\" 's'\n```\n"),
         "<pre><code>a &amp; b &lt; c &gt; d &quot;q&quot; &#39;s&#39;</code></pre>\n")
    case("代码块：语言标注作 pre class",
         render("```python\nx=1\n```\n"),
         '<pre class="python"><code>x=1</code></pre>\n')
    case("有序列表：type=1", render("1. 一\n2. 二\n"),
         '<ol type="1">\n<li>一</li>\n<li>二</li>\n</ol>\n')
    case("有序列表：start",
         render("3. 三\n"),
         '<ol start="3" type="1">\n<li>三</li>\n</ol>\n')
    case("表格：行类与对齐样式",
         render("| A | B |\n|:--|--:|\n| 1 | 2 |\n"),
         '<table>\n<thead>\n<tr class="header">\n'
         '<th style="text-align: left;">A</th>\n'
         '<th style="text-align: right;">B</th>\n'
         "</tr>\n</thead>\n<tbody>\n<tr class=\"odd\">\n"
         '<td style="text-align: left;">1</td>\n'
         '<td style="text-align: right;">2</td>\n'
         "</tr>\n</tbody>\n</table>\n")
    long_row = "| " + " | ".join(["很长的内容" * 8] * 3) + " |"
    case("表格：长行触发 colgroup（33%）",
         render(f"| 甲 | 乙 | 丙 |\n| --- | --- | --- |\n{long_row}\n"),
         '<table>\n<colgroup>\n'
         '<col style="width: 33%" />\n<col style="width: 33%" />\n<col style="width: 33%" />\n'
         "</colgroup>\n<thead>\n<tr class=\"header\">\n"
         "<th>甲</th>\n<th>乙</th>\n<th>丙</th>\n</tr>\n</thead>\n<tbody>\n<tr class=\"odd\">\n"
         + "\n".join(f"<td>{'很长的内容' * 8}</td>" for _ in range(3))
         + "\n</tr>\n</tbody>\n</table>\n")
    hdr9 = "|" + "|".join(f"c{i}" for i in range(9)) + "|"
    sep9 = "|" + "|".join(["---"] * 9) + "|"
    row9 = "|" + "|".join(["很长的内容" * 6] * 9) + "|"
    got = render(f"{hdr9}\n{sep9}\n{row9}\n")
    case("表格：多列不发内联宽度（宽度交给 CSS）",
         got.splitlines()[0], "<table>")
    print("renderer_mdit 自测：" + ("all pass" if ok else "FAILED"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true", help="内置对照自测")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    print("用法：build_site 内部调用；单独验证跑 --selftest", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
