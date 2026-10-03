#!/usr/bin/env python3
r"""把五篇技术文档 md 合体构建为单个响应式 HTML（动态侧边目录 + KaTeX 公式）。

用法:
    python3 build/build_html.py [--out html/index.html]

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
import mdprep
import lint_md
import check_html
import books
import template_common as tc
import selfcheck

# pandoc reader 参数：harvest（md_links）与真实转换共用，保证标题 id 一字不差
FROM_FLAGS = md_links.FROM_FLAGS

NL = chr(10)  # 行分隔符（模板/正文拼接用）

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
HTML_DIR = ROOT / "html"
FIG_SRC = [b.fig_dir for b in books.BOOKS]

# 五篇：(md路径相对ROOT, 显示标题, doc-id)；常量从 books 注册表派生
DOC_LABELS = [b.label for b in books.BOOKS]

DOCS = [(b.md_rel, b.title, b.doc_id) for b in books.BOOKS]

# 图片重名冲突：不同子目录可能有同名 fig_*.png
FIG_PREFIX = {b.key: b.fig_prefix for b in books.BOOKS}

# 篇目录 → 书名简称（正文跨篇引用写法）
BOOK_ALIAS = {b.key: b.alias for b in books.BOOKS}

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
    """构建端预处理：块分隔空行保证 + 分隔符规范化（见 mdprep 模块）＋
    非标题行的行尾稳定 ID 剥离（题目 `{#q-…}` 会被 pandoc 当字面文本渲染）。"""
    return mdprep.prepare(mdprep.strip_nonheading_ids(text))


def pandoc_to_html(md_text: str, cwd: Path) -> str:
    """单篇 md → HTML 片段（pandoc）。用 tempfile 避免残留临时文件。"""
    md_text = md_links.normalize_citations(md_text)
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



def find_selfcheck_span(text: str):
    """返回自检附录在 md 中的 [start, end)；找不到返回 None。

    区间 = 自检附录 H1 到下一个 H1（围栏感知）。自检之后的附录
    （扩展题/动手路径/逻辑链/参考文献等）天然在区间之外，按正文章节保留。
    """
    return selfcheck._selfcheck_span_range(text)


def remove_selfcheck_appendix(text: str) -> str:
    """从 md 中移除独立的“自检问题与答案”附录；保留其后的附录与收束内容。"""
    span = find_selfcheck_span(text)
    if span is None:
        return text
    start, end = span
    removed = text[start:end]

    # “把知识连成网”属于附录收束内容（连线条目），移到移除位原位保留。
    conn = re.search(
        r'<details>\s*<summary>\s*把知识连成网.*?</details>',
        removed,
        re.S,
    )
    connection = conn.group(0) if conn else ""

    return text[:start] + connection + ('\n' if connection else '') + text[end:]


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
        r'<p>Q(\d+).*?</p>|'
        r'Q(\d+)\.[^<\n]*|'
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
        elif tok.startswith('<strong>Q') or re.match(r'<p>Q\d', tok) or re.match(r'Q\d+\.', tok):
            if current is None:
                continue
            qm = (re.match(r'<strong>Q(\d+)', tok)
                  or re.match(r'<p>Q(\d+)', tok)
                  or re.match(r'Q(\d+)\.', tok))
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
    for m in re.finditer(r'<p><strong>\s*(\d+)(?:（[^）]*）)?\s*[.、．]', region):  # 题号可带（标签）：**4（反事实・边界情况）.**
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


CIRCLED_DIGITS = '①②③④⑤⑥⑦⑧⑨⑩'
# 答案中受控的自评引导语：出现即独立成段
SELFASSESS_LEADINS = ('你的答案至少应包含', '核对你的答案', '自评标准：')
# 拆分点：圈码编号项或受控引导语之前（由常量统一生成，避免两处脱节）
_BUBBLE_SPLIT_RE = re.compile(
    '(?=[%s]|%s)' % (CIRCLED_DIGITS, '|'.join(re.escape(x) for x in SELFASSESS_LEADINS))
)


def _tags_balanced(fragment):
    """段内常用行内标签开闭是否配对（防拆段把标签拦腰截断）。"""
    for t in ('strong', 'em', 'code', 'a', 'span', 'b', 'i', 'sub', 'sup'):
        if len(re.findall(rf'<{t}\b', fragment)) != len(re.findall(rf'</{t}>', fragment)):
            return False
    return True


def beautify_bubble(html):
    """气泡内容可读性排版：裸文本补 <p>；①②③… 编号项与自评引导语拆为独立段落。
    任一段拆出后标签不配对则整段放弃拆分（保内容正确，退化为原样）。"""
    if not html:
        return html
    s = html.strip()
    if not re.match(r'<(p|ul|ol|div|h[1-6]|blockquote|table)\b', s):
        s = f'<p>{s}</p>'

    def split_enum(m):
        inner = m.group(1)
        if not any(c in inner for c in CIRCLED_DIGITS) and not any(
            lead in inner for lead in SELFASSESS_LEADINS
        ):
            return m.group(0)
        parts = [p.strip() for p in _BUBBLE_SPLIT_RE.split(inner) if p.strip()]
        if not all(_tags_balanced(p) for p in parts):
            return m.group(0)
        return ''.join(f'<p>{p}</p>' for p in parts)

    return re.sub(r'<p>(.*?)</p>', split_enum, s, flags=re.S)


_EXT_QA_RE = re.compile(
    r'(<p>(?:<strong>)?Q\d+\..*?(?:</strong>)?</p>)\s*'
    r'<details>\s*<summary>\s*卡住再看提示\s*</summary>(?P<hint>.*?)</details>\s*'
    r'<details>\s*<summary>\s*答案\s*</summary>(?P<answer>.*?)</details>',
    re.S,
)


def convert_extended_popups(html: str) -> str:
    """把“扩展题”区的 details 提示/答案转成与其余自检一致的弹出按钮。"""
    m = re.search(r'<h[1-6][^>]*data-label="[^"]*扩展题"[^>]*>.*?</h[1-6]>', html)
    if not m:
        return html
    start = m.end()
    nxt = re.search(r'<h[1-6]\b', html[start:])
    end = start + nxt.start() if nxt else len(html)

    def repl(qm):
        popup = make_popup(qm.group("hint").strip(), qm.group("answer").strip())
        return qm.group(1) + popup

    return html[:start] + _EXT_QA_RE.sub(repl, html[start:end]) + html[end:]


def make_popup(hint_html, answer_html):
    """生成题旁的提示/答案按住浮现块（按住看，松开消失）。"""
    if not hint_html and not answer_html:
        return ""
    parts = ['<span class="selfcheck-popup">']
    if hint_html:
        parts.append(f'<button type="button" class="selfcheck-btn selfcheck-hint" aria-expanded="false">提示</button>'
                     f'<span class="selfcheck-bubble" hidden>{beautify_bubble(hint_html)}</span>')
    if answer_html:
        parts.append(f'<button type="button" class="selfcheck-btn selfcheck-answer" aria-expanded="false">答案</button>'
                     f'<span class="selfcheck-bubble" hidden>{beautify_bubble(answer_html)}</span>')
    parts.append('</span>')
    return "".join(parts)


def pair_questions(chapter, slots):
    """按组内出现顺序把题槽与 Q&A 配对（不依赖编号风格：正文可能跨组连续编号）。

    两侧顺序同源（正文题序与附录题序一致，由 selfcheck 守恒校验兜底），
    因此组内逐位配对比编号配对更稳；编号漂移由 lint 的 number-mismatch 监控。
    """
    questions = chapter.get("questions", [])
    by_group = {}
    for q in questions:
        by_group.setdefault(q.get("group"), []).append(q)
    used = {}
    pairs = []
    for slot in slots:
        g = slot.get("group")
        pool = by_group.get(g)
        if pool is None:
            pool = by_group.get(None, [])
        i = used.get(g, 0)
        if i < len(pool):
            pairs.append((slot, pool[i]))
            used[g] = i + 1
    return pairs


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
        if not chapter.get("questions"):
            continue
        pairs = pair_questions(chapter, slots)
        if len(pairs) != len(slots):
            raise RuntimeError(
                f"自检配对不完整（第 {idx + 1} 区）：题槽 {len(slots)}，配对 {len(pairs)}")
        for slot, q in pairs:
            popup = make_popup(q.get("hint"), q.get("answer"))
            if not popup:
                continue
            insert_at = slot["end"]
            insertions.append((region_start + insert_at, popup))
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
        attrs += f' data-label="{html_mod.escape(label, quote=True)}"'
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

KATEX_NEEDED = ["katex.min.css", "katex.min.js", "contrib/auto-render.min.js"]
KATEX_UNUSED = ["katex.js", "katex.mjs", "katex.css", "README.md"]


def _katex_ready(dst: Path) -> bool:
    version = (dst / "VERSION")
    if not version.exists() or version.read_text(encoding="utf-8").strip() != KATEX_VERSION:
        return False
    return all((dst / f).exists() for f in KATEX_NEEDED) and (dst / "fonts").is_dir()


def _copy_katex_assets(src: Path, dst: Path) -> None:
    """只复制页面实际加载的文件（min.css/js + auto-render + fonts），并写版本戳。"""
    dst.mkdir(parents=True, exist_ok=True)
    for f in ("katex.min.css", "katex.min.js"):
        shutil.copy2(src / f, dst / f)
    contrib = src / "contrib"
    (dst / "contrib").mkdir(exist_ok=True)
    shutil.copy2(contrib / "auto-render.min.js", dst / "contrib" / "auto-render.min.js")
    fonts_src, fonts_dst = src / "fonts", dst / "fonts"
    if fonts_src.is_dir():
        shutil.copytree(fonts_src, fonts_dst, dirs_exist_ok=True)
    for name in KATEX_UNUSED:                      # 历史整包复制的冗余文件
        (dst / name).unlink(missing_ok=True)
    (dst / "VERSION").write_text(KATEX_VERSION + "\n", encoding="utf-8")


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

    # 目标缺失或版本过期且本地无源时，用 npm 自动安装
    missing_packages = []
    if not _katex_ready(katex_dst) and not any(p.exists() for p in katex_candidates):
        missing_packages.append(f"katex@{KATEX_VERSION}")
    if not (hljs_dst / "highlight.min.js").exists() and not any(p.exists() for p in hljs_candidates):
        missing_packages.append(f"@highlightjs/cdn-assets@{HLJS_VERSION}")
    if missing_packages:
        _npm_install(missing_packages)

    if _katex_ready(katex_dst):
        print(f"✓ KaTeX 已存在且版本匹配（{KATEX_VERSION}），跳过复制")
    else:
        katex_src = next((p for p in katex_candidates if p.exists()), None)
        if katex_src is None:
            raise RuntimeError("KaTeX 源不可用，无法生成完整 HTML。请检查 npm 安装或恢复 vendor/。")
        _copy_katex_assets(katex_src, katex_dst)
        print(f"✓ 复制 KaTeX {KATEX_VERSION} 到 html/katex/（仅所需文件）")

    # 复制 highlight.js（代码高亮，本地化）
    if (hljs_dst / "highlight.min.js").exists():
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
    return re.sub(r'<img src="(?:\./)?figures/([^"]*)"([^><]*)>', _img_repl, html)


def wrap_takeaways(html: str) -> str:
    """本章回顾 → 要点卡（自检题区留在卡片之外，避免卡片吞掉交互题）。"""
    pattern = re.compile(
        r'(<h3\b[^>]*data-label="[^"]*本章回顾"[^>]*>.*?</h3>)(.*?)(?=<h[23]\b|\Z)',
        re.S)
    marker = '<p><strong>本章自检</strong>'

    def repl(m):
        content = m.group(2)
        cut = content.find(marker)
        if cut == -1:
            return f'<section class="takeaway">{m.group(1)}{content}</section>'
        return (f'<section class="takeaway">{m.group(1)}{content[:cut]}</section>'
                + content[cut:])

    return pattern.sub(repl, html)


def wrap_callouts(html: str) -> str:
    """阅读型 callout：本章回顾 → 要点卡。"""
    html = wrap_takeaways(html)
    return html


def index_headings(html_frag: str, book: str) -> None:
    """收集 doc 前缀标题的编号 → id 映射（供跨篇引用跳转）。"""
    pat = re.compile(r'<h[2-6][^>]*?id="([^"]+)"[^>]*?data-label="([^"]*)"')
    for m in pat.finditer(html_frag):
        hid, label = m.group(1), html_mod.unescape(m.group(2)).strip()
        key = None
        cm = re.match(r'(?:[▽◇○◌]\s*)?第\s*(\d+)\s*章', label)
        if cm:
            key = cm.group(1)
        else:
            sm = re.match(r'(?:[▽◇○◌]\s*)?(\d{1,2}(?:\.\d{1,3})*)', label)
            if sm and sm.group(1) != label.lstrip('0'):
                key = sm.group(1)
        if key:
            HEADING_INDEX.setdefault(book, {})[key] = hid


_XREF_PAT = re.compile(
    r'《(AI数学|扩散|基座模型|用好AI|AI规律)》\s*([§]?\s*\d{1,2}(?:\.\d{1,3})*|第\s*\d+\s*章)'
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


def reading_stats(md_text: str) -> str:
    """构建端估算篇幅与阅读时长（去代码/公式/标记后的正文字符数，约 350 字/分钟）。"""
    s = re.sub(r'\s*\{#[^}\s]+\}', '', md_text)      # 稳定 ID 不是正文（编号方案三件套）
    s = re.sub(r'```.*?```', '', s, flags=re.S)
    s = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', s)
    s = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', s)
    s = re.sub(r'\$\$.*?\$\$', '', s, flags=re.S)
    s = re.sub(r'\$[^$\n]*\$', '', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub(r'[#>*_`|~\-\s〔〕]', '', s)   # 〔〕 是绑定的机器标点，不算篇幅
    n = len(s)
    mins = max(1, round(n / 350))
    amount = f'{n/10000:.1f} 万字' if n >= 10000 else f'{n} 字'
    return f'全文约 {amount} · 阅读约 {mins} 分钟'


def render_doc(md_rel: str, title: str, doc_id: str) -> str:
    """单篇 md → doc-section 块 HTML（完整流水线）。"""
    md_path = ROOT / md_rel
    fig_prefix = FIG_PREFIX[md_rel.split("/")[0]]

    text = md_path.read_text(encoding="utf-8")
    meta_line = reading_stats(text)
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
    html = convert_extended_popups(html)
    html = prefix_code_block_ids(html, doc_id)
    html = prefix_internal_hrefs(html, doc_id, id_set)
    html = wrap_tables(html)
    html = mark_long_math(html)
    html = fix_image_tags(html, fig_prefix)
    html = remove_doc_title_heading(html, title)
    html = wrap_callouts(html)
    html = wrap_chapters(html)

    section = f'<section class="doc-section" id="{doc_id}" data-title="{title}">\n'
    section += f'<h1 class="doc-title" id="{doc_id}-title">{title}</h1>\n'
    section += f'<p class="doc-meta">{meta_line}</p>\n'
    section += html
    section += "</section>"
    print(f"✓ {md_rel} → HTML ({len(html)} chars)")
    return section

def main():
    ap = argparse.ArgumentParser(description="构建 AI 五篇合集单页 HTML")
    ap.add_argument("--out", default=str(HTML_DIR / "index.html"),
                    help="输出文件路径（默认 html/index.html）")
    ap.add_argument("--no-lint", action="store_true",
                    help="跳过 md 结构 lint（仅应急用）")
    ap.add_argument("--no-verify", action="store_true",
                    help="跳过产物校验（仅应急用）")
    args = ap.parse_args()

    if not args.no_lint:
        findings = lint_md.lint_paths([md_rel for md_rel, _, _ in DOCS])
        if lint_md.report(findings):
            raise SystemExit("md 结构 lint 未通过；修复源稿后重试（或 --no-lint）")

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
    _glossary = _json.dumps(
        _json.loads((HERE / "glossary.json").read_text(encoding="utf-8"))["terms"],
        ensure_ascii=False)
    html_out = (
        TEMPLATE.replace("{{COMMON_HEAD}}", tc.COMMON_HEAD)
                .replace("{{BODY}}", body)
                .replace("{{DOC_BTNS}}", doc_btns)
                .replace("{{GLOSSARY}}", _glossary)
    )
    for _ph in ("{{COMMON_HEAD}}", "{{BODY}}", "{{DOC_BTNS}}", "{{GLOSSARY}}"):
        if _ph in html_out:
            raise RuntimeError(f"模板占位符未替换：{_ph}（检查 template.html 与 build_html.py 契约）")
    out = Path(args.out)
    out.write_text(html_out, encoding="utf-8", newline="\n")
    print(f"✓ 输出 {out} ({out.stat().st_size/1024:.0f} KB)")

    if not args.no_verify:
        issues = check_html.check(out)
        if issues:
            for issue in issues:
                print(f"✗ {issue}")
            raise SystemExit(f"HTML 产物校验未通过（{len(issues)} 项）")
        print("✓ HTML 产物校验通过")


def _load_template() -> str:
    """读取页面模板（与构建脚本分离的 template.html）。"""
    path = HERE / "template.html"
    if not path.exists():
        raise RuntimeError(f"缺少模板文件：{path}")
    return path.read_text(encoding="utf-8")


TEMPLATE = _load_template()

if __name__ == "__main__":
    main()