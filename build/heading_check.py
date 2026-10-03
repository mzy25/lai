#!/usr/bin/env python3
"""标题完整性核对：md 源稿 ↔ 构建产物（HTML / DOCX）。

用途：兜住"标题被 pandoc 吞掉"一类静默事故（2026-09 §1.5 事故：
段落与标题间缺空行，标题并入段落，构建无告警）。

对齐口径（两侧都丢掉数学内容后比对）：
- md 侧：去围栏 → 去自检附录段（可选）→ 解析 `# 标题`（含引用块 `> ### 标题`）
  → 剥数学定界符（$...$ / \\(...\\) / \\[...\\]）→ 规范化（去标签/命令/标点，
  仅留 CJK+字母数字，小写）。
- HTML 侧：取 `h2-h6` 的 inner HTML，**整体删除** `<span class="math ...">…</span>`
  后剥标签 → 同一规范化。
- DOCX 侧：取 Heading 段落的 w:t 文本（OMML 数学天然不在 w:t 里）→ 同一规范化。

比较结果是多重集：missing（源稿有、产物缺）= 事故；extra（产物多出）
一般来自管线的有意增删（如 扩展题 保留、E. 自检答案），调用方按 warning 处理。
"""
from __future__ import annotations

import html as H
import re
import zipfile
from collections import Counter
from pathlib import Path

SELFCHECK_START = '# 附录：自检问题与答案'

_FENCE_RE = re.compile(r'^\s*(```|~~~)')
_MD_HEAD_RE = re.compile(r'^(?:\s*>\s*)*#{1,6}\s+(.*)$')
_MATH_DELIMS = [
    re.compile(r'\$\$.*?\$\$', re.S),
    re.compile(r'\$[^$\n]*\$'),
    re.compile(r'\\\[.*?\\\]', re.S),
    re.compile(r'\\\(.*?\\\)', re.S),
]
_MATH_SPAN_RE = re.compile(r'<span class="math [^"]*">.*?</span>', re.S)
_HTML_HEAD_RE = re.compile(r'<h([2-6])\b([^>]*)>(.*?)</h\1>', re.S)
_DOCX_PARA_RE = re.compile(r'<w:p\b.*?</w:p>', re.S)
_DOCX_HEADING_STYLE_RE = re.compile(r'<w:pStyle w:val="Heading\d?"')


# 标题行尾的稳定 ID 属性（编号方案三件套）
ID_ATTR_TAIL_RE = re.compile(r'\s*\{#[^}\s]+\}\s*$')


def canon(text: str) -> str:
    """标题规范化：去数学、去标签/命令/标点，仅留 CJK+字母数字，小写。"""
    s = H.unescape(text)
    s = re.sub(r'<[^>]+>', '', s)
    for rx in _MATH_DELIMS:
        s = rx.sub('', s)
    s = re.sub(r'\\[a-zA-Z]+', '', s)
    s = re.sub(r'[*_`~]', '', s)
    s = re.sub(r'[^0-9A-Za-z\u4e00-\u9fff]', '', s)
    return s.lower()


def _strip_fences(text: str) -> str:
    """围栏行保留为空行，围栏内内容替换为空行。"""
    out = []
    in_f = False
    for line in text.split('\n'):
        if _FENCE_RE.match(line):
            in_f = not in_f
            out.append('')
            continue
        out.append('' if in_f else line)
    return '\n'.join(out)


def _cut_selfcheck_appendix(text: str) -> str:
    """删除 `# 附录：自检问题与答案` 到下一个 H1（或 EOF）的区段（围栏感知）。"""
    lines = text.split('\n')
    out = []
    inside = False
    in_fence = False
    for line in lines:
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        if not in_fence:
            if line.strip() == SELFCHECK_START:
                inside = True
                continue
            if inside and re.match(r'^#\s', line):
                inside = False
        if not inside:
            out.append(line)
    return '\n'.join(out)


def md_headings(path: Path, *, drop_selfcheck: bool = True) -> list[str]:
    """源稿标题列表（文档序）。第一条 H1（书名标题）保留，由调用方决定是否去除。"""
    text = Path(path).read_text(encoding='utf-8')
    if drop_selfcheck:
        text = _cut_selfcheck_appendix(text)
    text = _strip_fences(text)
    out = []
    for line in text.split('\n'):
        m = _MD_HEAD_RE.match(line)
        if m:
            out.append(ID_ATTR_TAIL_RE.sub('', m.group(1)).strip())
    return out


def expected_html(md_path: Path) -> list[str]:
    """HTML 产物应有的标题：去书名标题、去自检附录（其内容转为交互弹窗）。"""
    hs = md_headings(md_path, drop_selfcheck=True)
    return hs[1:] if hs else []


def expected_docx(md_path: Path) -> list[str]:
    """DOCX 应有标题：含书名标题与自检附录题群标题。"""
    return md_headings(md_path, drop_selfcheck=False)


def html_headings(index_path: Path, doc_id: str) -> list[str]:
    """HTML 中该篇的 h2-h6 标题（inner HTML 去数学 span 后剥标签）。"""
    html = Path(index_path).read_text(encoding='utf-8')
    out = []
    for m in _HTML_HEAD_RE.finditer(html):
        attrs, inner = m.group(2), m.group(3)
        idm = re.search(r'id="([^"]*)"', attrs)
        if not idm or not idm.group(1).startswith(doc_id + '-'):
            continue
        inner = _MATH_SPAN_RE.sub('', inner)
        out.append(H.unescape(re.sub(r'<[^>]+>', '', inner)).strip())
    return out


def docx_headings(path: Path) -> list[str]:
    """DOCX 里 Heading 段落的纯文本（OMML 数学不在 w:t 中，天然被忽略）。"""
    with zipfile.ZipFile(path) as z:
        xml = z.read('word/document.xml').decode('utf-8', 'ignore')
    out = []
    for m in _DOCX_PARA_RE.finditer(xml):
        para = m.group(0)
        if not _DOCX_HEADING_STYLE_RE.search(para):
            continue
        text = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', para))
        if text.strip():
            out.append(text.strip())
    return out


def compare(expected: list[str], actual: list[str]) -> tuple[Counter, Counter]:
    """返回 (missing, extra) 两个 Counter（键为规范化标题）。"""
    ce = Counter(canon(x) for x in expected if canon(x))
    ca = Counter(canon(x) for x in actual if canon(x))
    return ce - ca, ca - ce


EXTRA_OK = re.compile(r'自检答案')  # 产物件：答案区标题（style_docx 页隔标题），唯一白名单


def check_html(md_path: Path, index_path: Path, doc_id: str) -> list[str]:
    missing, extra = compare(expected_html(md_path), html_headings(index_path, doc_id))
    extra = [k for k in extra if not EXTRA_OK.search(k)]
    return ([f'HTML 缺标题（{md_path}）：{k[:60]}' for k in missing]
            + [f'HTML 多出标题（{md_path}）：{k[:60]}' for k in extra])


def check_docx(md_path: Path, docx_path: Path) -> list[str]:
    expected = expected_docx(md_path)
    actual = [h for h in docx_headings(docx_path) if canon(h) != canon('E. 自检答案')]
    missing, extra = compare(expected, actual)
    extra = [k for k in extra if not EXTRA_OK.search(k)]
    return ([f'DOCX 缺标题（{md_path}）：{k[:60]}' for k in missing]
            + [f'DOCX 多出标题（{md_path}）：{k[:60]}' for k in extra])
