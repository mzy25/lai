#!/usr/bin/env python3
"""五篇书册注册表（构建管线单一事实源）。

md 路径 / 书名 / doc-id / 图前缀 / 跨篇别名 / 自检格式档案，全部在这里声明；
build_html、build_docx、check_html、lint_md 从这里取数，不再各自维护副本。

顺序即产物中的篇序（AI数学 → 基座 → 用好AI → 扩散 → AI规律）。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 自检附录 H1 标题（md 结构约定；build_docx 的翻页拆分标记同源）
SELFCHECK_HEADING = '# 附录：自检问题与答案'


@dataclass(frozen=True)
class Book:
    key: str            # 目录名
    markdown: str       # md 文件名
    title: str          # 显示书名（完整标题）
    doc_id: str         # HTML section id 前缀
    label: str          # 文档切换按钮的简称
    fig_prefix: str     # html/figures/ 中的图片前缀
    alias: str          # 跨篇引用简称（《AI数学》等）
    selfcheck_profile: str = 'auto'   # 自检附录格式：auto | canonical | legacy-bundle | legacy-law

    @property
    def md_rel(self) -> str:
        return f'{self.key}/{self.markdown}'

    @property
    def md_path(self) -> Path:
        return ROOT / self.md_rel

    @property
    def fig_dir(self) -> Path:
        return ROOT / self.key / 'figures'

    @property
    def docx_path(self) -> Path:
        return ROOT / 'docs' / f'{Path(self.markdown).stem}.docx'

    @property
    def raw_docx_name(self) -> str:
        return f'{Path(self.markdown).stem}_raw.docx'


BOOKS: list[Book] = [
    Book('1_ai_math', 'AI数学_从起步到前沿.md', 'AI数学：从起步到前沿', 'doc-1',
         'AI数学', 'aimath', 'AI数学'),
    Book('2_foundation', '基座模型_从咿呀到行动.md', '基座模型：从咿呀到行动', 'doc-2',
         '基座', 'base', '基座模型'),
    Book('3_use_ai', '用好AI_从有用到驾驭.md', '用好AI：从有用到驾驭', 'doc-3',
         '用好AI', 'use', '用好AI'),
    Book('1a_diffusion', '扩散_从噪声到生成.md', '扩散：从噪声到生成', 'doc-4',
         '扩散', 'diff', '扩散'),
    Book('4_ai_law', 'AI规律_从现象到预见.md', 'AI规律：从现象到预见', 'doc-5',
         'AI规律', 'ailaw', 'AI规律'),
]

BY_DOC_ID = {b.doc_id: b for b in BOOKS}
BY_ALIAS = {b.alias: b for b in BOOKS}
BY_KEY = {b.key: b for b in BOOKS}
