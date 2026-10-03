#!/usr/bin/env python3
"""HTML 产物校验（可入库版本，构建后自动运行）。

检查项：
1. id 唯一；内部锚点 href 全部可达
2. 图片文件存在（html/figures/）
3. 引用标记未退化为脚注（footnote-ref / footnotes 区 / 游离 ^）
4. 五篇 doc-section 齐全
5. 标题完整性：md 源稿标题（去书名标题、去自检附录）必须全部出现在产物中
   （heading_check；兜住"标题被吞"的静默事故）
6. 分隔符字面残留：正文不得出现 `* * *` 文本（HR 合并事故的产物形态）
7. 跨篇引用链接数 == 源稿引用样式匹配数，且每个 xref 锚点可达

用法::

    python3 build/check_html.py [--index html/index.html]

退出码：0 全过；1 有问题。
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import heading_check as hc  # noqa: E402
import books as _books  # noqa: E402
import selfcheck as _selfcheck  # noqa: E402

# (md 相对路径, doc id) —— 从注册表派生
BOOKS = [(b.md_rel, b.doc_id) for b in _books.BOOKS]


def _doc_segment(html: str, doc_id: str) -> str:
    m = re.search(rf'<section class="doc-section" id="{doc_id}"', html)
    if not m:
        return ''
    nxt = re.search(r'<section class="doc-section" id="doc-', html[m.end():])
    return html[m.start():m.end() + nxt.start()] if nxt else html[m.start():]

_XREF_SRC_RE = re.compile(
    r'《(AI数学|扩散|基座模型|用好AI|AI规律)》\s*([§]?\s*\d{1,2}(?:\.\d{1,3})*|第\s*\d+\s*章)')


def check(index_path: Path | None = None) -> list[str]:
    index = Path(index_path) if index_path else ROOT / 'html' / 'index.html'
    if not index.exists():
        return [f'缺少 {index}（先跑 build/build_html.py）']
    html = index.read_text(encoding='utf-8')
    issues: list[str] = []

    # 1. id 唯一 + 内部锚点可达
    ids = re.findall(r'id="([^"]+)"', html)
    dupes = {k: v for k, v in Counter(ids).items() if v > 1}
    if dupes:
        issues.append(f'重复 id：{list(dupes.items())[:5]}')
    id_set = set(ids)
    hrefs = re.findall(r'href="#([^"]+)"', html)
    broken = sorted({h for h in hrefs if h not in id_set})
    if broken:
        issues.append(f'内部锚点不可达（{len(broken)}）：{broken[:8]}')

    # 2. 图片存在
    imgs = re.findall(r'<img src="(?:\./)?figures/([^"]+)"', html)
    missing_imgs = sorted({s for s in imgs if not (ROOT / 'html' / 'figures' / s).exists()})
    if missing_imgs:
        issues.append(f'图片缺失（{len(missing_imgs)}）：{missing_imgs[:5]}')

    # 3. 引用标记
    if re.search(r'class="footnote-ref"', html) or re.search(r'<section id="footnotes"', html) or re.search(r'</a>\^', html):
        issues.append('引用标记退化为脚注/游离 ^（检查 normalize_citations）')

    # 4. 五篇齐全
    for _, doc_id in BOOKS:
        if f'id="{doc_id}"' not in html:
            issues.append(f'缺少文档区段 {doc_id}')

    # 5. 标题完整性
    for md_rel, doc_id in BOOKS:
        md = ROOT / md_rel
        if md.exists():
            issues.extend(hc.check_html(md, index, doc_id))

    # 5b. 自检 popup 数 == 正文题数 + 扩展题数（selfcheck 模型）
    for md_rel, doc_id in BOOKS:
        md = ROOT / md_rel
        if not md.exists():
            continue
        text = md.read_text(encoding='utf-8')
        expected = (sum(len(r.questions) for r in _selfcheck.parse_body(text))
                    + _selfcheck.count_extra_questions(text))
        actual = _doc_segment(html, doc_id).count('class="selfcheck-popup"')
        if actual != expected:
            issues.append(f'{doc_id} 自检 popup 数 {actual} ≠ 期望 {expected}（{md_rel}）')

    # 5c. 代码块内不得出现「$ 数学 + 中文」——凡此类必是 details 缩进残渣把散文渲染成了代码
    prose_code = 0
    for m in re.finditer(r'<pre><code[^>]*>(.*?)</code></pre>', html, re.S):
        body = m.group(1)
        # 成对 $…$（行内/跨行上限 120 字）＋中文：shell `$VAR` 等合法代码不误伤
        if re.search(r'\$[^$\n]{1,120}\$', body, re.S) and re.search(r'[\u4e00-\u9fff]', body):
            prose_code += 1
    if prose_code:
        issues.append(f'代码块内出现中文+$ 散文 {prose_code} 处（details 缩进/复制事故）')

    # 6. 分隔符字面残留
    if '* * *' in html:
        issues.append('产物出现字面 `* * *`（分隔符合并事故）')

    # 7. 跨篇引用：源稿匹配数 == 产物链接数；每个 xref 锚点可达
    n_refs = 0
    for md_rel, _ in BOOKS:
        md = ROOT / md_rel
        if md.exists():
            n_refs += len(_XREF_SRC_RE.findall(md.read_text(encoding='utf-8')))
    n_xref = html.count('class="xref"')
    if n_refs != n_xref:
        issues.append(f'跨篇引用数不匹配：源稿 {n_refs} vs 产物 {n_xref}（有引用未解析成链接）')
    xref_hrefs = re.findall(r'<a class="xref" href="#([^"]+)"', html)
    dead = sorted({h for h in xref_hrefs if h not in id_set})
    if dead:
        issues.append(f'跨篇引用锚点不可达（{len(dead)}）：{dead[:5]}')

    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description='HTML 产物校验')
    ap.add_argument('--index', default=None, help='默认 html/index.html')
    args = ap.parse_args()
    issues = check(Path(args.index) if args.index else None)
    if issues:
        for i in issues:
            print('✗', i)
        print(f'check_html: {len(issues)} issue(s)')
        return 1
    print('check_html: all checks passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
