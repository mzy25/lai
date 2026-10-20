#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""md 表结构检查器（系列仓，纯 stdlib）。

用法：
    python3 series/tools/table_check.py [文件...]   # 缺省扫描 series/*.md
    python3 series/tools/table_check.py --selftest  # 内置坏样/好样对照

检查（只定位不判罚；有问题退出码 1，全绿 0）：
    ① 管道表块缺分隔行（| --- | 行）；
    ② 行格数与分隔行不一致（常见成因：单元格内未转义 |）；
    ③ 孤立表格行（单独一行且首尾都是 |，多半是被插语劈开的表）。
跳过 ``` 围栏代码块；`\\|` 视为转义不参与切格。
"""
import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def cells(s: str):
    s = s.strip()
    if s.startswith('|'):
        s = s[1:]
    if s.endswith('|') and not s.endswith('\\|'):
        s = s[:-1]
    return [p.strip() for p in re.split(r'(?<!\\)\|', s)]


def is_sep(line: str) -> bool:
    body = line.strip()
    if not body.startswith('|'):
        return False
    parts = cells(body)
    return len(parts) >= 1 and all(re.fullmatch(r':?-{2,}:?', p) for p in parts if p != '')


def check_text(text: str, name: str):
    issues = []
    lines = text.splitlines()
    in_fence = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith('```'):
            in_fence = not in_fence
            i += 1
            continue
        if in_fence:
            i += 1
            continue
        s = line.strip()
        if s.startswith('|') and s.count('|') >= 2:
            j = i
            block = []
            while j < len(lines) and lines[j].strip().startswith('|'):
                block.append(j)
                j += 1
            if len(block) >= 2 and is_sep(lines[block[1]]):
                ncols = len(cells(lines[block[1]]))
                for k in block:
                    c = len(cells(lines[k]))
                    if c != ncols:
                        issues.append((name, k + 1, f'格数 {c}!={ncols}（含未转义 |）', lines[k][:60]))
            elif len(block) >= 2:
                issues.append((name, block[0] + 1, '缺分隔行', lines[block[0]][:60]))
            elif s.endswith('|'):
                issues.append((name, block[0] + 1, '孤立表格行', lines[block[0]][:60]))
            i = j
        else:
            i += 1
    return issues


def selftest() -> bool:
    bad = (
        "| a | b |\n| c | d |\n\n"
        "| h | x |y| |\n| --- | --- | --- |\n| 1 | 2 | 3 |\n\n"
        "| 孤 | 行 |\n"
    )
    good = (
        "| a | b |\n| --- | --- |\n| c | d |\n\n"
        "| h | x \\|y\\| |\n| --- | --- |\n| 1 | 2 |\n"
    )
    ib = check_text(bad, 'bad')
    ig = check_text(good, 'good')
    kinds = {x[2] for x in ib}
    ok = any('缺分隔行' in k for k in kinds) and any('格数' in k for k in kinds) \
        and any('孤立表格行' in k for k in kinds) and not ig
    print('selftest:', 'PASS' if ok else f'FAIL bad={ib} good={ig}')
    return ok


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--selftest' in sys.argv:
        return 0 if selftest() else 1
    files = [pathlib.Path(a) for a in args] if args else sorted(ROOT.glob('*.md'))
    all_issues = []
    for f in files:
        if not f.exists() or not f.suffix == '.md':
            continue
        all_issues += check_text(f.read_text(encoding='utf-8'), f.name)
    for name, ln, kind, excerpt in all_issues:
        print(f'[{kind}] {name[:24]} L{ln}')
        print(f'    {excerpt}')
    print(f'table_check：{len(files)} 文件，{len(all_issues)} 处问题')
    return 1 if all_issues else 0


if __name__ == '__main__':
    sys.exit(main())
