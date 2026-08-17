#!/usr/bin/env python3
r"""把四篇技术文档 md 合体转换为最终发布产物：单个响应式 HTML（动态侧边目录 + KaTeX 公式）。

用法:
    python3 build_html.py [--out html/index.html]

流程:
    1. 每篇 md 用 pandoc 转 HTML（--mathjax 输出 \\(...\\) 供 KaTeX 渲染）
    2. 内链修复（md_links）：目录锚点改写为 pandoc 实际 id，标题 id 加 doc-N- 前缀后回写 href
    3. 每篇包进 <div class="doc-section" id="doc-N">，标题层级整体 +1（H1→H2 等）
    4. 图片路径修正为 html/figures/
    5. 合并 + 注入模板（CSS/JS/KaTeX CDN）
"""
import argparse
import re
import subprocess
import shutil
import tempfile
from pathlib import Path

import md_links

# pandoc reader 参数：harvest（md_links）与真实转换共用，保证标题 id 一字不差
FROM_FLAGS = md_links.FROM_FLAGS

import md_links

# pandoc reader 参数（harvest 与真实转换必须一字不差，保证 id 一致）
FROM_FLAGS = "markdown+gfm_auto_identifiers+tex_math_dollars+raw_tex-yaml_metadata_block"

ROOT = Path(__file__).resolve().parent
HTML_DIR = ROOT / "html"
FIG_SRC = [ROOT / "1_ai_math" / "figures", ROOT / "2_foundation" / "figures",
           ROOT / "3_use_ai" / "figures", ROOT / "1a_diffusion" / "figures"]

# 四篇：(md路径相对ROOT, 显示标题, doc-id)
DOCS = [
    ("1_ai_math/AI数学_从起步到前沿.md", "AI数学：从起步到前沿", "doc-1"),
    ("2_foundation/基座模型_从咿呀到行动.md", "基座模型：从咿呀到行动", "doc-2"),
    ("3_use_ai/用好AI_从有用到好用.md", "用好AI：从有用到好用", "doc-3"),
    ("1a_diffusion/扩散_从噪声生成.md", "扩散：从噪声生成", "doc-4"),
]

# 图片重名冲突：不同子目录可能有同名 fig_*.png
FIG_PREFIX = {
    "1_ai_math": "aimath",
    "1a_diffusion": "diff",
    "2_foundation": "base",
    "3_use_ai": "use",
}


# 自动安装前端资源所用的 npm 缓存目录（系统临时目录，避免污染仓库）
NPM_CACHE_DIR = Path(tempfile.gettempdir()) / "ai-primer-npm-assets"
KATEX_VERSION = "0.16.9"
HLJS_VERSION = "11.11.2"


def _npm_install(packages: list[str]) -> Path:
    """Run npm install for missing frontend assets into a shared cache dir."""
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError(
            "未找到 npm，无法自动安装 KaTeX/highlight.js。"
            "请安装 Node.js/npm，或恢复 vendor/ 目录后重试。"
        )
    NPM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        npm, "install",
        "--prefix", str(NPM_CACHE_DIR),
        "--no-save",
        "--no-package-lock",
        "--no-audit",
        "--no-fund",
        "--ignore-scripts",
        *packages,
    ]
    print("⬇ 自动安装前端资源：" + " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "自动安装前端资源失败，请检查网络/npm 配置，或恢复 vendor/ 目录后重试。"
        ) from exc
    return NPM_CACHE_DIR / "node_modules"


def _copy_highlight_assets(src: Path, dst: Path) -> None:
    """Copy highlight.js assets into html/highlight in the layout the template expects."""
    dst.mkdir(parents=True, exist_ok=True)

    js = src / "highlight.min.js"
    if not js.exists():
        js = src / "lib" / "highlight.min.js"
    if not js.exists():
        raise RuntimeError(f"highlight.js 源中未找到 highlight.min.js：{src}")
    shutil.copy2(js, dst / "highlight.min.js")

    # npm 包样式在 styles/ 下；仓库 vendor/ 里样式直接在根目录。
    css_dir = src / "styles" if (src / "styles").exists() else src
    for css_name in ("atom-one-dark.min.css", "github.min.css"):
        css = css_dir / css_name
        if css.exists():
            shutil.copy2(css, dst / css_name)



def preprocess_md(text: str) -> str:
    """预处理器：修正 pandoc 会误解析的语法。"""
    # 1. 行首 --- 在段落后会被 GFM 当作 h2；转成 ***（pandoc 渲染 <hr>）
    lines = text.split("\n")
    out = []
    for i, line in enumerate(lines):
        s = line.strip()
        if s == "---" and i > 0:
            prev = lines[i - 1].strip()
            if prev and not prev.startswith(("#", ">", "|", "-", "*")):
                out.append("***")
                continue
        out.append(line)
    return "\n".join(out)


def pandoc_to_html(md_text: str, cwd: Path, prefix: str) -> str:
    """单篇 md → HTML 片段（pandoc）。用 tempfile 避免残留临时文件。"""
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".md", delete=False) as f:
        f.write(md_text)
        tmp_path = f.name
    try:
        r = subprocess.run(
            ["pandoc", tmp_path,
             "-t", "html",
             f"--from={FROM_FLAGS}",
             "--mathjax",
             "--wrap=none",
             "--resource-path=.:figures"],
            cwd=cwd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"pandoc 失败: {r.stderr[:500]}")
        return r.stdout
    finally:
        Path(tmp_path).unlink(missing_ok=True)



SELFCHECK_MARKERS = [
    "## 附录：自检问题与答案",
    "## B. 自检问题与答案",
    "# 附录：自检问题与答案",
]

SELFCHECK_END_MARKERS = [
    "## 附录：algo-coach——把全篇框架用进一个真实产品",
    "## C. 逻辑链",
    "> **全书完**",
]


def find_selfcheck_span(text: str):
    """返回自检附录在 md 中的 [start, end)；找不到返回 None。"""
    start = -1
    for marker in SELFCHECK_MARKERS:
        pos = text.find(marker)
        if pos != -1:
            start = pos
            break
    if start == -1:
        return None
    end = len(text)
    for em in SELFCHECK_END_MARKERS:
        pos = text.find(em, start + 1)
        if pos != -1 and pos < end:
            end = pos
    return start, end


def remove_selfcheck_appendix(text: str) -> str:
    """从 md 中移除独立的“自检问题与答案”附录，保留需要留存的扩展/收束内容。"""
    span = find_selfcheck_span(text)
    if span is not None:
        start, end = span
        # 3_use_ai 的“扩展题”不是正文某章的自检题，保留为文末独立练习区；
        # 只移除与正文章节对应的自检 Q&A 附录。
        keep_start = text.find("### 扩展题", start, end)
        if keep_start != -1:
            removed = text[start:keep_start]
            tail = text[keep_start:]
        else:
            removed = text[start:end]
            tail = text[end:]

        # AI数学/基座模型 的“把知识连成网”属于附录收束内容，移到正文自检区之后保留。
        conn = re.search(
            r'<details>\s*<summary>\s*把知识连成网.*?</details>',
            removed,
            re.S,
        )
        connection = conn.group(0) if conn else ""

        text = text[:start] + connection + tail

    return text


def remove_selfcheck_toc_refs(text: str) -> str:
    """移除/清理 HTML 中指向已删除自检附录的目录项，保留源 md 的完整目录。"""
    lines = text.splitlines(keepends=True)
    out = []
    for line in lines:
        stripped = line.strip()
        # 独立的自检附录目录项：HTML 中该附录已被移除，不能保留死链。
        if stripped.startswith("- 自检题卡住了？提示与答案在文末 ->") or \
           stripped.startswith("- [自检问题与答案](#附录自检问题与答案)"):
            continue
        # 1a_diffusion 的附录总目录行：链接指向仍保留的 A，但不应再列出已移除的 B。
        if stripped.startswith("- [附录](#a-数学预备)") and "B 自检问题" in line:
            line = line.replace(" · B 自检问题", "")
        out.append(line)
    return "".join(out)


def parse_selfcheck_html(appendix_html: str):
    """把自检附录 HTML 解析成按章排列的 Q&A 数据。"""
    chapters = []
    token_re = re.compile(
        r'(<h3\b[^>]*>.*?</h3>|'
        r'<p><strong>【[^】]+】</strong></p>|'
        r'<strong>Q(\d+).*?</strong>|'
        r'<details>.*?</details>)',
        re.S,
    )
    current = None
    current_group = None
    for m in token_re.finditer(appendix_html):
        tok = m.group(0)
        if tok.startswith('<h3'):
            if current is not None:
                chapters.append(current)
            heading = re.sub(r'<[^>]+>', '', tok).strip()
            current = {
                "heading": heading,
                "questions": [],
                "group_details": [],
            }
            current_group = None
        elif tok.startswith('<p><strong>【'):
            gm = re.match(r'<p><strong>【([^】]+)】</strong></p>', tok)
            current_group = gm.group(1) if gm else None
        elif tok.startswith('<strong>Q'):
            if current is None:
                continue
            qm = re.match(r'<strong>Q(\d+)', tok)
            if qm:
                current["questions"].append({
                    "group": current_group,
                    "number": int(qm.group(1)),
                    "hint": None,
                    "answer": None,
                })
        elif tok.startswith('<details>'):
            if current is None:
                continue
            sm = re.search(r'<summary>\s*(.*?)\s*</summary>', tok, re.S)
            summary = sm.group(1).strip() if sm else ""
            content = tok[sm.end():-len('</details>')].strip() if sm else tok
            if current["questions"] and (
                current["questions"][-1].get("hint") is None
                or current["questions"][-1].get("answer") is None
            ):
                q = current["questions"][-1]
                if "提示" in summary:
                    q["hint"] = content
                elif "答案" in summary or "解析" in summary:
                    q["answer"] = content
                else:
                    if q.get("answer") is None:
                        q["answer"] = content
                    else:
                        current["group_details"].append({
                            "summary": summary,
                            "content": content,
                        })
            else:
                current["group_details"].append({
                    "summary": summary,
                    "content": content,
                })
    if current is not None:
        chapters.append(current)
    return chapters


def extract_selfcheck_data(md_text: str, cwd: Path):
    """从原始 md 中抽出附录区并转成结构化 Q&A 数据。"""
    span = find_selfcheck_span(md_text)
    if span is None:
        return []
    start, end = span
    segment = md_text[start:end]
    appendix_html = pandoc_to_html(segment, cwd, "selfcheck")
    return parse_selfcheck_html(appendix_html)


def extract_top_level_lis(fragment: str):
    """提取 HTML 片段中 <ol> 下的顶层 <li> 内部 HTML，并把随后的 <ul> 补充到对应编号项。

    用于把整组答案拆到每题；只把有序列表的编号项当作一道题，<ul> 子要点并入前一项。
    """
    # 1. 先找所有 <ol> 块，提取其中的编号 <li>
    ol_blocks = []
    for m in re.finditer(r'<ol\b', fragment):
        end_ol = fragment.find('</ol>', m.end())
        if end_ol == -1:
            continue
        ol_blocks.append((m.start(), end_ol + len('</ol>')))
    if not ol_blocks:
        return []

    def _ol_lis(block: str):
        events = []
        for m in re.finditer(r'<li\b', block):
            tag_end = block.find('>', m.end())
            events.append((m.start(), "li_start", tag_end + 1 if tag_end != -1 else m.end()))
        for m in re.finditer(r'</li>', block):
            events.append((m.start(), "li_end", m.end()))
        for m in re.finditer(r'<ol\b', block):
            events.append((m.start(), "ol_start", m.end()))
        for m in re.finditer(r'</ol>', block):
            events.append((m.start(), "ol_end", m.end()))
        for m in re.finditer(r'<ul\b', block):
            events.append((m.start(), "ul_start", m.end()))
        for m in re.finditer(r'</ul>', block):
            events.append((m.start(), "ul_end", m.end()))
        events.sort(key=lambda x: x[0])
        list_stack = []
        depth = 0
        start_content = None
        items = []
        for pos, typ, end in events:
            if typ == "ol_start":
                list_stack.append("ol")
            elif typ == "ul_start":
                list_stack.append("ul")
            elif typ == "ol_end":
                if list_stack and list_stack[-1] == "ol":
                    list_stack.pop()
            elif typ == "ul_end":
                if list_stack and list_stack[-1] == "ul":
                    list_stack.pop()
            elif typ == "li_start":
                if depth == 0 and list_stack and list_stack[-1] == "ol":
                    start_content = end
                depth += 1
            elif typ == "li_end":
                depth -= 1
                if depth == 0 and start_content is not None:
                    items.append(block[start_content:pos].strip())
                    start_content = None
        return items

    items = []
    for i, (start_ol, end_ol) in enumerate(ol_blocks):
        block = fragment[start_ol:end_ol]
        block_items = _ol_lis(block)
        if not block_items:
            continue
        next_start = ol_blocks[i + 1][0] if i + 1 < len(ol_blocks) else len(fragment)
        tail = fragment[end_ol:next_start]
        # 把该编号项后面紧跟的 <ul> 子要点并入最后一项
        ul_tail = ""
        for um in re.finditer(r'<ul\b.*?</ul>', tail, re.S):
            ul_tail += um.group(0)
        if ul_tail:
            block_items[-1] = block_items[-1] + "\n" + ul_tail
        items.extend(block_items)
    return items


def collect_body_slots(region: str):
    """收集一个“本章自检”区域里的题目槽位（li 或 p），返回带 group/number 的列表。"""
    group_positions = [
        (m.start(), m.end(), m.group(1))
        for m in re.finditer(r'<p><strong>【([^】]+)】</strong></p>', region)
    ]

    events = []
    for m in re.finditer(r'<li\b', region):
        events.append((m.start(), "li_start", m.end()))
    for m in re.finditer(r'</li>', region):
        events.append((m.start(), "li_end", m.end()))
    events.sort(key=lambda x: x[0])

    depth = 0
    start_content = None
    li_slots = []
    for pos, typ, end in events:
        if typ == "li_start":
            if depth == 0:
                start_content = end
            depth += 1
        else:
            depth -= 1
            if depth == 0 and start_content is not None:
                li_slots.append({
                    "kind": "li",
                    "start": start_content,
                    "end": pos,  # 指向 </li> 的开头，插入点在其前
                })
                start_content = None

    p_slots = []
    for m in re.finditer(r'<p><strong>\s*(\d+)\s*[.、．]', region):
        start = m.start()
        end = region.find('</p>', m.end())
        if end == -1:
            continue
        end += len('</p>')
        p_slots.append({
            "kind": "p",
            "start": start,
            "end": end,
            "number": int(m.group(1)),
        })

    slots = li_slots + p_slots
    slots.sort(key=lambda s: s["start"])

    result = []
    group_counts = {}
    current_group = None
    gi = 0
    for slot in slots:
        while gi < len(group_positions) and group_positions[gi][0] < slot["start"]:
            current_group = group_positions[gi][2]
            gi += 1
        slot["group"] = current_group
        key = current_group if current_group is not None else "__none__"
        if slot["kind"] == "p" and "number" in slot:
            num = slot["number"]
        else:
            group_counts[key] = group_counts.get(key, 0) + 1
            num = group_counts[key]
        slot["number"] = num
        result.append(slot)
    return result


def make_popup(hint_html, answer_html):
    """生成题旁的提示/答案折叠块。"""
    if not hint_html and not answer_html:
        return ""
    parts = ['<div class="selfcheck-popup">']
    if hint_html:
        parts.append(f'<details class="selfcheck-hint"><summary>提示</summary>{hint_html}</details>')
    if answer_html:
        parts.append(f'<details class="selfcheck-answer"><summary>答案</summary>{answer_html}</details>')
    parts.append('</div>')
    return "".join(parts)


def find_question(chapter, slot):
    """按 group+number（或仅 number）在 per_q 章节中查找对应题目。"""
    questions = chapter.get("questions", [])
    if not questions:
        return None
    has_groups = any(q.get("group") for q in questions)
    if has_groups:
        return next(
            (
                q for q in questions
                if (q.get("group") or "") == (slot.get("group") or "")
                and q["number"] == slot["number"]
            ),
            None,
        )
    return next((q for q in questions if q["number"] == slot["number"]), None)


def inject_selfcheck_popups(html: str, qa_data):
    """把自检 Q&A 以 popup/details 形式插到正文题目旁边。"""
    markers = list(re.finditer(r'<p><strong>本章自检</strong>：</p>', html))
    # 从后往前处理，避免已插入内容影响前面标记的位置
    for idx in range(len(markers) - 1, -1, -1):
        if idx >= len(qa_data):
            continue
        chapter = qa_data[idx]
        m = markers[idx]
        region_start = m.end()
        nxt = re.search(r'<h[1-6]\b', html[region_start:])
        region_end = region_start + nxt.start() if nxt else len(html)
        region = html[region_start:region_end]
        slots = collect_body_slots(region)

        insertions = []
        if chapter.get("questions"):
            for slot in slots:
                q = find_question(chapter, slot)
                if q is None:
                    continue
                popup = make_popup(q.get("hint"), q.get("answer"))
                if not popup:
                    continue
                insert_at = slot["end"] if slot["kind"] == "li" else slot["end"]
                insertions.append((region_start + insert_at, popup))
        else:
            # AI 数学等没有 Q 编号、以整组 details 出现的章节：
            # 把提示/答案的 <li> 按组切分，逐题插入。
            hint_items = None
            for d in chapter.get("group_details", []):
                if "提示" in d["summary"]:
                    hint_items = extract_top_level_lis(d["content"])
                    break

            consumed = {}
            group_names = []
            for slot in slots:
                if slot["group"] not in group_names:
                    group_names.append(slot["group"])
            for gname in group_names:
                gslots = [s for s in slots if s["group"] == gname]
                if not gslots:
                    continue
                answer_key = None
                if gname and "逻辑链" in gname:
                    answer_key = "逻辑链答案"
                elif gname and ("知识点" in gname or "Attention" in gname or "组装" in gname):
                    answer_key = "知识点答案"
                elif gname is None:
                    answer_key = "知识点答案"

                ans_items = []
                if answer_key:
                    for d in chapter.get("group_details", []):
                        if answer_key in d["summary"]:
                            ans_items = extract_top_level_lis(d["content"])
                            break

                offset = consumed.get(answer_key, 0)
                use_hint = bool(
                    gname and ("知识点" in gname or "Attention" in gname or "组装" in gname)
                ) or (gname is None and answer_key == "知识点答案")
                for j, slot in enumerate(gslots):
                    hint_html = None
                    if use_hint and hint_items and offset + j < len(hint_items):
                        hint_html = hint_items[offset + j]
                    ans_html = None
                    if ans_items and offset + j < len(ans_items):
                        ans_html = ans_items[offset + j]
                    popup = make_popup(hint_html, ans_html)
                    if popup:
                        insert_at = slot["end"] if slot["kind"] == "li" else slot["end"]
                        insertions.append((region_start + insert_at, popup))
                consumed[answer_key] = offset + len(gslots)

        for pos, snippet in sorted(insertions, key=lambda x: x[0], reverse=True):
            html = html[:pos] + snippet + html[pos:]

    return html


# LaTeX 命令 → Unicode 可读符号映射（供 TOC data-label 使用）
CMD_MAP = {
    '\\eta': 'η', '\\theta': 'θ', '\\varepsilon': 'ε', '\\epsilon': 'ϵ',
    '\\nabla': '∇', '\\times': '×', '\\cdot': '·', '\\log': 'log',
    '\\max': 'max', '\\min': 'min', '\\sum': 'Σ', '\\prod': 'Π',
    '\\int': '∫', '\\partial': '∂', '\\infty': '∞', '\\approx': '≈',
    '\\neq': '≠', '\\geq': '≥', '\\leq': '≤', '\\alpha': 'α',
    '\\beta': 'β', '\\gamma': 'γ', '\\lambda': 'λ', '\\mu': 'μ',
    '\\sigma': 'σ', '\\omega': 'ω', '\\phi': 'φ', '\\pi': 'π',
    '\\delta': 'δ', '\\in': '∈', '\\subset': '⊂', '\\cup': '∪',
    '\\cap': '∩', '\\rightarrow': '→', '\\leftarrow': '←',
    '\\Rightarrow': '⇒', '\\equiv': '≡', '\\propto': '∝', '\\pm': '±',
    '\\dots': '…', '\\ldots': '…', '\\cdots': '…',
}

# 上标/下标 Unicode 映射（含常用字母下标）
_SUP = str.maketrans('0123456789+-=()n', '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ')
_SUB = str.maketrans('0123456789+-=()aehklnoprx', '₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕₖₗₙₒₚᵣₓ')


def convert_latex(label: str) -> str:
    """把标题里的 LaTeX 命令/记号转成 Unicode 可读符号（TOC 显示用）。"""
    # 1. \sqrt{...} → √(...)
    label = re.sub(r'\\sqrt\{([^}]*)\}', r'√\1', label)
    # 2. \text{...} / \mathrm{...} / \operatorname{...} → 内容
    label = re.sub(r'\\(?:text|mathrm|operatorname)\{([^}]*)\}', r'\1', label)
    # 3. 简单命令映射（较长优先，避免 \eta 匹配 \varepsilon 前缀）
    for cmd in sorted(CMD_MAP, key=len, reverse=True):
        label = label.replace(cmd, CMD_MAP[cmd])
    # 4. 剩余 \cmd 剥掉反斜杠（保留字母）
    label = re.sub(r'\\([a-zA-Z]+)', r'\1', label)
    # 5. 花括号清理
    label = label.replace('{', '').replace('}', '')
    # 6. 下标/上标转 Unicode（仅纯记号，避免吃掉后续文字）
    def sub_repl(m):
        inner = m.group(1)
        if re.fullmatch(r'[0-9+\-=()a-z]+', inner):
            return inner.translate(_SUB)
        return '_' + inner
    label = re.sub(r'_\{?([^}\s]*)\}?', sub_repl, label)
    def sup_repl(m):
        inner = m.group(1)
        if re.fullmatch(r'[0-9+\-=()n]+', inner):
            return inner.translate(_SUP)
        return '^' + inner
    label = re.sub(r'\^\{?([^}\s]*)\}?', sup_repl, label)
    return label


def bump_headings(html: str, new_doc_id: str) -> str:
    """把 h1-h6 提升一级（h1→h2），并给顶级文档标题加 doc 前缀 id。
    同时给每个标题 id 加 doc 前缀避免跨篇冲突。
    额外给每个标题加 data-label（KaTeX 渲染前的干净纯文本，供 TOC 使用）。"""
    import html as html_mod

    def repl(m):
        tag, attrs, inner = m.group(1), m.group(2), m.group(3)
        # 解析现有 id
        idm = re.search(r'id="([^"]*)"', attrs)
        if idm:
            old_id = idm.group(1)
            new_id = f"{new_doc_id}-{old_id}"
            attrs = attrs.replace(f'id="{old_id}"', f'id="{new_id}"')
        # 干净纯文本：去标签、去公式定界符、实体还原
        label = re.sub(r"<[^>]+>", "", inner)
        label = html_mod.unescape(label)
        label = label.replace(r"\(", "").replace(r"\)", "").replace(r"\[", "").replace(r"\]", "")
        label = convert_latex(label)
        label = label.strip()
        attrs += f' data-label="{label}"'
        return f"<{tag}{attrs}>{inner}</{tag}>"

    # 先统一加前缀（所有标题）
    html = re.sub(r"<(h[1-6])([^>]*)>(.*?)</\1>", repl, html, flags=re.S)
    # 再提升一级：h1→h2, h2→h3, h3→h4, h4→h5, h5→h6（只升 1 级，一次性替换）
    for lv in range(5, 0, -1):
        html = html.replace(f"<h{lv}", f"<h{lv+1}").replace(f"</h{lv}>", f"</h{lv+1}>")
    return html


def remove_doc_title_heading(html: str, title: str) -> str:
    """去掉 pandoc 把原文档 H1 提升后产生的重复 H2 标题。

    页面顶部已经有独立的 <h1 class="doc-title">，这个重复的 H2 只会造成
    多余章节和视觉重复。
    """
    pattern = re.compile(
        r'<h2[^>]*>\s*' + re.escape(title) + r'\s*</h2>',
        re.S
    )
    return pattern.sub('', html, count=1)


def wrap_chapters(html: str) -> str:
    """把每篇文档里的 h2 章节目录包成 <section class="chapter">。

    这样可以在 CSS 中给每一章加 content-visibility: auto，
    让超长页面滚动时跳过视口外的渲染，显著改善滚动性能。
    """
    # 用捕获组切分：奇数位是 <h2 ...>，偶数位是两两之间的内容
    parts = re.split(r'(<h2\b[^>]*>)', html)
    out: list[str] = []
    buf: list[str] = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            buf.append(part)
        else:
            # part 是 h2 开标签：先把之前累积的内容作为一章收掉
            if buf and "".join(buf).strip():
                out.append('<section class="chapter">' + "".join(buf) + '</section>')
                buf = []
            buf.append(part)
    if buf and "".join(buf).strip():
        out.append('<section class="chapter">' + "".join(buf) + '</section>')
    return "".join(out)

def ensure_frontend_assets() -> None:
    """Ensure html/katex and html/highlight exist, auto-installing via npm if needed."""
    katex_dst = HTML_DIR / "katex"
    hljs_dst = HTML_DIR / "highlight"

    katex_candidates = [
        ROOT / "vendor" / "katex",
        Path("/tmp/node_modules/katex/dist"),
        NPM_CACHE_DIR / "node_modules" / "katex" / "dist",
    ]
    hljs_candidates = [
        ROOT / "vendor" / "highlight.js",
        Path("/tmp/node_modules/highlight.js"),
        Path("/tmp/node_modules/@highlightjs/cdn-assets"),
        NPM_CACHE_DIR / "node_modules" / "@highlightjs" / "cdn-assets",
    ]

    # 如果目标已有产物则跳过；否则若所有本地源都缺失，自动用 npm 安装缺失项
    missing_packages = []
    if not katex_dst.exists() and not any(p.exists() for p in katex_candidates):
        missing_packages.append(f"katex@{KATEX_VERSION}")
    if not hljs_dst.exists() and not any(p.exists() for p in hljs_candidates):
        missing_packages.append(f"@highlightjs/cdn-assets@{HLJS_VERSION}")
    if missing_packages:
        _npm_install(missing_packages)

    if katex_dst.exists():
        print(f"✓ KaTeX 已存在（{katex_dst}），跳过复制")
    else:
        katex_src = next((p for p in katex_candidates if p.exists()), None)
        if katex_src is None:
            raise RuntimeError("KaTeX 源不可用，无法生成完整 HTML。请检查 npm 安装或恢复 vendor/。")
        shutil.copytree(katex_src, katex_dst)
        print(f"✓ 复制 KaTeX 到 html/katex/")

    # 复制 highlight.js（代码高亮，本地化）
    if hljs_dst.exists():
        print(f"✓ highlight.js 已存在（{hljs_dst}），跳过复制")
    else:
        hljs_src = next((p for p in hljs_candidates if p.exists()), None)
        if hljs_src is None:
            raise RuntimeError("highlight.js 源不可用，无法生成完整 HTML。请检查 npm 安装或恢复 vendor/。")
        _copy_highlight_assets(hljs_src, hljs_dst)
        print(f"✓ 复制 highlight.js 到 html/highlight/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HTML_DIR / "index.html"))
    args = ap.parse_args()

    HTML_DIR.mkdir(exist_ok=True)
    (HTML_DIR / "figures").mkdir(exist_ok=True)

    ensure_frontend_assets()

    # 复制图片（重命名加前缀）；先清空旧图，避免源图删除后残留
    for old in (HTML_DIR / "figures").glob("*.png"):
        old.unlink()
    copied = 0
    for src_dir, key in zip(FIG_SRC, [d[0].split("/")[0] for d in DOCS]):
        prefix = FIG_PREFIX[key]
        if not src_dir.exists():
            continue
        for p in src_dir.glob("*.png"):
            shutil.copy2(p, HTML_DIR / "figures" / f"{prefix}_{p.name}")
            copied += 1
    print(f"✓ 复制图片 {copied} 张")

    # 逐篇转 HTML
    sections = []
    for md_rel, title, doc_id in DOCS:
        md_path = ROOT / md_rel
        key = md_rel.split("/")[0]
        text = md_path.read_text(encoding="utf-8")
        qa_data = extract_selfcheck_data(text, md_path.parent)
        text = remove_selfcheck_appendix(text)
        text = remove_selfcheck_toc_refs(text)
        text = preprocess_md(text)
        text, link_warnings, id_set = md_links.fix_internal_links(
            text, md_path.parent, FROM_FLAGS)
        for w in link_warnings:
            print(f"⚠ {md_rel}: {w}")
        html = pandoc_to_html(text, md_path.parent, key)
        html = bump_headings(html, doc_id)
        html = inject_selfcheck_popups(html, qa_data)
        # 代码块行号 id 去重：pandoc 每篇都从 cb1 开始，合并后会产生重复 id；
        # 这里给每个 doc 的代码块 id 加上 doc-N- 前缀，保证全局唯一。
        html = re.sub(r'id="(cb[0-9][^"]*)"', lambda m: f'id="{doc_id}-{m.group(1)}"', html)
        html = re.sub(r'href="#(cb[0-9][^"]*)"', lambda m: f'href="#{doc_id}-{m.group(1)}"', html)
        # 内链 href 回写 doc-N- 前缀（fix_internal_links 已把锚点改成 pandoc
        # 实际 id，此处是纯精确替换；不在 id 集合里的 href 原样保留）
        html = re.sub(
            r'href="#([^"]+)"',
            lambda m: f'href="#{doc_id}-{m.group(1)}"'
            if m.group(1) in id_set else m.group(0),
            html)
        # 注意：不 unescape 公式实体！pandoc 输出 &lt; &gt; &amp; 是安全的 HTML 实体，
        # DOM textContent 会转回 < > &，KaTeX 读取时得到正确字符。若还原成裸 < 会破坏 HTML 解析。
        # 表格包 .table-wrap（移动端横向滚动）
        html = re.sub(r'(<table[^>]*>)', r'<div class="table-wrap">\1', html)
        html = re.sub(r'(</table>)', r'\1</div>', html)
        # 超长行内公式（>80字符）标记 math-long，允许换行避免横向滚动
        html = re.sub(r'<span class="math inline">([^<]{80,}?)</span>',
                      r'<span class="math inline math-long">\1</span>', html)
        # 修正图片路径（pandoc 输出 src="figures/xxx.png"）+ 懒加载（保留原 alt）
        def _img_repl(m):
            src = m.group(1)
            rest = m.group(2)  # 含 alt，可能以 "/" 结尾（pandoc 的 /> 被换行拆开）
            # 去掉尾部 / 或空格，追加 loading="lazy" 并闭合
            rest = re.sub(r'/?\s*$', '', rest)
            return f'<img src="figures/{FIG_PREFIX[key]}_{src}"{rest} loading="lazy" decoding="async" />'
        html = re.sub(r'<img src="figures/([^"]*)"([^><]*)>', _img_repl, html)
        # 去掉重复的文档大标题（已有外层 doc-title），再按章包裹
        html = remove_doc_title_heading(html, title)
        html = wrap_chapters(html)
        # 文档标题块
        section = f'<section class="doc-section" id="{doc_id}" data-title="{title}">\n'
        section += f'<h1 class="doc-title" id="{doc_id}-title">{title}</h1>\n'
        section += html
        section += "</section>"
        sections.append(section)
        print(f"✓ {md_rel} → HTML ({len(html)} chars)")

    body = "\n".join(sections)

    # 模板
    html_out = TEMPLATE.replace("{{BODY}}", body)
    out = Path(args.out)
    out.write_text(html_out, encoding="utf-8")
    print(f"✓ 输出 {out} ({out.stat().st_size/1024:.0f} KB)")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 四篇入门读物合集</title>
<link rel="stylesheet" href="katex/katex.min.css">
<link rel="stylesheet" href="highlight/atom-one-dark.min.css" id="hljs-theme">
<script src="katex/katex.min.js"></script>
<script src="katex/contrib/auto-render.min.js"></script>
<script src="highlight/highlight.min.js"></script>
<style>
/* ===== 基础 ===== */
* { margin:0; padding:0; box-sizing:border-box; }
:root {
  --bg: #fafaf8; --card: #ffffff; --ink: #1f2937; --ink-soft: #4b5563;
  --line: #e5e7eb; --accent: #2563eb; --accent-soft: #eff6ff;
  --code-bg: #f3f4f6; --sidebar-w: 300px;
  --blockquote-bg: #f9fafb; --blockquote-line: #d1d5db;
  --th-bg: #f3f4f6; --row-alt: #fafafa; --pre-bg: #1f2937; --pre-ink: #f9fafb;
  --summary-bg: #f9fafb;
}
/* 深色模式 */
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #111827; --card: #1f2937; --ink: #e5e7eb; --ink-soft: #9ca3af;
    --line: #374151; --accent: #60a5fa; --accent-soft: #1e3a5f;
    --code-bg: #273244; --blockquote-bg: #1a2332; --blockquote-line: #4b5563;
    --th-bg: #273244; --row-alt: #1a2332; --pre-bg: #0d1117; --pre-ink: #e5e7eb;
    --summary-bg: #273244;
  }
  img { filter: brightness(0.9); }
}
html { scroll-behavior:smooth; }
body { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",system-ui,sans-serif;
       background:var(--bg); color:var(--ink); line-height:1.75; }
a { color:var(--accent); text-decoration:none; overflow-wrap:anywhere; word-break:break-word; }

/* 图片全局防溢出 */
img { max-width:100%; height:auto; }

/* ===== 布局 ===== */
.layout { display:flex; max-width:1500px; margin:0 auto; min-height:100vh; }

/* 侧边栏 */
.sidebar { width:var(--sidebar-w); flex-shrink:0; background:var(--card);
           border-right:1px solid var(--line); position:sticky; top:0; height:100vh;
           overflow-y:auto; padding:20px 14px; z-index:50; }
.sidebar-header { font-weight:700; font-size:1.05rem; padding:6px 10px 14px;
                  border-bottom:1px solid var(--line); margin-bottom:10px;
                  color:var(--ink); display:flex; align-items:center; gap:8px; }
.sidebar-header .brand { font-size:0.8rem; color:var(--ink-soft); font-weight:400; }
.toc { list-style:none; font-size:0.86rem; }
.toc li { margin:1px 0; }
.toc a { display:block; padding:4px 10px; border-radius:5px; color:var(--ink-soft);
         transition:all .15s; border-left:2px solid transparent; }
.toc a:hover { background:var(--accent-soft); color:var(--accent); }
.toc a.active { background:var(--accent-soft); color:var(--accent); border-left-color:var(--accent); font-weight:600; }
.toc .lvl-2 { padding-left:22px; }
.toc .lvl-3 { padding-left:38px; font-size:0.8rem; }
.toc .lvl-4 { padding-left:52px; font-size:0.78rem; color:#9ca3af; }
/* 折叠式目录：章 = 可展开组，默认收起 */
.toc .toc-chapter { margin:0; }
.toc .toc-chapter-head { display:flex; align-items:center; cursor:pointer;
                         padding:6px 0; font-weight:600; }
.toc .toc-chapter-head::before { content:'▸'; display:inline-block; width:16px;
                                 color:var(--ink-soft); transition:transform .15s; font-size:0.75rem; }
.toc .toc-chapter.open .toc-chapter-head::before { transform:rotate(90deg); }
.toc .toc-chapter-head a { flex:1; font-weight:600; }
.toc .toc-children { display:none; list-style:none; padding:0; }
.toc .toc-chapter.open .toc-children { display:block; }
.toc .toc-children .lvl-3 { padding-left:22px; }
.toc .toc-children .lvl-4 { padding-left:38px; font-size:0.78rem; color:#9ca3af; }
.toc .doc-head { font-weight:700; color:var(--ink); margin-top:8px; font-size:0.9rem; }
.toc .doc-head a { color:var(--ink); }
.toc .doc-head a:hover { color:var(--accent); }

/* 侧边栏折叠按钮（窄屏） */
.sidebar-toggle { display:none; }

/* 文档切换 */
.doc-switch { display:flex; gap:6px; margin:10px 0; flex-wrap:wrap; }
.doc-btn { flex:1; min-width:60px; padding:6px 4px; border:1px solid var(--line);
           background:var(--card); color:var(--ink-soft); border-radius:6px;
           cursor:pointer; font-size:0.82rem; transition:all .15s; }
.doc-btn:hover { border-color:var(--accent); color:var(--accent); }
.doc-btn.active { background:var(--accent); border-color:var(--accent); color:#fff; font-weight:600; }

/* 搜索框 */
.search-box { margin:10px 0; }
.search-box input { width:100%; padding:8px 10px; border:1px solid var(--line);
                    border-radius:6px; font-size:0.88rem; background:var(--card);
                    color:var(--ink); outline:none; }
.search-box input:focus { border-color:var(--accent); }
.search-box input::placeholder { color:var(--ink-soft); opacity:.7; }

/* 主内容 */
.main { flex:1; min-width:0; padding:36px 48px 80px; }
.doc-section { max-width:860px; margin:0 auto 60px; }
.doc-section + .doc-section { border-top:2px solid var(--line); padding-top:48px; }

/* 性能：超长页面滚动时跳过视口外内容的渲染/绘制 */
.chapter {
  content-visibility: auto;
  contain-intrinsic-size: auto 800px;
}
figure, pre, .table-wrap, details, blockquote {
  content-visibility: auto;
  contain-intrinsic-size: auto 300px;
}
.doc-title { font-size:1.9rem; font-weight:800; margin-bottom:8px; color:var(--ink);
             padding-bottom:12px; border-bottom:3px solid var(--accent); }
.doc-section > .doc-title + * { margin-top:20px; }

/* 标题 */
h2 { font-size:1.55rem; color:var(--ink); margin:40px 0 18px; padding-bottom:8px;
     border-bottom:1px solid var(--line); scroll-margin-top:20px; }
h3 { font-size:1.25rem; margin:30px 0 14px; color:var(--ink); scroll-margin-top:20px; }
h4 { font-size:1.1rem; margin:24px 0 12px; color:var(--ink-soft); scroll-margin-top:20px; }
h5, h6 { font-size:1rem; margin:20px 0 10px; color:var(--ink-soft); }
h2, h3, h4 { font-weight:700; }

/* 正文 */
p { margin:0 0 16px; }
ul, ol { margin:0 0 16px 26px; }
li { margin:4px 0; }
strong { font-weight:700; }

/* 引用 */
blockquote { border-left:4px solid var(--blockquote-line); background:var(--blockquote-bg); padding:12px 18px;
             margin:18px 0; border-radius:0 6px 6px 0; color:var(--ink-soft); }
blockquote > p:last-child { margin-bottom:0; }

/* 公式 */
.katex { font-size:1.05em; }
.math.display { display:block; margin:18px 0; overflow-x:auto; overflow-y:hidden; padding:4px 0; max-width:100%; }
span.math.inline { white-space:nowrap; overflow:visible; display:inline-block;
                   vertical-align:middle; padding:1px 0; }
span.math.inline.math-long { white-space:normal; overflow:visible; }
/* KaTeX 内部强制 nowrap，math-long 需覆盖让长公式换行 */
span.math.inline.math-long .katex,
span.math.inline.math-long .katex .base { white-space:normal !important; }
span.math.inline.math-long .katex .base { width:auto !important; }
/* 移动端：公式超宽时触摸可滚动，但隐藏滚动条（无滑动箭头干扰） */
@media (max-width: 640px) {
  span.math.inline { max-width:100%; overflow-x:auto; overflow-y:hidden;
                     scrollbar-width:none; -ms-overflow-style:none; }
  span.math.inline::-webkit-scrollbar { display:none; }
  span.math.inline.math-long { max-width:100%; }
}

/* 表格 */
.table-wrap { overflow-x:auto; margin:20px 0; }
table { border-collapse:collapse; width:100%; font-size:0.92rem; }
th, td { border:1px solid var(--line); padding:8px 12px; text-align:left; white-space:normal; }
th { background:var(--th-bg); font-weight:700; }
tr:nth-child(even) td { background:var(--row-alt); }

/* 代码 */
code { background:var(--code-bg); padding:2px 6px; border-radius:4px;
       font-family:"SF Mono",Consolas,monospace; font-size:0.88em; }
pre { background:var(--pre-bg); color:var(--pre-ink); padding:16px; border-radius:8px;
      overflow-x:auto; margin:18px 0; font-size:0.88rem; line-height:1.6; }
pre code { background:transparent; color:inherit; padding:0; }
/* 非代码的“逻辑链/示意图”块：不用深色代码框，改用浅色卡片，避免黑框 */
pre:not(.sourceCode):not(.hljs) {
  background: var(--blockquote-bg);
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: 10px;
}
pre:not(.sourceCode):not(.hljs) code {
  background: transparent;
  color: inherit;
  font-family: inherit;
}
/* 代码高亮：白底主题覆盖（浅色模式） */
.hljs { background:var(--code-bg) !important; border-radius:8px; }
code.hljs, pre.hljs { padding:0; }

/* details 折叠 */
details { margin:14px 0; border:1px solid var(--line); border-radius:8px;
          background:var(--card); overflow:hidden; }
summary { cursor:pointer; padding:10px 16px; font-weight:600; color:var(--ink);
          background:var(--summary-bg); user-select:none; list-style:none; position:relative; }
summary::-webkit-details-marker { display:none; }
summary::before { content:"▸"; display:inline-block; margin-right:8px; color:var(--accent);
                  transition:transform .2s; }
details[open] summary::before { transform:rotate(90deg); }
details[open] summary { border-bottom:1px solid var(--line); }
details > *:not(summary) { padding:10px 16px; }
details > p { padding:10px 16px; }

/* 自检题旁的内嵌提示/答案（popup） */
.selfcheck-popup { margin:0.35em 0 0.65em; display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
.selfcheck-popup details { margin:0; border:1px solid var(--line); border-radius:8px; background:var(--card); }
.selfcheck-popup summary { padding:4px 10px; font-size:0.82rem; font-weight:600; border-radius:7px; display:inline-block; }
.selfcheck-popup details[open] summary { border-bottom:1px solid var(--line); border-radius:7px 7px 0 0; }
.selfcheck-popup details > *:not(summary) { padding:8px 12px; font-size:0.9rem; }
.selfcheck-popup details > p:last-child { margin-bottom:0; }

/* 图片 */
figure { margin:20px 0; text-align:center; }
figure img { max-width:100%; height:auto; border-radius:6px; }
figcaption { margin-top:6px; font-size:0.85rem; color:var(--ink-soft); }

/* 上标引用 */
sup { font-size:0.7em; color:var(--accent); }

/* 返回顶部 */
.back-top { position:fixed; right:24px; bottom:24px; width:40px; height:40px;
            border-radius:50%; background:var(--accent); color:#fff; border:none;
            font-size:1.1rem; cursor:pointer; box-shadow:0 2px 8px rgba(0,0,0,.2);
            display:none; z-index:60; }
.back-top.show { display:block; }

/* 进度条 */
.progress { position:fixed; top:0; left:0; height:3px; background:var(--accent);
            width:0; z-index:100; transition:width .1s; }

/* ===== 响应式 ===== */
@media (max-width: 1024px) {
  .layout { flex-direction:column; }
  .sidebar { width:100%; height:auto; position:relative; max-height:none;
             border-right:none; border-bottom:1px solid var(--line); padding:12px; }
  .sidebar-header { margin-bottom:6px; }
  .toc { display:none; }
  .toc.open { display:block; max-height:60vh; overflow-y:auto; }
  .sidebar-toggle { display:block; background:var(--accent); color:#fff; border:none;
                    padding:8px 14px; border-radius:6px; cursor:pointer; font-size:0.95rem;
                    margin-bottom:10px; }
  .main { padding:24px 18px 60px; }
}
@media (max-width: 640px) {
  .main { padding:16px 12px 48px; }
  .doc-title { font-size:1.5rem; }
  h2 { font-size:1.3rem; }
  .doc-section { margin-bottom:36px; }
}

/* ===== 打印样式 ===== */
@media print {
  .sidebar, .sidebar-toggle, .back-top, .progress { display:none !important; }
  .layout { display:block; }
  .main { padding:0; max-width:100%; }
  .doc-section { max-width:100%; margin:0 0 30px; page-break-after:always; }
  .doc-section:last-child { page-break-after:auto; }
  details { border:none; margin:8px 0; }
  details > *:not(summary) { padding:0; }
  details[open] summary { border-bottom:none; }
  pre { white-space:pre-wrap; word-break:break-all; }
  .math.display, span.math.inline { overflow:visible !important; white-space:normal !important; }
  a { color:var(--ink); text-decoration:none; }
  figure { page-break-inside:avoid; }
  table { font-size:0.8rem; }
  h2, h3, h4 { page-break-after:avoid; }
}
</style>
</head>
<body>
<div class="progress" id="progress"></div>
<div class="layout">
  <aside class="sidebar">
    <div class="sidebar-header">📚 目录 <span class="brand">· AI 四篇合集</span></div>
    <button class="sidebar-toggle" id="tocToggle">☰ 目录</button>
    <div class="doc-switch">
      <button class="doc-btn" data-doc="doc-1">AI数学</button>
      <button class="doc-btn" data-doc="doc-2">基座</button>
      <button class="doc-btn" data-doc="doc-3">用好AI</button>
      <button class="doc-btn" data-doc="doc-4">扩散</button>
    </div>
    <div class="search-box">
      <input type="search" id="searchInput" placeholder="🔍 搜索标题…" autocomplete="off">
    </div>
    <nav class="toc" id="toc"></nav>
  </aside>
  <main class="main">
{{BODY}}
  </main>
</div>
<button class="back-top" id="backTop" title="回到顶部">↑</button>

<script>
/* ===== 构建目录 ===== */
(function () {
  const toc = document.getElementById('toc');
  const sections = document.querySelectorAll('.doc-section');
  const docBtns = document.querySelectorAll('.doc-btn');

  sections.forEach(function (sec) {
    const title = sec.dataset.title;
    // 文档级标题
    const headLi = document.createElement('li');
    headLi.className = 'doc-head';
    const headA = document.createElement('a');
    headA.href = '#' + sec.id;
    headA.textContent = title;
    headLi.appendChild(headA);
    toc.appendChild(headLi);

    // 章节标题（h2 = 原 h1, h3 = 原 h2, h4 = 原 h3）
    // 按章分组：h2 是章，其下 h3/h4 是节的子项
    let currentChapter = null;   // 当前章的 <li>（h2 容器）
    let currentChapterList = null; // 当前章的子项 <ul>
    sec.querySelectorAll('h2, h3, h4').forEach(function (h) {
      if (h.classList.contains('doc-title')) return; // 跳过文档大标题
      if (h.textContent.trim() === title) return;   // 跳过与文档标题重复的内部 h1
      if ((h.dataset.label || '').trim() === '目录') return; // 跳过文档内部"目录"章
      const id = h.id;
      if (!id) return;
      const a = document.createElement('a');
      a.href = '#' + id;
      // 标题文本：优先用构建端注入的 data-label（KaTeX 渲染前的干净文本）
      a.textContent = h.dataset.label || h.textContent;
      if (h.tagName === 'H2') {
        // 新章：创建组容器（默认收起）
        currentChapter = document.createElement('li');
        currentChapter.className = 'toc-chapter';
        const headWrapper = document.createElement('div');
        headWrapper.className = 'toc-chapter-head';
        headWrapper.appendChild(a);
        currentChapter.appendChild(headWrapper);
        currentChapterList = document.createElement('ul');
        currentChapterList.className = 'toc-children';
        currentChapter.appendChild(currentChapterList);
        toc.appendChild(currentChapter);
        // 点击章名 toggle 展开/收起（不跳转，避免误导航）
        // 注意：用局部变量捕获当前章，避免闭包引用外层最终值
        (function (chapter) {
          headWrapper.addEventListener('click', function (e) {
            e.preventDefault();
            chapter.classList.toggle('open');
          });
        })(currentChapter);
      } else {
        // h3/h4：挂到当前章的子列表
        if (!currentChapterList) {
          // 章前的小节（理论不会发生，兜底直接挂 toc）
          const orphanLi = document.createElement('li');
          orphanLi.className = 'lvl-' + h.tagName.toLowerCase();
          orphanLi.appendChild(a);
          toc.appendChild(orphanLi);
          return;
        }
        const li = document.createElement('li');
        li.className = 'lvl-' + h.tagName.toLowerCase();
        li.appendChild(a);
        currentChapterList.appendChild(li);
      }
    });
  });

  /* ===== 滚动高亮（IntersectionObserver） ===== */
  const links = toc.querySelectorAll('a');
  const map = new Map();
  links.forEach(function (a) {
    const id = a.getAttribute('href').slice(1);
    const el = document.getElementById(id);
    if (el) map.set(el, a);
  });

  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        links.forEach(function (a) { a.classList.remove('active'); });
        const a = map.get(entry.target);
        if (a) a.classList.add('active');
        // 自动展开当前章（收起其他章）——动态层次随阅读位置变化
        const chapter = a && a.closest('.toc-chapter');
        if (chapter) {
          toc.querySelectorAll('.toc-chapter').forEach(function (c) {
            c.classList.toggle('open', c === chapter);
          });
        }
        // 联动文档切换按钮
        const sec = entry.target.closest('.doc-section');
        if (sec) {
          docBtns.forEach(function (b) {
            b.classList.toggle('active', b.dataset.doc === sec.id);
          });
        }
      }
    });
  }, { rootMargin: '-10% 0px -70% 0px' });

  map.forEach(function (a, el) { observer.observe(el); });

  /* ===== 平滑滚动（保留浏览器行为，只做移动端目录收起） ===== */
  document.getElementById('tocToggle').addEventListener('click', function () {
    toc.classList.toggle('open');
  });
  links.forEach(function (a) {
    a.addEventListener('click', function () {
      if (window.innerWidth <= 1024) toc.classList.remove('open');
    });
  });

  /* ===== 文档切换 ===== */
  docBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      const id = btn.dataset.doc;
      const sec = document.getElementById(id);
      if (sec) sec.scrollIntoView({ behavior: 'smooth' });
      docBtns.forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      if (window.innerWidth <= 1024) toc.classList.remove('open');
    });
  });

  /* ===== 搜索（过滤 TOC 标题） ===== */
  const searchInput = document.getElementById('searchInput');
  const allTocItems = toc.querySelectorAll('li');
  searchInput.addEventListener('input', function () {
    const q = searchInput.value.trim().toLowerCase();
    // 先收集原始结构（doc-head 始终显示，章节按匹配过滤）
    let matched = 0;
    allTocItems.forEach(function (li) {
      if (li.classList.contains('doc-head')) return; // 文档头始终显示
      const txt = li.textContent.toLowerCase();
      const show = !q || txt.includes(q);
      li.style.display = show ? '' : 'none';
      if (show) matched++;
    });
    // 搜索时展开所有含匹配的章（否则结果被折叠隐藏）
    if (q) {
      toc.querySelectorAll('.toc-chapter').forEach(function (c) {
        const hasMatch = c.querySelectorAll('li').length > 0 &&
          [...c.querySelectorAll('li')].some(function (li) { return li.style.display !== 'none'; });
        c.classList.toggle('open', hasMatch);
      });
    }
    // 无匹配提示
    let hint = document.getElementById('searchHint');
    if (!hint) {
      hint = document.createElement('div');
      hint.id = 'searchHint';
      hint.style.cssText = 'padding:8px 10px;color:var(--ink-soft);font-size:0.82rem;';
      toc.appendChild(hint);
    }
    hint.style.display = q && matched === 0 ? '' : 'none';
    hint.textContent = '无匹配标题';
    // 窄屏时显示结果
    if (q && window.innerWidth <= 1024) toc.classList.add('open');
  });

  /* ===== 返回顶部 + 进度条 ===== */
  const backTop = document.getElementById('backTop');
  const progress = document.getElementById('progress');
  let scrollTicking = false;
  let docScrollRange = 0;
  function updateDocScrollRange() {
    docScrollRange = document.documentElement.scrollHeight - window.innerHeight;
  }
  function updateScrollUI() {
    const st = window.scrollY;
    backTop.classList.toggle('show', st > 600);
    progress.style.width = (docScrollRange > 0 ? (st / docScrollRange) * 100 : 0) + '%';
    scrollTicking = false;
  }
  updateDocScrollRange();
  window.addEventListener('resize', updateDocScrollRange);
  window.addEventListener('load', updateDocScrollRange);
  window.addEventListener('scroll', function () {
    if (!scrollTicking) {
      requestAnimationFrame(updateScrollUI);
      scrollTicking = true;
    }
  }, { passive: true });
  backTop.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'smooth' }); });
})();

/* ===== 代码高亮 ===== */
(function () {
  if (window.hljs) { hljs.highlightAll(); }
})();

/* ===== KaTeX 渲染（同步脚本已就绪，直接执行） ===== */
(function () {
  if (window.renderMathInElement) {
    renderMathInElement(document.body, {
      delimiters: [
        { left: '\\(', right: '\\)', display: false },
        { left: '\\[', right: '\\]', display: true }
      ],
      output: 'html',
      ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
      throwOnError: false
    });
  }
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()