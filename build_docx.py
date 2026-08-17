#!/usr/bin/env python3
"""Build Markdown chapters into styled DOCX reference files.

Usage:
    python3 build_docx.py           # build all chapters
    python3 build_docx.py 1a_diffusion
    python3 build_docx.py --verify-only
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


ROOT = Path(__file__).resolve().parent


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


# Output: intermediate raw docx in chapter folder, reference docx in docx/
CHAPTERS = [
    Chapter("1_ai_math", "1_ai_math", "AI数学_从起步到前沿.md", "AI数学_从起步到前沿_raw.docx", str(ROOT / "docx" / "AI数学_从起步到前沿.docx"), "AI数学：从起步到前沿", "# 附录：自检问题与答案"),
    Chapter("1a_diffusion", "1a_diffusion", "扩散_从噪声生成.md", "扩散_从噪声生成_raw.docx", str(ROOT / "docx" / "扩散_从噪声生成.docx"), "扩散：从噪声生成", "## B. 自检问题与答案"),
    Chapter("2_foundation", "2_foundation", "基座模型_从咿呀到行动.md", "基座模型_从咿呀到行动_raw.docx", str(ROOT / "docx" / "基座模型_从咿呀到行动.docx"), "基座模型：从咿呀到行动", "## 附录：自检问题与答案"),
    Chapter("3_use_ai", "3_use_ai", "用好AI_从有用到好用.md", "用好AI_从有用到好用_raw.docx", str(ROOT / "docx" / "用好AI_从有用到好用.docx"), "用好AI：从有用到好用", "## 附录：自检问题与答案"),
]


def preprocess_self_check(text: str, split_marker: str) -> str:
    """Extract <details> answer blocks into a separate section with page break.

    Only <details> blocks in the self-check section (after the per-chapter
    ``split_marker``, e.g. "## B. 自检问题") are extracted to the answer
    appendix.  <details> blocks in chapter bodies are expanded inline
    (bold title + content) so they render properly in docx.
    """
    # Replace standalone --- separators (not YAML frontmatter) with * * *
    # to prevent pandoc's yaml_metadata_block from eating sections containing
    # colon-bearing lines (e.g. "doi: 10.1038/...") between two --- delimiters.
    # NOTE: \s* would also swallow the blank line after ---, merging the
    # separator with a following heading (pandoc then treats the heading as a
    # paragraph continuation). Match only the newline itself:
    text = re.sub(r'(?<=\n)---[^\S\n]*\n(?!$)', '* * *\n', text)

    # Split at self-check section: chapter body vs Q&A section
    split_pos = text.find(split_marker)

    if split_pos == -1:
        # No self-check section — just expand all <details> inline
        return _expand_details_inline(text)

    chapter_text = text[:split_pos]
    qa_text = text[split_pos:]

    # Expand chapter-body <details> inline
    chapter_text = _expand_details_inline(chapter_text)

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
        q_num += 1
        content = m.group(2).strip()
        answers.append(f"**A{q_num}**：{content}")
        return ""  # remove from questions section

    questions_only = pattern.sub(_extract, qa_text)

    if not answers:
        return chapter_text + questions_only

    # Build answer section with page break before it
    answer_section = (
        "\n\n\\newpage\n\n"
        "### E. 自检答案\n\n"
        "> 答题建议：先独立完成上一页的自检问题，再翻页对照答案。\n\n"
        + "\n\n".join(answers)
    )

    return chapter_text + questions_only + answer_section


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
            str(ROOT / "style_docx.py"),
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
        bookmarks = set(re.findall(r'<w:bookmarkStart[^>]*w:name="([^"]+)"', xml))
        anchors = re.findall(r'<w:hyperlink[^>]*w:anchor="([^"]+)"', xml)
        dead_anchors = [a for a in anchors if a not in bookmarks]

    ok = not missing_images and media_count >= len(image_refs) and not dead_anchors
    status = "OK" if ok else "FAIL"
    print(
        f"{status} {chapter.key}: images={media_count}/{len(image_refs)} "
        f"drawings={drawing_count} tables={table_count} math={math_count} "
        f"links={len(anchors)}/{len(anchors) - len(dead_anchors)} headers={headers}"
    )
    if missing_images:
        print(f"  missing images: {missing_images}")
    if dead_anchors:
        print(f"  dead anchors: {dead_anchors}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and verify styled DOCX outputs.")
    parser.add_argument("chapters", nargs="*", help="Chapter keys to build: " + ", ".join(c.key for c in CHAPTERS))
    parser.add_argument("--verify-only", action="store_true", help="Skip pandoc/style rebuild and only verify existing DOCX files.")
    args = parser.parse_args()

    selected = CHAPTERS
    if args.chapters:
        wanted = set(args.chapters)
        selected = [chapter for chapter in CHAPTERS if chapter.key in wanted]
        unknown = wanted - {chapter.key for chapter in CHAPTERS}
        if unknown:
            print("Unknown chapter(s): " + ", ".join(sorted(unknown)), file=sys.stderr)
            return 2

    if not args.verify_only:
        for chapter in selected:
            build_chapter(chapter)

    results = [verify_chapter(chapter) for chapter in selected]
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
