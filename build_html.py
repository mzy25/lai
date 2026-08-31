#!/usr/bin/env python3
r"""把五篇技术文档 md 合体构建为单个响应式 HTML（动态侧边目录 + KaTeX 公式）。

用法:
    python3 build_html.py [--out html/index.html]

每篇处理流水线（render_doc）:
    1. 自检附录数据抽取（转交互弹窗）与自检区裁剪/保留
    2. pandoc 转 HTML（--mathjax 输出 LaTeX 定界符供 KaTeX 渲染）
    3. md_links 内链修复：目录锚点改写为 pandoc 实际 id
    4. 标题 id/href 加 doc-N- 前缀防跨篇冲突；标题层级 +1（H1→H2 等）
    5. 表格包裹、长公式标记、图片路径与加载方式修正
    6. 包进 section.doc-section，并按章包裹

最后合并 body 注入模板（CSS/JS/KaTeX），自检五篇齐全后写出。
"""
import argparse
import re
import subprocess
import shutil
import tempfile
from pathlib import Path

import html as html_mod

import md_links

# pandoc reader 参数：harvest（md_links）与真实转换共用，保证标题 id 一字不差
FROM_FLAGS = md_links.FROM_FLAGS

NL = chr(10)  # 行分隔符（模板/正文拼接用）

ROOT = Path(__file__).resolve().parent
HTML_DIR = ROOT / "html"
FIG_SRC = [ROOT / "1_ai_math" / "figures", ROOT / "2_foundation" / "figures",
           ROOT / "3_use_ai" / "figures", ROOT / "1a_diffusion" / "figures",
           ROOT / "4_ai_law" / "figures"]

# 五篇：(md路径相对ROOT, 显示标题, doc-id)
DOC_LABELS = ["AI数学", "基座", "用好AI", "扩散", "AI law"]

DOCS = [
    ("1_ai_math/AI数学_从起步到前沿.md", "AI数学：从起步到前沿", "doc-1"),
    ("2_foundation/基座模型_从咿呀到行动.md", "基座模型：从咿呀到行动", "doc-2"),
    ("3_use_ai/用好AI_从有用到好用.md", "用好AI：从有用到好用", "doc-3"),
    ("1a_diffusion/扩散_从噪声生成.md", "扩散：从噪声生成", "doc-4"),
    ("4_ai_law/AI_law_从现象到规律.md", "AI law：从现象到规律", "doc-5"),
]

# 图片重名冲突：不同子目录可能有同名 fig_*.png
FIG_PREFIX = {
    "1_ai_math": "aimath",
    "1a_diffusion": "diff",
    "2_foundation": "base",
    "3_use_ai": "use",
    "4_ai_law": "ailaw",
}

# 篇目录 → 书名简称（正文跨篇引用写法）
BOOK_ALIAS = {
    "1_ai_math": "AI数学",
    "1a_diffusion": "扩散",
    "2_foundation": "基座模型",
    "3_use_ai": "用好AI",
    "4_ai_law": "AI law",
}

# 跨篇引用索引：{书名: {编号(normalized): 目标标题 id}}
HEADING_INDEX = {}


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


def pandoc_to_html(md_text: str, cwd: Path) -> str:
    """单篇 md → HTML 片段（pandoc）。用 tempfile 避免残留临时文件。"""
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
    "# 附录：自检问题与答案",
]

SELFCHECK_END_MARKERS = [
    "# 附录：逻辑链",
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

        text = text[:start] + connection + '\n' + tail

    return text


def remove_selfcheck_toc_refs(text: str) -> str:
    """移除/清理 HTML 中指向已删除自检附录的目录项，保留源 md 的完整目录。"""
    lines = text.splitlines(keepends=True)
    out = []
    for line in lines:
        stripped = line.strip()
        # 独立的自检附录目录项：HTML 中该附录已被移除（转为交互弹窗），
        # 指向它的链接必然是死链——按链接目标匹配，不依赖箭头等文案细节。
        if "#附录自检问题与答案" in stripped:
            continue
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
            sm = re.search(r'<summary>\s*(.*?)\s*</summary>', tok, re.S)
            summary = sm.group(1).strip() if sm else ""
            cm = None
            if current is None and sm:
                cm = re.match(r'(?:Ch\s*(\d+)|第\s*(\d+)\s*章)\s*(提示|答案|解析)', summary)
            if cm:
                # ai-law 风格：无 h3 的整章答案折叠（ChN 答案/提示）→ 按章收录
                idx = int(cm.group(1) or cm.group(2)) - 1
                while len(chapters) <= idx:
                    chapters.append({'heading': 'Ch%d' % (len(chapters) + 1), 'questions': [], 'group_details': []})
                detail_content = tok[sm.end():-len('</details>')].strip() if sm else tok
                items = extract_top_level_lis(detail_content)
                key = 'numbered_hints' if cm.group(3) == '提示' else 'numbered_answers'
                chapters[idx].setdefault(key, []).extend(items)
                continue
            content = tok[sm.end():-len('</details>')].strip() if sm else tok
            if current is None:
                continue
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
    appendix_html = pandoc_to_html(segment, cwd)
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
                insert_at = slot["end"]
                insertions.append((region_start + insert_at, popup))
        elif chapter.get("numbered_answers") or chapter.get("numbered_hints"):
            # ai-law 风格：题目与答案两侧各 1..N 同序，按位置配对（题目经 <ol start> 全局编号）
            answers = chapter.get("numbered_answers") or []
            hints = chapter.get("numbered_hints") or []
            for j, slot in enumerate(slots):
                ans_html = answers[j] if j < len(answers) else None
                hint_html = hints[j] if j < len(hints) else None
                popup = make_popup(hint_html, ans_html)
                if popup:
                    insertions.append((region_start + slot["end"], popup))
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
                        insert_at = slot["end"]
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

def copy_figures() -> int:
    """把各篇 figures/*.png 复制到 html/figures/（按篇加前缀防重名）。

    先清空旧图，避免源图删除后残留。
    """
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
    return copied


def prefix_code_block_ids(html: str, doc_id: str) -> str:
    """代码块行号 id 加 doc 前缀：pandoc 每篇都从 cb1 开始，合并后 id 会撞车。"""
    html = re.sub(r'id="(cb[0-9][^"]*)"', lambda m: f'id="{doc_id}-{m.group(1)}"', html)
    return re.sub(r'href="#(cb[0-9][^"]*)"', lambda m: f'href="#{doc_id}-{m.group(1)}"', html)


def prefix_internal_hrefs(html: str, doc_id: str, id_set) -> str:
    """内链 href 回写 doc 前缀（fix_internal_links 已把锚点改成 pandoc 实际 id）。

    仅替换 id_set 中的精确匹配；不在集合里的 href 原样保留。
    注意：不 unescape 公式实体！pandoc 输出 &lt; &gt; &amp; 是安全 HTML 实体，
    DOM textContent 会转回 < > &，KaTeX 读取时得到正确字符；
    若还原成裸 < 会破坏 HTML 解析。
    """
    return re.sub(
        r'href="#([^"]+)"',
        lambda m: f'href="#{doc_id}-{m.group(1)}"' if m.group(1) in id_set else m.group(0),
        html)


def wrap_tables(html: str) -> str:
    """表格包 .table-wrap（移动端横向滚动）。"""
    html = re.sub(r'(<table[^>]*>)', r'<div class="table-wrap">\1', html)
    return re.sub(r'(</table>)', r'\1</div>', html)


def mark_long_math(html: str) -> str:
    """超长行内公式（>80 字符）标记 math-long，允许换行避免横向滚动。"""
    return re.sub(r'<span class="math inline">([^<]{80,}?)</span>',
                  r'<span class="math inline math-long">\1</span>', html)


def _png_dims(path: Path):
    """读取 PNG 宽高（IHDR），失败返回 None。用于懒加载预占位，避免锚点跳转错位。"""
    try:
        with open(path, "rb") as f:
            head = f.read(26)
        if head[:8] != b'\x89PNG\r\n\x1a\n' or head[12:16] != b'IHDR':
            return None
        import struct
        w, h = struct.unpack('>II', head[16:24])
        return w, h
    except Exception:
        return None


def fix_image_tags(html: str, fig_prefix: str) -> str:
    """修图片路径（pandoc 输出 src="figures/xxx"）并加篇名前缀。

    懒加载 + 宽高预占位：构建期把 PNG 真实宽高写入 width/height，
    浏览器据属性预留等比空间，懒加载不再引发布局抖动，
    锚点跳转（侧边目录）不会错位。
    """
    def _img_repl(m):
        src = m.group(1)
        rest = m.group(2)  # 含 alt；可能以 "/" 结尾（pandoc 的 /> 被换行拆开）
        rest = re.sub(r'/?\s*$', '', rest)
        attrs = ' loading="lazy" decoding="async"'
        dim = _png_dims(HTML_DIR / "figures" / f"{fig_prefix}_{src}")
        if dim:
            attrs += f' width="{dim[0]}" height="{dim[1]}"'
        return f'<img src="figures/{fig_prefix}_{src}"{rest}{attrs} />'
    return re.sub(r'<img src="figures/([^"]*)"([^><]*)>', _img_repl, html)


def index_headings(html_frag: str, book: str) -> None:
    """收集 doc 前缀标题的编号 → id 映射（供跨篇引用跳转）。"""
    pat = re.compile(r'<h[2-6][^>]*?id="([^"]+)"[^>]*?data-label="([^"]*)"')
    for m in pat.finditer(html_frag):
        hid, label = m.group(1), html_mod.unescape(m.group(2)).strip()
        key = None
        cm = re.match(r'第\s*(\d+)\s*章', label)
        if cm:
            key = cm.group(1)
        else:
            sm = re.match(r'(\d{1,2}(?:\.\d{1,3})*)', label)
            if sm and sm.group(1) != label.lstrip('0'):
                key = sm.group(1)
        if key:
            HEADING_INDEX.setdefault(book, {})[key] = hid


_XREF_PAT = re.compile(
    r'《(AI数学|扩散|基座模型|用好AI|AI law)》\s*([§]?\s*\d{1,2}(?:\.\d{1,3})*|第\s*\d+\s*章)'
)


def rewrite_cross_refs(body: str) -> str:
    """把正文跨篇引用《书名》§X.Y / 第X章 改成可点击跳转链接（只处理文本节点）。"""
    def repl(m):
        book, num = m.group(1), m.group(2)
        cm = re.match(r'第\s*(\d+)\s*章', num)
        if cm:
            key = cm.group(1)
        else:
            key = re.sub(r'[\s§]', '', num)
        target = HEADING_INDEX.get(book, {}).get(key)
        if not target:
            return m.group(0)
        return f'<a class="xref" href="#{target}">{m.group(0)}</a>'

    parts = re.split(r'(<[^>]*>)', body)
    out = []
    for part in parts:
        if part.startswith("<") and part.endswith(">"):
            out.append(part)
        else:
            out.append(_XREF_PAT.sub(repl, part))
    return "".join(out)


def render_doc(md_rel: str, title: str, doc_id: str) -> str:
    """单篇 md → doc-section 块 HTML（完整流水线）。"""
    md_path = ROOT / md_rel
    fig_prefix = FIG_PREFIX[md_rel.split("/")[0]]

    text = md_path.read_text(encoding="utf-8")
    qa_data = extract_selfcheck_data(text, md_path.parent)
    text = remove_selfcheck_appendix(text)
    text = remove_selfcheck_toc_refs(text)
    text = preprocess_md(text)
    text, link_warnings, id_set = md_links.fix_internal_links(
        text, md_path.parent, FROM_FLAGS)
    for w in link_warnings:
        print(f"⚠ {md_rel}: {w}")

    html = pandoc_to_html(text, md_path.parent)
    html = bump_headings(html, doc_id)
    index_headings(html, BOOK_ALIAS[md_rel.split("/")[0]])
    html = inject_selfcheck_popups(html, qa_data)
    html = prefix_code_block_ids(html, doc_id)
    html = prefix_internal_hrefs(html, doc_id, id_set)
    html = wrap_tables(html)
    html = mark_long_math(html)
    html = fix_image_tags(html, fig_prefix)
    html = remove_doc_title_heading(html, title)
    html = wrap_chapters(html)

    section = f'<section class="doc-section" id="{doc_id}" data-title="{title}">\n'
    section += f'<h1 class="doc-title" id="{doc_id}-title">{title}</h1>\n'
    section += html
    section += "</section>"
    print(f"✓ {md_rel} → HTML ({len(html)} chars)")
    return section

def main():
    ap = argparse.ArgumentParser(description="构建 AI 五篇合集单页 HTML")
    ap.add_argument("--out", default=str(HTML_DIR / "index.html"),
                    help="输出文件路径（默认 html/index.html）")
    args = ap.parse_args()

    HTML_DIR.mkdir(exist_ok=True)
    (HTML_DIR / "figures").mkdir(exist_ok=True)

    ensure_frontend_assets()
    copy_figures()

    sections = [render_doc(md_rel, title, doc_id) for md_rel, title, doc_id in DOCS]
    body = "\n".join(sections)
    body = rewrite_cross_refs(body)

    # 自检：五篇全部产出才算成功
    for _, _, doc_id in DOCS:
        if f'id="{doc_id}"' not in body:
            raise RuntimeError(f"构建结果缺少文档 {doc_id}，请检查 pandoc 输出")

    doc_btns = NL.join(
        f'      <button class="doc-btn" data-doc="{doc_id}">{label}</button>'
        for (_, _, doc_id), label in zip(DOCS, DOC_LABELS)
    )
    import json as _json
    import pathlib as _pl
    _glossary = _json.dumps(
        _json.loads((_pl.Path(__file__).resolve().parent / "tools" / "glossary.json").read_text(encoding="utf-8"))["terms"],
        ensure_ascii=False)
    html_out = (
        TEMPLATE.replace("{{BODY}}", body)
                .replace("{{DOC_BTNS}}", doc_btns)
                .replace("{{GLOSSARY}}", _glossary)
    )
    out = Path(args.out)
    out.write_text(html_out, encoding="utf-8")
    print(f"✓ 输出 {out} ({out.stat().st_size/1024:.0f} KB)")


def _load_template() -> str:
    """读取页面模板（与构建脚本分离的 template.html）。"""
    path = ROOT / "template.html"
    if not path.exists():
        raise RuntimeError(f"缺少模板文件：{path}")
    return path.read_text(encoding="utf-8")


TEMPLATE = _load_template()

if __name__ == "__main__":
    main()