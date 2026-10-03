#!/usr/bin/env python3
"""学习卡构建：五篇 md → html/cards.html + cards/ai-primer_cards.tsv。

四堆卡片，全部从源稿/既有权威文件抽取（零新增写作，可回溯来源）：

- core   章核心卡：章首 `> **核心概念/推导/心智模型/决策**：` 块的有序列表
- myth   误解卡：误解陈述（正面）+ 纠正（背面，回显误解句防指代断裂）
- term   术语卡：build/glossary.json（术语 → 释义），自动定位书中首现小节
- quiz   自检题卡：selfcheck 规范形正文题↔附录答案 + 扩展题（背面回显题干）

自含性（防断章取义）：
- 每张卡带来源行（《书》章节）与回看链接（index.html#锚点）
- 误解卡/自检卡背面回显陈述/题干；背面 §X.Y 自动超链
- 极少数自含性不足的卡用 cards_overrides.json 人工桥接（见 check_cards.py 报告）

用法::

    .venv/bin/python build/build_cards.py            # 构建（先跑 build_html）
    .venv/bin/python build/build_cards.py --verify   # 只校验既有产物
"""
from __future__ import annotations

import argparse
import html as H
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import books as bks  # noqa: E402
import template_common as tc  # noqa: E402
import selfcheck as sc  # noqa: E402
import md_links  # noqa: E402

HTML_DIR = ROOT / "html"
INDEX = HTML_DIR / "index.html"
CARDS_HTML = HTML_DIR / "cards.html"
CARDS_TSV_DIR = ROOT / "cards"
CARDS_TSV = CARDS_TSV_DIR / "ai-primer_cards.tsv"
TEMPLATE = HERE / "cards_template.html"
OVERRIDES = HERE / "cards_overrides.json"
ONLINE_BASE = "https://mzy25.github.io/lai/#"

# 分书断言（误解按 2026-09 源稿实际形态校验；不到数即构建失败）
EXPECT_CORE = {"1_ai_math": 7, "2_foundation": 6, "3_use_ai": 8,
               "1a_diffusion": 9, "4_ai_law": 7}
EXPECT_MYTH = {"1_ai_math": 14, "1a_diffusion": 21, "2_foundation": 33,
               "3_use_ai": 12, "4_ai_law": 21}
EXPECT_TERM = 44
EXPECT_QUIZ = {"1_ai_math": 66, "2_foundation": 85, "3_use_ai": 46,
               "1a_diffusion": 38, "4_ai_law": 52}
EXPECT_EXTRA = {"3_use_ai": 12}

DECK_LABELS = {"core": "章核心", "myth": "误解", "term": "术语", "quiz": "自检题"}


# ---------------------------------------------------------------- 锚点索引

def load_anchors():
    """从 html/index.html 解析每篇标题锚点：doc_id → [(id, level, label)]。"""
    html = INDEX.read_text(encoding="utf-8")
    pat = re.compile(
        r'<h([1-6])\b[^>]*id="(doc-\d)-[^"]*"[^>]*data-label="([^"]*)"')
    out: dict[str, list[tuple[str, int, str]]] = {}
    for m in pat.finditer(html):
        level, doc_id, label = int(m.group(1)), m.group(2), H.unescape(m.group(3)).strip()
        # 完整 id 需要从属性中再取
        idm = re.search(r'id="([^"]+)"', m.group(0))
        assert idm is not None
        out.setdefault(doc_id, []).append((idm.group(1), level, label))
    if not out:
        raise RuntimeError(
            "未从 html/index.html 解析到任何标题锚点——HTML 结构或属性顺序变化？"
            "先跑 build/build_html.py 并检查 data-label/id 形态（锚点缺失会让全部卡片回看链接退化为站根）")
    return out


def doc_id_for(key: str) -> str:
    return bks.BY_KEY[key].doc_id


def canon(s: str) -> str:
    """标题规范化：去标签/数学/命令/标点，仅留 CJK+字母数字，小写。"""
    s = H.unescape(s)
    s = re.sub(r'<[^>]+>', '', s)
    for rx in (r'\$\$.*?\$\$', r'\$[^$\n]*\$', r'\\\[.*?\\\]', r'\\\(.*?\\\)'):
        s = re.sub(rx, '', s, flags=re.S)
    s = re.sub(r'\\[a-zA-Z]+', '', s)
    s = re.sub(r'[^0-9A-Za-z\u4e00-\u9fff]', '', s)
    return s.lower()


def _strip_symbol(label: str) -> str:
    return re.sub(r'^[▽◇○◌]\s*', '', label).strip()





def find_anchor(anchors, doc_id: str, *, chapter: str | None = None,
                section: str | None = None, label: str | None = None):
    """定位锚点：章号 → §节号（容忍符号前缀）→ 标题规范化匹配（含篇首回退）。"""
    items = anchors.get(doc_id, [])
    if chapter:
        m = re.search(r'第\s*(\d+)\s*章', chapter) or re.search(r'Ch\s*(\d+)', chapter)
        if m:
            n = m.group(1)
            for hid, lv, lb in items:
                if re.search(rf'第\s*{n}\s*章', lb) and lv == 2:
                    return hid, lb
            for hid, lv, lb in items:
                if re.search(rf'第\s*{n}\s*章', lb):
                    return hid, lb
        else:
            c = canon(chapter)
            for hid, lv, lb in items:
                lbc = canon(lb)
                if c and (lbc == c or lbc.startswith(c[:8]) or c.startswith(lbc[:8])):
                    return hid, lb
    if section:
        want = canon(section)
        if '.' not in section:      # 裸章号：§5 → 第5章
            for hid, lv, lb in items:
                if re.search(rf'第\s*{re.escape(section)}\s*章', lb):
                    return hid, lb
        for hid, lv, lb in items:
            num_m = re.match(r'(\d+(?:\.\d+)*)',
                             _strip_symbol(lb))
            if num_m and num_m.group(1) == section:
                return hid, lb
    if label:
        c = canon(label)
        for hid, lv, lb in items:
            if canon(lb) == c:
                return hid, lb
        for hid, lv, lb in items:
            lbc = canon(lb)
            if c and len(c) >= 6 and (lbc.startswith(c[:8]) or c.startswith(lbc[:8])):
                return hid, lb
        # 篇首（书名标题）回退
        title = bks.BY_DOC_ID[doc_id].title
        if c and (canon(title) == c or c.startswith(canon(title)[:6])):
            return f'{doc_id}-title', title
    return None, None


# ---------------------------------------------------------------- 抽取

CORE_RE = re.compile(r'^> \*\*(核心(?:概念|推导|心智模型|决策))\*\*[：:]?\s*$')
CHAPTER_RE = re.compile(r'^#\s*(?:[▽◇○◌]\s*)?(?:第\s*(\d+)\s*章|Ch\s*(\d+))\s*[：:]?\s*(.*)$')
MYTH_A_RE = re.compile(r'^\*\*(?:常见)?误解\s*([0-9]+|[一二三四五六七八九十]+)\s*[：:]\s*(.+?)\*\*(.*)$')
MYTH_B_RE = re.compile(r'^\*\*(?:常见)?误解(?:\s*([0-9]+|[一二三四五六七八九十]+))?\*\*\s*[：:]?\s*(.*)$')
# 2026-09-15 加粗瘦身后形态：**误解N：**陈述（冒号在粗体内）
MYTH_C_RE = re.compile(r'^\*\*(?:常见)?误解\s*([0-9]+|[一二三四五六七八九十]+)\s*[：:]\*\*\s*(.*)$')
QUOTE_RE = re.compile(r'^[“"\'\s]*(.+?)[”"\'\s]*$')
# 标题行尾的稳定 ID 属性（编号方案三件套）：`{#sec-…}` / `{#ch-N}` / `{#q-…}`
ID_ATTR_RE = re.compile(r'\s*\{#[^}\s]+\}\s*$')


def clean_statement(s: str) -> str:
    s = s.strip()
    m = QUOTE_RE.match(s)
    return (m.group(1) if m else s).strip()


def extract_chapters(text: str):
    """yield (lineno, chapter_no, title) for H1 chapters.

    2026-09-28：章标题行尾会挂稳定 ID（`{#ch-N}`，见编号方案三件套），这里必须剥掉——
    否则 `{#ch-1}` 会原样漏进章级卡片的正面标签、TSV 与 cards.html，并让
    build/cards_review.json 的键失配。小节侧不受影响：那些标题经 pandoc 后
    data-label 只含标题文字（属性进 id），但本章走的是 md 直读。
    """
    for i, line in enumerate(text.split('\n')):
        m = CHAPTER_RE.match(line)
        if m:
            num = m.group(1) or m.group(2)
            title = sc.clean_heading_label(line)
            yield i, num, title


def extract_core(text: str, key: str, book_label: str):
    lines = text.split('\n')
    cards = []
    for i, num, title in extract_chapters(text):
        seg = lines[i:i + 60]
        hit = None
        for j, l in enumerate(seg):
            if CORE_RE.match(l):
                hit = j
                break
        if hit is None:
            continue
        core_m = CORE_RE.match(seg[hit])
        assert core_m is not None
        label = core_m.group(1)
        items = []
        cur = None
        for l in seg[hit + 1:]:
            if not l.startswith('>'):
                break
            if re.match(r'^> \*\*', l):   # 下一个 blockquote 区块
                break
            m = re.match(r'^>\s*\d+\.\s*(.*)$', l)
            if m:
                if cur is not None:
                    items.append(cur.strip())
                cur = m.group(1)
            elif cur is not None and l.strip() not in ('>', '> '):
                cur += '\n' + re.sub(r'^>\s?', '', l)
        if cur is not None:
            items.append(cur.strip())
        if len(items) < 2:
            continue
        cards.append({
            "id": f"core-{key}-{num}",
            "deck": "core", "book": key, "book_label": book_label,
            "chapter": title, "group": None, "number": None,
            "front_md": f"**《{book_label}》{title}**\n\n说出本章的 **{len(items)} 条{label}**",
            "echo_md": None,
            "back_md": "\n".join(f"{k + 1}. {it}" for k, it in enumerate(items)),
            "hint_md": None,
            "source": {"chapter": title, "section": None},
        })
    return cards


def extract_myths(text: str, key: str, book_label: str):
    lines = text.split('\n')
    cards = []
    i = 0
    while i < len(lines):
        line = lines[i]
        ma = MYTH_A_RE.match(line)
        mb = None if ma else MYTH_B_RE.match(line)
        mc = None if (ma or mb) else MYTH_C_RE.match(line)
        if not ma and not mb and not mc:
            i += 1
            continue
        if ma:
            num, stmt_raw, rest = ma.group(1), ma.group(2), ma.group(3)
        else:
            num, tail = (mb or mc).group(1), (mb or mc).group(2)
            qm = re.search(r'[“"]([^”"]+)[”"]', tail)
            if qm:
                stmt_raw, rest = qm.group(1), tail[qm.end():]
            else:
                stmt_raw, rest = tail, ''
        stmt = clean_statement(stmt_raw)
        if not stmt or len(stmt) < 4:
            i += 1
            continue
        body_lines = [rest.strip()] if rest.strip() else []
        j = i + 1
        while j < len(lines):
            l = lines[j]
            if re.match(r'^#', l) or MYTH_A_RE.match(l) or MYTH_B_RE.match(l) or MYTH_C_RE.match(l):
                break
            body_lines.append(l)
            j += 1
        body = '\n'.join(body_lines).strip()
        # 章节归属：向上找最近 H2
        chapter = next((sc.clean_heading_label(lines[k])
                        for k in range(i, -1, -1)
                        if re.match(r'^##\s', lines[k])), '')
        cards.append({
            "id": f"myth-{key}-{len(cards) + 1}",
            "deck": "myth", "book": key, "book_label": book_label,
            "chapter": chapter, "group": None, "number": num,
            "front_md": f"**《{book_label}》{chapter}**\n\n这句话错在哪？\n\n> {stmt}",
            "echo_md": stmt,
            "back_md": body,
            "hint_md": None,
            "source": {"chapter": None, "section": None, "label": chapter},
        })
        i = j
    return cards


def extract_terms(anchors):
    data = json.loads((HERE / "glossary.json").read_text(encoding="utf-8"))
    cards = []
    for idx, (term, definition) in enumerate(data["terms"], 1):
        # 首现定位：按篇序找第一个含该术语的篇，再找其最近上级标题
        found = None
        for b in bks.BOOKS:
            t = b.md_path.read_text(encoding="utf-8")
            pos = t.find(term)
            if pos == -1:
                pos = t.lower().find(term.lower())
            if pos == -1:
                continue
            lines = t[:pos].split('\n')
            label, level = None, None
            for l in reversed(lines):
                m = re.match(r'^(#{1,6})\s+(.*)$', l)
                if m:
                    # 剥掉行尾稳定 ID（编号方案三件套），否则会漏进术语卡的
                    # chapter 字段与 cards.html 内嵌 JSON
                    level = len(m.group(1))
                    label = sc.clean_heading_label(m.group(0))
                    break
            found = (b, label, level)
            break
        src = {"chapter": None, "section": None, "label": None}
        if found:
            b, label, level = found
            hid, found_label = find_anchor(anchors, b.doc_id, label=label)
            src = {"chapter": label if level == 1 else None,
                   "label": found_label or label, "anchor": hid}
        cards.append({
            "id": f"term-{idx}",
            "deck": "term", "book": found[0].key if found else None,
            "book_label": found[0].label if found else "",
            "chapter": found[1] if found else "", "group": None, "number": None,
            "front_md": f"**{term}**",
            "echo_md": None,
            "back_md": definition,
            "hint_md": None,
            "source": src,
        })
    return cards


def pair_records(region, chapter):
    by_group: dict = {}
    for r in chapter.records:
        by_group.setdefault(r.group, []).append(r)
    used: dict = {}
    out = []
    for q in region.questions:
        pool = by_group.get(q.group) or by_group.get(None, [])
        i = used.get(q.group, 0)
        if i < len(pool):
            out.append((q, pool[i]))
            used[q.group] = i + 1
    return out


def extract_quiz(text: str, key: str, book_label: str):
    regions = sc.parse_body(text)
    chapters = sc.parse_appendix(text)
    cards = []
    for ri, (region, chapter) in enumerate(zip(regions, chapters)):
        pairs = pair_records(region, chapter)
        assert len(pairs) == len(region.questions), (
            f"{book_label}: 第{ri + 1}区配对 {len(pairs)}/{len(region.questions)}")
        for q, r in pairs:
            cards.append({
                "id": f"quiz-{key}-{ri + 1}-{q.group or ''}-{q.number}",
                "qid": q.qid,
                "deck": "quiz", "book": key, "book_label": book_label,
                "chapter": region.chapter, "group": q.group, "number": q.number,
                "front_md": (f"**《{book_label}》{region.chapter}"
                             + (f" · {q.group}" if q.group else "")
                             + f" · 第{q.number}题**\n\n" + q.text),
                "echo_md": q.text,
                "back_md": r.answer or "",
                "hint_md": r.hint,
                "source": {"chapter": region.chapter, "section": None},
            })
    for r in sc.extra_records(text):
        cards.append({
            "id": f"quiz-{key}-extra-{r.number}",
            "deck": "quiz", "book": key, "book_label": book_label,
            "chapter": "扩展题", "group": None, "number": r.number,
            "front_md": f"**《{book_label}》扩展题 · 第{r.number}题**\n\n" + (r.text or ""),
            "echo_md": r.text or "",
            "back_md": r.answer or "", "hint_md": r.hint,
            "source": {"chapter": None, "section": None, "label": "附录：扩展题"},
        })
    return cards


# ---------------------------------------------------------------- 覆盖与后处理

OVERRIDE_FIELDS = {"front", "echo", "back", "hint", "context", "source_label", "note"}


def validate_overrides(data: dict) -> list[str]:
    """纯校验（O1 2026-10）：未知字段即报；键形（卡 id 或稳定题 ID `q-…`）由解析期兜底。"""
    problems = []
    for cid, edit in data.items():
        if not isinstance(edit, dict):
            problems.append(f"{cid}: 覆盖值必须是对象")
            continue
        unknown = sorted(set(edit) - OVERRIDE_FIELDS)
        if unknown:
            problems.append(f"{cid}: 未知字段 {unknown}（允许 {sorted(OVERRIDE_FIELDS)}）")
        for k, v in edit.items():
            if k in OVERRIDE_FIELDS and not isinstance(v, str):
                problems.append(f"{cid}: 字段 {k} 必须是字符串，实为 {type(v).__name__}")
    return problems


def resolve_cards(cards):
    """卡索引：id、限定题 ID（`q-…@book`）、裸题 ID（全局唯一时才可解析）。

    qid 是**篇内** ID（每书都有 q-c1-kp01），跨书重复是常态；**同书同 qid 重复**才是
    ID 空间异常（idcheck 应拦）。返回 (id_map, qmap, bare, dup_qid_keys)。
    """
    id_map, qmap, bare, dup = {}, {}, {}, []
    for c in cards:
        id_map[c["id"]] = c
        q = c.get("qid")
        if not q:
            continue
        key = f"{q}@{c['book']}"
        if key in qmap and qmap[key] is not c:
            dup.append(key)
        else:
            qmap[key] = c
        if q not in bare:
            bare[q] = c
        elif bare[q] is not c and bare[q] is not None:
            bare[q] = None          # 全局歧义：裸键不可解析，须写限定键
    return id_map, qmap, bare, dup


def apply_overrides(cards):
    """→ (覆盖条数, 孤儿键, 冲突, 问题清单)。

    键优先按卡 id，其次按稳定题 ID `q-…`（O2 2026-10）。冲突 = 同键命中不同卡 + 重复 qid
    （`check_cards` 失败项，Q3）；问题 = 未知字段/非对象值（仅报告，R3 不中断）。
    """
    if not OVERRIDES.exists():
        return 0, [], [], []
    data = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    index, qindex, bare, conflicts = resolve_cards(cards)
    problems = validate_overrides(data)
    orphans = []
    n = 0
    for cid, edit in data.items():
        if not isinstance(edit, dict):   # R3：坏值只报告，不参与解析、不崩
            continue
        by_id = index.get(cid)
        if by_id:
            c = by_id
        elif "@" in cid:
            c = qindex.get(cid)
        elif cid in bare:
            c = bare[cid]
            if c is None:                # 裸 qid 跨书歧义 → 须写 q-…@book
                conflicts.append(cid)
                continue
        else:
            c = None
        if c is None:
            orphans.append(cid)
            continue
        if "front" in edit:
            c["front_md"] = edit["front"]
        if "echo" in edit:
            c["echo_md"] = edit["echo"]
        if "back" in edit:
            c["back_md"] = edit["back"]
        if "hint" in edit:
            c["hint_md"] = edit["hint"]
        if "context" in edit:
            c["back_md"] = edit["context"].rstrip() + "\n\n" + (c["back_md"] or "")
        if "source_label" in edit:
            c["source"]["label"] = edit["source_label"]
        c["override_note"] = edit.get("note", "")
        n += 1
    return n, orphans, conflicts, problems


IMG_RE = re.compile(r'!\[([^\]]*)\]\([^)]*\)')
DETAILS_RE = re.compile(r'<details>\s*<summary>(.*?)</summary>(.*?)</details>', re.S)


def clean_fragment(md: str) -> str:
    """卡片片段：图转 alt 文本；details 展开为加粗标题+内容。"""
    md = IMG_RE.sub(lambda m: m.group(1) or '（图）', md)
    md = DETAILS_RE.sub(lambda m: f"**{m.group(1).strip()}**\n\n{m.group(2).strip()}", md)
    return md.strip()


def batch_md_to_html(fragments: list[str]) -> list[str]:
    """一次 pandoc 批量转换（标记段落切分），空片段返回空串。"""
    parts = []
    order = []
    for i, frag in enumerate(fragments):
        frag = clean_fragment(frag or '')
        if not frag:
            continue
        marker = f"CARDFRAGMARK{i}END"
        parts.append(f"{marker}\n\n{frag}\n")
        order.append(i)
    if not parts:
        return ['' for _ in fragments]
    joined = "\n\n".join(parts)
    assert 'CARDFRAGMARK' not in ''.join(fragments), '卡片片段含保留标记字符串'
    joined = md_links.normalize_citations(joined)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".md",
                                     delete=False) as f:
        f.write(joined)
        tmp = f.name
    try:
        r = subprocess.run(
            ["pandoc", tmp, "-t", "html", f"--from={md_links.FROM_FLAGS}",
             "--mathjax", "--wrap=none"],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"pandoc 卡片转换失败: {r.stderr[:400]}")
        out_html = r.stdout
    finally:
        Path(tmp).unlink(missing_ok=True)
    result = ['' for _ in fragments]
    pieces = re.split(r'<p>CARDFRAGMARK(\d+)END</p>\s*', out_html)
    # pieces: [pre, idx, body, idx, body, ...]
    for k in range(1, len(pieces), 2):
        idx = int(pieces[k])
        result[idx] = pieces[k + 1].strip()
    missing = [i for i in order if not result[i]]
    assert not missing, f"pandoc 丢失卡片片段: {missing[:5]}"
    return result


REF_RE = re.compile(r'§\s*(\d{1,2}(?:\.\d{1,3})*)')


def link_section_refs(html: str, anchors, doc_id: str):
    """把正文段中的 §X.Y 变成 index.html 锚点链接；无法解析的原样保留并计数。"""
    unresolved = []

    def repl_text(text):
        def one(m):
            sec = m.group(1)
            hid, _ = find_anchor(anchors, doc_id, section=sec)
            if hid:
                return f'<a class="card-ref" href="index.html#{hid}">{m.group(0)}</a>'
            unresolved.append(sec)
            return m.group(0)
        return REF_RE.sub(one, text)

    parts = re.split(r'(<[^>]+>)', html)
    out = []
    for part in parts:
        if part.startswith('<') and part.endswith('>'):
            out.append(part)
        else:
            out.append(repl_text(part))
    return ''.join(out), unresolved


# ---------------------------------------------------------------- 渲染

def abs_link(anchor: str | None) -> str:
    return ONLINE_BASE + anchor if anchor else ONLINE_BASE


def render_tsv(cards) -> str:
    lines = ["Front\tBack\tTags"]
    for c in cards:
        front = c["front_html"]
        if c.get("hint_html"):
            front += f'<div class="hint"><i>提示：{c["hint_html"]}</i></div>'
        back_parts = []
        if c.get("echo_html"):
            back_parts.append(f'<div class="echo">{c["echo_html"]}</div>')
        back_parts.append(c["back_html"])
        src = c.get("source_label") or ""
        link = abs_link(c.get("anchor"))
        if src:
            back_parts.append(f'<div class="src">来源：{src} · <a href="{link}">回看正文</a></div>')
        back = ''.join(back_parts)
        tags = f"ai-primer {c['deck']} {c['book_label']}".strip()
        esc = lambda s: s.replace('\t', ' ').replace('\r', '').replace('\n', '<br>')
        lines.append(f"{esc(front)}\t{esc(back)}\t{esc(tags)}")
    return '\n'.join(lines) + '\n'


def render_page(cards) -> str:
    tpl = TEMPLATE.read_text(encoding="utf-8")
    payload = json.dumps(cards, ensure_ascii=False, separators=(',', ':')).replace("</", "<\\/")
    labels = json.dumps(DECK_LABELS, ensure_ascii=False)
    page = (tpl.replace("{{COMMON_HEAD}}", tc.COMMON_HEAD)
               .replace("{{CARDS_JSON}}", payload).replace("{{DECK_LABELS}}", labels))
    if "{{" in page:
        raise RuntimeError("cards_template.html 占位符未替换（检查模板与 build_cards.py 契约）")
    return page


# ---------------------------------------------------------------- 主流程

def collect_cards(anchors):
    all_cards = []
    core_by_key = {}
    for b in bks.BOOKS:
        text = b.md_path.read_text(encoding="utf-8")
        core = extract_core(text, b.key, b.label)
        myths = extract_myths(text, b.key, b.label)
        quiz = extract_quiz(text, b.key, b.label)
        core_by_key[b.key] = len(core)
        assert len(core) == EXPECT_CORE[b.key], (
            f"{b.label}: 章核心卡 {len(core)}，期望 {EXPECT_CORE[b.key]}")
        assert len(myths) == EXPECT_MYTH[b.key], (
            f"{b.label}: 误解卡 {len(myths)}，期望 {EXPECT_MYTH[b.key]}")
        n_quiz = sum(1 for c in quiz if '-extra-' not in c["id"])
        n_extra = len(quiz) - n_quiz
        assert n_quiz == EXPECT_QUIZ[b.key], (
            f"{b.label}: 自检题 {n_quiz}，期望 {EXPECT_QUIZ[b.key]}"
            "（新增/删题后：同步本文件 EXPECT_QUIZ 与 README 卡片计数）")
        assert n_extra == EXPECT_EXTRA.get(b.key, 0), (
            f"{b.label}: 扩展题 {n_extra}")
        all_cards += core + myths + quiz
    # 核心卡总数断言（各篇合计）
    terms = extract_terms(anchors)
    assert len(terms) == EXPECT_TERM, f"术语卡 {len(terms)}，期望 {EXPECT_TERM}"
    all_cards += terms
    # 来源锚点 + 回显 + § 链接（HTML 阶段）
    for c in all_cards:
        doc_id = doc_id_for(c["book"]) if c["book"] else None
        src = c["source"]
        hid, lb = (None, None)
        if doc_id:
            hid, lb = find_anchor(anchors, doc_id, chapter=src.get("chapter"),
                                  section=src.get("section"), label=src.get("label"))
        c["anchor"] = hid
        # 来源标签剥跳读标记（▽○◌◇）：标记在正文/目录里是读者可见的路径提示，
        # 但在卡片的"来源"行是噪声（2026-09-29 复审：扩散 Ch7-9、基座 §6.4/§6.5 曾漏）
        lb = sc.clean_heading_label(lb) if lb else lb
        c["source_label"] = lb or src.get("label") or src.get("chapter") or ""
    return all_cards


def convert_cards(cards, anchors):
    frags = []
    slots = []
    for c in cards:
        for field in ("front_md", "echo_md", "back_md", "hint_md"):
            slots.append((c, field))
            frags.append(c.get(field) or "")
    htmls = batch_md_to_html(frags)
    for (c, field), h in zip(slots, htmls):
        if field == "front_md":
            c["front_html"] = h
        elif field == "echo_md":
            c["echo_html"] = h
        elif field == "back_md":
            c["back_html"] = h
        else:
            c["hint_html"] = h
    warnings = []
    for c in cards:
        doc_id = doc_id_for(c["book"]) if c["book"] else None
        for field in ("echo_html", "back_html", "front_html", "hint_html"):
            if not c.get(field) or not doc_id:
                continue
            c[field], un = link_section_refs(c[field], anchors, doc_id)
            if un:
                warnings.append((c["id"], field, un))
    # 清理仅用于构建的 md 字段
    for c in cards:
        for k in ("front_md", "echo_md", "back_md", "hint_md"):
            c.pop(k, None)
    return warnings


def main() -> int:
    ap = argparse.ArgumentParser(description="构建学习卡（cards.html + TSV）")
    ap.add_argument("--verify", action="store_true", help="只校验既有产物")
    args = ap.parse_args()

    if not INDEX.exists():
        print("缺少 html/index.html（先跑 build/build_html.py）", file=sys.stderr)
        return 2
    anchors = load_anchors()
    cards = collect_cards(anchors)
    n_ov, orphans, ov_conflicts, ov_problems = apply_overrides(cards)
    if orphans:
        print(f"⚠ cards_overrides.json 有孤儿 id：{orphans[:5]}", file=sys.stderr)
        return 2
    for cf in ov_conflicts:
        print(f"⚠ cards_overrides.json 冲突键/重复 qid：{cf}", file=sys.stderr)
    for pb in ov_problems:
        print(f"⚠ cards_overrides.json：{pb}", file=sys.stderr)
    warnings = convert_cards(cards, anchors)

    by_deck = {}
    for c in cards:
        by_deck.setdefault(c["deck"], []).append(c)

    if not args.verify:
        CARDS_TSV_DIR.mkdir(exist_ok=True)
        CARDS_HTML.write_text(render_page(cards), encoding="utf-8", newline="\n")
        CARDS_TSV.write_text(render_tsv(cards), encoding="utf-8", newline="\n")

    ids = [c["id"] for c in cards]
    if len(set(ids)) != len(ids):
        dup = sorted(i for i in set(ids) if ids.count(i) > 1)
        print(f"✗ 卡片 id 重复：{dup[:5]}（{len(dup)} 个）", file=sys.stderr)
        return 1
    missing_anchor = sum(1 for c in cards if not c["anchor"])
    print("✓ 卡片：", " / ".join(f"{DECK_LABELS[k]} {len(v)}" for k, v in sorted(by_deck.items())))
    print(f"✓ 覆盖：{n_ov} 张 · 来源锚点缺失：{missing_anchor} 张")
    if missing_anchor:
        print(f"✗ 来源锚点缺失 {missing_anchor} 张——卡片回看链接会退化为站根（检查标题 ID/data-label）",
              file=sys.stderr)
        return 1
    if warnings:
        print(f"⚠ § 引用未解析 {len(warnings)} 处（check_cards.py 可出报告）")
    if not args.verify:
        print(f"✓ 输出 {CARDS_HTML} ({CARDS_HTML.stat().st_size/1024:.0f} KB)")
        print(f"✓ 输出 {CARDS_TSV} ({CARDS_TSV.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
