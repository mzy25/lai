#!/usr/bin/env python3
"""Build Markdown chapters into styled DOCX reference files.

Usage:
    python3 build/build_docx.py           # build all chapters
    python3 build/build_docx.py 1a_diffusion
    python3 build/build_docx.py --verify-only
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import md_links
import mdprep
import lint_md
import heading_check
import books
import selfcheck


ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Chapter:
    key: str
    folder: str
    markdown: str
    raw_docx: str
    output_docx: str
    fallback_title: str
    # 自检答案区起点标记：正文(题目)与附录(答案)的分界。
    # 每次 build 时把该标记之后的 <details> 答案块提取到页尾，形成"题目页→答案页"的物理翻页间隔
    # （desirable difficulty：合意困难需要延迟反馈，答案不能与题目同页）。
    self_check_marker: str = ""


# Output: intermediate raw docx in chapter folder, reference docx in docs/
# 书册元数据从 build/books.py 注册表派生（单一事实源）
CHAPTERS = [
    Chapter(b.key, b.key, b.markdown, b.raw_docx_name, str(b.docx_path),
            b.title, books.SELFCHECK_HEADING)
    for b in books.BOOKS
]


def preprocess_self_check(text: str, split_marker: str) -> str:
    """Extract <details> answer blocks into a separate section with page break.

    Only <details> blocks in the self-check section (after the per-chapter
    ``split_marker``, e.g. "# 附录：自检问题与答案") are extracted to the answer
    appendix.  <details> blocks in chapter bodies are expanded inline
    (bold title + content) so they render properly in docx.
    """
    # 预处理：块分隔空行保证 + 分隔符统一（与 HTML 管线共用 mdprep）。
    # 旧版这里单独把 --- 换成 * * *；现行方案是两条管线同一函数，且构建前
    # 已由 lint_md 保证源稿干净。
    text = mdprep.prepare(text)

    # Split at self-check section: chapter body vs Q&A section
    split_pos = text.find(split_marker)

    if split_pos == -1:
        # No self-check section — just expand all <details> inline
        return _expand_details_inline(text)

    # 自检区终点 = 之后的第一个 H1（围栏感知）。自检区之后的附录（如
    # 「前沿优化器选读」）里的 details 是正文深层折叠，应内联展开，
    # 不能当作自检答案搬去页尾。
    # 「附录：扩展题」与自检同族（题在正文侧、答案延迟到页尾），并入提取区。
    section_end = len(text)
    in_fence = False
    for off, line in markdown_scanner_offsets(text, split_pos + len(split_marker)):
        if re.match(r'^\s*(```|~~~)', line):
            in_fence = not in_fence
            continue
        if not in_fence and re.match(r'^#\s', line):
            if line.strip() == '# 附录：扩展题':
                continue
            section_end = off
            break

    before = _expand_details_inline(text[:split_pos])
    qa_text = text[split_pos:section_end]
    after = _expand_details_inline(text[section_end:])

    # Extract Q&A <details> blocks into answer appendix.
    # 跳过"提示"折叠（summary 含"提示"）：提示是支架，保留在题目区；
    # 只提取"答案/解析"折叠（summary 含"答案/解析"）到页尾答案区。
    pattern = re.compile(r'<details>\s*<summary>(.*?)</summary>\s*(.*?)\s*</details>', re.DOTALL)

    answers = []
    q_num = 0

    def _extract(m: re.Match) -> str:
        nonlocal q_num
        summary = m.group(1).strip()
        if "提示" in summary:
            return m.group(0)  # 支架保留在题目区
        # "把知识连成网"是附录收束的连接练习（含题目与示范答案），
        # 与 HTML 管线一致保留在题目区，不编号为自检答案。
        if summary.startswith("把知识连成网"):
            return m.group(0)
        q_num += 1
        content = m.group(2).strip()
        answers.append(f"**A{q_num}**：{content}")
        return ""  # remove from questions section

    questions_only = pattern.sub(_extract, qa_text)

    if not answers:
        return before + questions_only + after

    # Build answer section with page break before it
    answer_section = (
        "\n\n\\newpage\n\n"
        "### E. 自检答案\n\n"
        "> 答题建议：先独立完成上一页的自检问题，再翻页对照答案。\n\n"
        + "\n\n".join(answers)
    )

    return before + questions_only + after + answer_section


def markdown_scanner_offsets(text: str, start: int):
    """从 start 起逐 (字符偏移, 行) 产出（供围栏感知的块边界扫描）。"""
    pos = start
    for line in text[start:].split('\n'):
        yield pos, line
        pos += len(line) + 1


def _expand_details_inline(text: str) -> str:
    """Convert <details><summary><b>Title</b></summary>body</details> to
    inline **Title** followed by body, so it renders in docx."""
    pattern = re.compile(
        r'<details>\s*<summary>(.*?)</summary>\s*(.*?)\s*</details>',
        re.DOTALL,
    )

    def _replace(m: re.Match) -> str:
        summary = m.group(1).strip()
        body = m.group(2).strip()
        # Strip <b> tags if present (pandoc handles **bold** natively)
        summary = re.sub(r'</?b>', '**', summary)
        return f"\n\n{summary}\n\n{body}\n"

    return pattern.sub(_replace, text)


def run(cmd: list[str], cwd: Path) -> None:
    print("$", " ".join(cmd), f"(cwd={cwd.relative_to(ROOT)})")
    subprocess.run(cmd, cwd=cwd, check=True)


def build_chapter(chapter: Chapter) -> None:
    # Ensure output docx directory exists
    Path(chapter.output_docx).parent.mkdir(exist_ok=True)
    cwd = ROOT / chapter.folder
    md_path = cwd / chapter.markdown
    md_text = md_path.read_text(encoding="utf-8")

    # Preprocess: separate self-check questions and answers with page break
    processed = preprocess_self_check(md_text, chapter.self_check_marker)
    processed = mdprep.strip_nonheading_ids(processed)   # 题目行尾 {#q-…} 不渲染
    processed = md_links.normalize_citations(processed)
    # 内链修复：目录锚点 → pandoc 实际 id（与 HTML 管线共用，保证书签/链接一致）
    processed, link_warnings, _ = md_links.fix_internal_links(
        processed, cwd, md_links.FROM_FLAGS)
    for w in link_warnings:
        print(f"⚠ {chapter.folder}: {w}")

    # Write to temp file for pandoc
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".md", delete=False, dir=cwd
    ) as tmp:
        tmp.write(processed)
        tmp_path = Path(tmp.name)

    try:
        run([
            "pandoc",
            str(tmp_path.name),
            "-o",
            chapter.raw_docx,
            "--resource-path=.:figures",
            f"--from={md_links.FROM_FLAGS}",
            "--to=docx",
        ], cwd)
        run([
            sys.executable,
            str(HERE / "style_docx.py"),
            "--input",
            str(cwd / chapter.raw_docx),
            "--output",
            str(cwd / chapter.output_docx),
            "--fallback-title",
            chapter.fallback_title,
        ], ROOT)
    finally:
        tmp_path.unlink(missing_ok=True)


def verify_chapter(chapter: Chapter) -> bool:
    cwd = ROOT / chapter.folder
    md_path = cwd / chapter.markdown
    docx_path = cwd / chapter.output_docx
    if not md_path.exists():
        print(f"FAIL {chapter.key}: missing markdown {md_path}")
        return False
    if not docx_path.exists():
        print(f"FAIL {chapter.key}: missing docx {docx_path}")
        return False

    text = md_path.read_text(encoding="utf-8")
    image_refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
    missing_images = []
    for ref in image_refs:
        clean = ref.strip().strip("<>").split()[0]
        if clean.startswith(("http://", "https://")):
            continue
        if not (cwd / clean).exists() and not (cwd / "figures" / clean).exists():
            missing_images.append(clean)

    with zipfile.ZipFile(docx_path) as zf:
        names = zf.namelist()
        xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
        media_count = sum(name.startswith("word/media/") for name in names)
        drawing_count = xml.count("<w:drawing>")
        table_count = xml.count("<w:tbl>")
        math_count = xml.count("<m:oMath")
        headers = []
        for name in names:
            if name.startswith("word/header"):
                raw = zf.read(name).decode("utf-8", errors="ignore")
                plain = re.sub(r"<[^>]+>", " ", raw)
                headers.append(re.sub(r"\s+", " ", plain).strip())
        # 内链一致性：目录锚点必须落在书签里（md_links 改写失败会在此暴露）
        # pandoc 对 bookmark 和 hyperlink anchor 的归一化不一致（如 ：被剥、—— 位置不同），
        # 比较前先统一：剥 ：—— ，统一小写，去 -
        def _norm(s):
            return s.replace("：", "").replace("——", "").replace("-", "").lower()
        bookmarks = {_norm(b) for b in re.findall(r'<w:bookmarkStart[^>]*w:name="([^"]+)"', xml)}
        anchors = re.findall(r'<w:hyperlink[^>]*w:anchor="([^"]+)"', xml)
        dead_anchors = [a for a in anchors if _norm(a) not in bookmarks]

        # 散文误落代码样式：SourceCode 段含 $ 与中文（details 缩进残渣，2026-10-02）
        prose_code = 0
        for pm in re.finditer(r'<w:p\b[^>]*>.*?</w:p>', xml, re.S):
            para = pm.group(0)
            if 'w:val="SourceCode"' not in para:
                continue
            txt = re.sub(r'<[^>]+>', '', para)
            # 成对 $…$ ＋中文（shell `$VAR` 等合法代码不误伤；2026-10-02 收窄）
            if re.search(r'\$[^$\n]{1,120}\$', txt, re.S) and re.search(r'[\u4e00-\u9fff]', txt):
                prose_code += 1
        prose_code_issues = ([f'docx 代码样式段含中文+$ 散文 {prose_code} 段']
                             if prose_code else [])
        math_issues = ([f'docx 公式渲染缺失：源稿含 $…$ 但 OMML 计数为 0（math-count gate）']
                       if ('$' in text and math_count == 0) else [])

    # 标题完整性：md 标题（含书名标题与自检附录题群）必须都落在 docx Heading 里
    heading_issues = heading_check.check_docx(md_path, docx_path)

    # 答案完整性：页尾 A 段数 == 自检附录答案数 + 扩展题答案数（源自 selfcheck 模型）
    expected_answers = (
        sum(1 for ch in selfcheck.parse_appendix(text) for r in ch.records if r.answer)
        + sum(1 for r in selfcheck.extra_records(text) if r.answer))
    actual_answers = _count_docx_answers(docx_path)
    answer_issues = []
    if actual_answers != expected_answers:
        answer_issues.append(
            f'docx 答案数 {actual_answers} ≠ 期望 {expected_answers}')
    pagebreak_issues = []
    if actual_answers and 'w:pageBreakBefore' not in xml:
        pagebreak_issues.append('docx 答案区缺分页（pageBreakBefore）——翻页隔离失效')

    ok = (not missing_images and media_count >= len(image_refs)
          and not dead_anchors and not heading_issues and not answer_issues
          and not prose_code_issues and not math_issues and not pagebreak_issues)
    status = "OK" if ok else "FAIL"
    print(
        f"{status} {chapter.key}: images={media_count}/{len(image_refs)} "
        f"drawings={drawing_count} tables={table_count} math={math_count} "
        f"links={len(anchors)}/{len(anchors) - len(dead_anchors)} "
        f"answers={actual_answers}/{expected_answers} headers={headers}"
    )
    if missing_images:
        print(f"  missing images: {missing_images}")
    if dead_anchors:
        print(f"  dead anchors: {dead_anchors}")
    for issue in heading_issues + answer_issues + prose_code_issues + math_issues + pagebreak_issues:
        print(f"  {issue}")
    return ok


def _count_docx_answers(docx_path: Path) -> int:
    """统计页尾答案段（段首 'A<数字>：'）数量。"""
    with zipfile.ZipFile(docx_path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
    n = 0
    for m in re.finditer(r'<w:p\b.*?</w:p>', xml, re.S):
        txt = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', m.group(0)))
        if re.match(r'^A\d+[：:]', txt):
            n += 1
    return n


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and verify styled DOCX outputs.")
    parser.add_argument("chapters", nargs="*", help="Chapter keys to build: " + ", ".join(c.key for c in CHAPTERS))
    parser.add_argument("--verify-only", action="store_true", help="Skip pandoc/style rebuild and only verify existing DOCX files.")
    parser.add_argument("--no-lint", action="store_true", help="跳过 md 结构 lint（仅应急用）")
    args = parser.parse_args()

    selected = CHAPTERS
    if args.chapters:
        wanted = set(args.chapters)
        selected = [chapter for chapter in CHAPTERS if chapter.key in wanted]
        unknown = wanted - {chapter.key for chapter in CHAPTERS}
        if unknown:
            print("Unknown chapter(s): " + ", ".join(sorted(unknown)), file=sys.stderr)
            return 2

    if not args.no_lint:
        findings = lint_md.lint_paths(
            [f"{c.folder}/{c.markdown}" for c in selected])
        if lint_md.report(findings):
            print("md 结构 lint 未通过；修复源稿后重试（或 --no-lint）", file=sys.stderr)
            return 2

    if not args.verify_only:
        for chapter in selected:
            build_chapter(chapter)

    results = [verify_chapter(chapter) for chapter in selected]
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
