#!/usr/bin/env python3
"""md 预处理：块分隔空行保证 + 分隔符规范化（HTML/DOCX 两条管线共用）。

只做结构安全，不改内容：

1. ``normalize_separators``：独立分隔符行（--- / *** / * * * / ___）统一为
   ``***``。消除两类歧义：段落后 ``---`` 被解析成 setext H2；成对 ``---``
   之间夹冒号行被当作 YAML 元数据块。
2. ``ensure_block_separation``：分隔符行/标题行前缺空行时补一个空行。
   段落后直接跟分隔符或 ``# 标题`` 都会被 pandoc 并入段落（2026-09 §1.5
   标题事故的成因）；本函数是构建端安全网，源码仍须由 lint_md 保持干净。
3. ``prepare`` = 按序组合，幂等；围栏代码块内容不动。

用法::

    from mdprep import prepare
    text = prepare(text)

自检::

    python3 build/mdprep.py --selftest
"""
from __future__ import annotations

import re
import sys

# 独立分隔符行：*** / * * * / --- / - - - / ___ / _ _ _（允许行首尾空白）
_HR_RE = re.compile(r'^\s*(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})\s*$')
_HEADING_RE = re.compile(r'^#{1,6}\s')
# 块标记（自检区标题/组标签）：紧贴上一段会被 pandoc 并入段落，必须空行隔离
_BLOCK_MARK_RE = re.compile(r'^(?:\*\*【[^】]+】\*\*|\*\*本章自检\*\*)\s*[:：]?\s*$')
_FENCE_RE = re.compile(r'^\s*(```|~~~)')
# 列表项 / 缩进续行：这些上下文前不加空行（会改变 tight/loose 列表语义）
_LIST_CTX_RE = re.compile(r'^(\s{2,}|[-*+]\s|\d+[.、)]\s)')


def _map_outside_fences(text: str, fn) -> str:
    """对围栏外的行应用 fn(line, state)，围栏行与围栏内行原样保留。"""
    out: list[str] = []
    in_fence = False
    for line in text.split('\n'):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        out.append(line if in_fence else fn(line))
    return '\n'.join(out)


def normalize_separators(text: str) -> str:
    """独立分隔符行统一为 ``***``（围栏代码块内不动）。"""
    return _map_outside_fences(
        text, lambda line: '***' if _HR_RE.match(line) else line)


def ensure_block_separation(text: str) -> str:
    """分隔符行/标题行前缺空行时补空行（围栏内不动，列表上下文保守跳过）。

    幂等：只检查写入结果的前一行，已分块的行不会重复插入。
    """
    out: list[str] = []
    in_fence = False
    for line in text.split('\n'):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        if not in_fence:
            prev = out[-1] if out else ''
            if prev.strip():
                if _HR_RE.match(line):
                    out.append('')
                elif _BLOCK_MARK_RE.match(line):
                    out.append('')
                elif (_HEADING_RE.match(line)
                      and not _HR_RE.match(prev)
                      and not _HEADING_RE.match(prev)
                      and not _LIST_CTX_RE.match(prev)):
                    out.append('')
        out.append(line)
    return '\n'.join(out)


def strip_nonheading_ids(text: str) -> str:
    """剥掉**非标题行**的行尾稳定 ID（`{#sec-…}`/`{#ch-…}`/`{#q-…}`）。

    标题行尾的 ID 由 pandoc 解析为锚点属性（不可见，必须保留）；列表行/段落的
    行尾 ID 会被 pandoc 当字面文本渲染（题目 `{#q-…}` 曾漏进 HTML/DOCX 各
    294/573 处，2026-09-29 I2）。两条构建管线（HTML/DOCX）共用本函数；
    卡片侧由 selfcheck 解析时剥离。"""
    out = []
    for line in text.split("\n"):
        if re.match(r"^#{1,6}\s", line):
            out.append(line)
        else:
            out.append(re.sub(r"\s*\{#[^}\s]+\}\s*$", "", line))
    return "\n".join(out)


def prepare(text: str) -> str:
    """构建端标准预处理：分隔符统一 + 块分隔空行保证（幂等）。"""
    return ensure_block_separation(normalize_separators(text))


# ---------------------------------------------------------------- selftest

def _selftest() -> int:
    cases = []

    def case(name, got, want):
        cases.append((name, got == want, got, want))

    # 1. 段落后分隔符：补空行（§1.5 事故形态）
    src = '正文。\n * * *\n## 1.5 标题\n'
    want = '正文。\n\n***\n## 1.5 标题\n'
    case('hr-after-paragraph', prepare(src), want)

    # 2. 段落后标题：补空行
    case('heading-after-paragraph', prepare('正文\n## 标题\n'), '正文\n\n## 标题\n')

    # 3. 分隔符后标题：不再插空行（pandoc 可正确分块）
    case('heading-after-hr', prepare('正文\n\n***\n## 标题\n'), '正文\n\n***\n## 标题\n')

    # 4. 行尾带空格的 * * * 统一
    case('hr-trailing-space', prepare('正文\n\n * * * \n'), '正文\n\n***\n')

    # 5. 围栏内原文保留
    src = '正文\n```\n * * *\n---\n```\n * * *\n'
    want = '正文\n```\n * * *\n---\n```\n\n***\n'
    case('fence-protected', prepare(src), want)

    # 6. 列表上下文前不插空行
    src = '- 条目一\n## 这是列表续行内容\n'
    case('list-context-skip', prepare(src), '- 条目一\n## 这是列表续行内容\n')

    # 7. 幂等：二跑结果不变
    once = prepare('正文\n * * *\n## h\n\nx\n---\n\ny\n')
    case('idempotent', prepare(once), once)

    # 8. 表格分隔行不受影响
    case('table-sep', prepare('| a | b |\n|---|---|\n| 1 | 2 |\n'),
         '| a | b |\n|---|---|\n| 1 | 2 |\n')

    # 9. 组标签紧贴上一题：补空行
    case('group-label-merge', prepare('1. 题目？\n**【生成】**\n\n2. 下一题？\n'),
         '1. 题目？\n\n**【生成】**\n\n2. 下一题？\n')

    # 10. 本章自检标记紧贴上一段：补空行
    case('selfcheck-marker-merge', prepare('正文。\n**本章自检**：\n\n1. 题？\n'),
         '正文。\n\n**本章自检**：\n\n1. 题？\n')

    ok = True
    for name, passed, got, want in cases:
        print(('PASS ' if passed else 'FAIL ') + name)
        if not passed:
            ok = False
            print('  got :', repr(got))
            print('  want:', repr(want))
    print('mdprep selftest:', 'all pass' if ok else 'FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        raise SystemExit(_selftest())
    print(__doc__)
