#!/usr/bin/env python3
"""md 源稿结构 lint（构建前置闸门）。

检查项（error 会导致构建中止；warning 只报告）:

- hr-merge       独立分隔符行前一行非空（会被并入段落——§1.5 事故形态）
- heading-merge  标题行前一行非空且不是标题/分隔符（会被并入段落/列表项）
- details-code-indent  <details> 内正文行不得 4 空格缩进（会渲染为代码块；
                     2026-10-02：45 处答案句曾因此在 HTML/DOCX 变成代码/等宽段）
- details-pair   <details> / </details> 数量不配对（围栏外）
- summary-pair   <summary> / </summary> 数量不配对（围栏外）
- fence-parity   围栏行（```` ``` ````/`~~~`）总数为奇数
- figure-missing md 引用的本地图片文件不存在（error）
- figure-unused  figures/ 中未被 md 引用的 PNG（warning）
- citation-form  引用标记出现白名单外的写法（warning；白名单：
                 ^[N]^ 与 <sup>[N]</sup>，参考文献区的裸 [N] 不计）

用法::

    python3 build/lint_md.py                     # 五篇全查
    python3 build/lint_md.py 1_ai_math/xx.md     # 指定文件
    python3 build/lint_md.py --selftest          # 夹具回归
"""
from __future__ import annotations

import argparse
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

import books as _books  # noqa: E402
import selfcheck as _selfcheck  # noqa: E402

BOOKS = [b.md_rel for b in _books.BOOKS]

HR_RE = re.compile(r'^\s*(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})\s*$')
HEADING_RE = re.compile(r'^#{1,6}\s')
BLOCK_MARK_RE = re.compile(r'^(?:\*\*【[^】]+】\*\*|\*\*本章自检\*\*)\s*[:：]?\s*$')
FENCE_RE = re.compile(r'^\s*(```|~~~)')
IMG_RE = re.compile(r'!\[[^\]]*\]\(\s*([^)\s]+)')
CORNER_CITE_RE = re.compile(r'【\d+】')
CARET_OPEN_RE = re.compile(r'\^\[\d+\](?!\^)')


@dataclass
class Finding:
    file: str
    line: int
    code: str
    severity: str  # error | warning
    message: str

    def render(self) -> str:
        mark = '✗' if self.severity == 'error' else '⚠'
        return f'{mark} {self.file}:{self.line} [{self.code}] {self.message}'


def _split_fence_state(lines):
    """yield (line, in_fence)——围栏行本身算 in_fence 之外（分隔符行语义）。"""
    in_fence = False
    for line in lines:
        if FENCE_RE.match(line):
            yield line, False
            in_fence = not in_fence
        else:
            yield line, in_fence


def lint_text(text: str, file: str = '<text>') -> list[Finding]:
    lines = text.split('\n')
    out: list[Finding] = []
    fence_lines = 0

    prev = None
    in_details = False
    for i, (line, in_fence) in enumerate(_split_fence_state(lines), start=1):
        if FENCE_RE.match(line):
            fence_lines += 1
            prev = ''  # 围栏是块边界：其后的标题/分隔符无须再补空行
            continue
        if in_fence:
            prev = line
            continue
        if '<details' in line:
            in_details = True
        elif '</details>' in line:
            in_details = False
        elif in_details and re.match(r'^ {4,}\S', line):
            out.append(Finding(file, i, 'details-code-indent', 'error',
                               'details 内正文行 4 空格缩进，会渲染为代码块（代码请用围栏）'))
        if HR_RE.match(line) and prev is not None and prev.strip():
            out.append(Finding(file, i, 'hr-merge', 'error',
                               '分隔符行前缺空行，会被并入上一段'))
        if (HEADING_RE.match(line) and prev is not None and prev.strip()
                and not HR_RE.match(prev) and not HEADING_RE.match(prev)):
            out.append(Finding(file, i, 'heading-merge', 'error',
                               '标题行前缺空行，会被并入上一段/列表项'))
        if (BLOCK_MARK_RE.match(line) and prev is not None and prev.strip()):
            out.append(Finding(file, i, 'block-merge', 'error',
                               '组标签/自检区标题前缺空行，会被并入上一段'))
        prev = line

    # details / summary 配对（围栏外）
    outside = '\n'.join(l for l, f in _split_fence_state(lines) if not f)
    for open_tag, close_tag, code in [('<details', '</details>', 'details-pair'),
                                      ('<summary', '</summary>', 'summary-pair')]:
        n_open = outside.count(open_tag)
        n_close = outside.count(close_tag)
        if n_open != n_close:
            out.append(Finding(file, 0, code, 'error',
                               f'{open_tag}={n_open} 与 {close_tag}={n_close} 不配对'))

    if fence_lines % 2:
        out.append(Finding(file, 0, 'fence-parity', 'error',
                           f'围栏行总数为奇数（{fence_lines}），存在未闭合代码块'))

    # 引用标记白名单
    for m in CORNER_CITE_RE.finditer(outside):
        line_no = outside[:m.start()].count('\n') + 1
        out.append(Finding(file, line_no, 'citation-form', 'warning',
                           f'出现非规范引用写法 {m.group(0)}（应为 ^[N]^）'))
    for m in CARET_OPEN_RE.finditer(outside):
        line_no = outside[:m.start()].count('\n') + 1
        out.append(Finding(file, line_no, 'citation-form', 'warning',
                           f'上标引用缺少结尾 ^：{m.group(0)}'))
    return out


def lint_file(path: Path) -> list[Finding]:
    text = path.read_text(encoding='utf-8')
    findings = lint_text(text, str(path))

    # 自检区结构守恒（正文题 ↔ 附录答案；详见 build/selfcheck.py）
    for issue in _selfcheck.validate(text):
        findings.append(Finding(str(path), 0, issue.code, issue.severity, issue.message))

    # 图片引用存在性 + 未用图（warning）
    refs = [m.group(1).strip('<>') for m in IMG_RE.finditer(text)]
    local = [r for r in refs if not r.startswith(('http://', 'https://'))]
    for ref in local:
        cand = path.parent / ref
        if not cand.exists() and not (path.parent / 'figures' / ref).exists():
            findings.append(Finding(str(path), 0, 'figure-missing', 'error',
                                    f'引用的图片不存在：{ref}'))
    fig_dir = path.parent / 'figures'
    if fig_dir.is_dir():
        used = {Path(r).name for r in local}
        for png in sorted(fig_dir.glob('*.png')):
            if png.name not in used:
                findings.append(Finding(str(path), 0, 'figure-unused', 'warning',
                                        f'figures/ 中未被引用：{png.name}'))
    return findings


def lint_paths(paths) -> list[Finding]:
    out: list[Finding] = []
    for p in paths:
        fp = Path(p)
        if not fp.is_absolute():
            fp = ROOT / fp
        if not fp.exists():
            out.append(Finding(str(p), 0, 'file-missing', 'error', '文件不存在'))
            continue
        out.extend(lint_file(fp))
    return out


def report(findings: list[Finding], *, max_warn: int = 12) -> int:
    errors = [f for f in findings if f.severity == 'error']
    warnings = [f for f in findings if f.severity != 'error']
    for f in errors:
        print(f.render())
    for f in warnings[:max_warn]:
        print(f.render())
    if len(warnings) > max_warn:
        by_code: dict[str, int] = {}
        for f in warnings[max_warn:]:
            by_code[f.code] = by_code.get(f.code, 0) + 1
        tail = ', '.join(f'{k}×{v}' for k, v in sorted(by_code.items()))
        print(f'⚠ …另有 {len(warnings) - max_warn} 条 warning 未展开（{tail}）')
    print(f'lint_md: errors={len(errors)} warnings={len(warnings)}')
    return 1 if errors else 0


# ---------------------------------------------------------------- selftest

def _selftest() -> int:
    ok = True

    def expect(name, text, codes, *, file='<selftest>'):
        nonlocal ok
        got = {f.code for f in lint_text(text, file)}
        passed = got == set(codes)
        print(('PASS ' if passed else 'FAIL ') + name)
        if not passed:
            ok = False
            print('  got :', sorted(got))
            print('  want:', sorted(codes))

    expect('hr-merge fires', '正文\n * * *\n', ['hr-merge'])
    expect('heading-merge fires', '正文\n## 标题\n', ['heading-merge'])
    expect('block-merge fires', '题？\n**【生成】**\n', ['block-merge'])
    expect('heading after hr is ok', '正文\n\n***\n## 标题\n', [])
    expect('clean sample silent', '正文\n\n***\n\n## 标题\n\n- a\n- b\n', [])
    expect('details unbalanced', '<details>\n<summary>x\n', ['details-pair', 'summary-pair'])
    expect('details code indent fires', '<details>\n\n    缩进答案句。\n</details>\n',
           ['details-code-indent'])
    expect('details indent in fence ok',
           '<details>\n\n```\n    code\n```\n\n</details>\n', [])
    expect('fence odd', '```\ncode\n', ['fence-parity'])
    expect('corner citation', '正文【3】结束。\n', ['citation-form'])
    expect('caret unclosed', '正文 ^[3] 结束。\n', ['citation-form'])
    expect('caret ok', '正文 ^[3]^ 结束。\n', [])
    expect('fence hides hr', '```\n * * *\n```\n', [])

    # 文件级：figure-missing / figure-unused
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / 'figures').mkdir()
        (d / 'figures' / 'a.png').write_bytes(b'\x89PNG\r\n\x1a\n')
        (d / 'figures' / 'orphan.png').write_bytes(b'\x89PNG\r\n\x1a\n')
        md = d / 'book.md'
        md.write_text('![x](figures/a.png)\n\n![y](figures/missing.png)\n', encoding='utf-8')
        got = lint_file(md)
        codes = [f.code for f in got]
        passed = ('figure-missing' in codes and 'figure-unused' in codes)
        print(('PASS ' if passed else 'FAIL ') + 'figure rules')
        if not passed:
            ok = False
            print('  got:', [f.render() for f in got])

    print('lint_md selftest:', 'all pass' if ok else 'FAILED')
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='md 结构 lint')
    ap.add_argument('files', nargs='*', default=None,
                    help='默认五篇；相对路径按仓库根解析')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    paths = args.files if args.files else BOOKS
    return report(lint_paths(paths))


if __name__ == '__main__':
    raise SystemExit(main())
