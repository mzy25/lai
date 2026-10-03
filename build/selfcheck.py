#!/usr/bin/env python3
"""自检区结构模型：正文题 ↔ 附录答案的解析与守恒校验（md 级，构建前置）。

解析两类源稿格式（过渡期并存；规范形即 per-question）：

- per-question（规范形，现状：扩散/基座/用好AI）：
  附录 `### 章标题` + 可选 `**【组名】**` + `Qn（标签）?. 题干`（加粗可选） +
  `<details><summary>卡住再看提示</summary>…</details>`（可选）+
  `<details><summary>答案</summary>…</details>`（必填）。
- legacy-bundle（AI数学现状）：附录按章收 `知识点答案/逻辑链答案` 的
  有序列表整包；正文题干按组序配对，提示来自 `卡住再看提示` 整包。
- legacy-law（AI规律现状）：附录 `ChN 提示/答案` 两包有序列表；正文题干
  按章序配对。

校验输出（供 lint_md 转 Finding）：

- selfcheck-region-count  正文自检区数 ≠ 附录章数
- selfcheck-count         某章正文题数 ≠ 附录记录数
- selfcheck-answer-missing 某题无答案
- selfcheck-text-mismatch  规范形附录题面与正文题干不一致（warning）
- selfcheck-number-mismatch 规范形 Q 编号与正文题号不一致（warning）
- selfcheck-empty-region   正文自检区无题（warning）

用法::

    from selfcheck import validate
    issues = validate(md_text)
自检::

    python3 build/selfcheck.py --selftest
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field

from books import SELFCHECK_HEADING

_FENCE_RE = re.compile(r'^\s*(```|~~~)')
_HEAD_RE = re.compile(r'^(#{1,6})\s+(.*)$')
_REGION_RE = re.compile(r'^\*\*本章自检\*\*')
# 标题行尾的稳定 ID 属性（编号方案三件套）
ID_ATTR_TAIL_RE = re.compile(r'\s*\{#[^}\s]+\}\s*$')
# 跳读标记（▽○◌◇）不是标题文字：卡片标签/章字段/来源行都必须剥掉。
# 2026-09-29 复审：此前只剥稳定 ID，导致扩散 Ch7-9、规律 Ch8、基座 §6.4/§6.5 的
# 标记漏进 28+ 张卡片。build_cards 复用本函数（sc.clean_heading_label）。
_READ_MARK_RE = re.compile(r'^[▽○◌◇]\s*')


def strip_id_tail(s: str) -> str:
    """剥行尾稳定 ID（题目 `{#q-…}`）——它在解析层就该消失，不许进题面文本
    （2026-09-29 I2：卡片 TSV 曾因此残留 ID 字面量）。"""
    return ID_ATTR_TAIL_RE.sub("", s).strip()


def clean_heading_label(raw: str) -> str:
    """标题行/标题文字 → 干净标签：剥 `#` 前缀、行尾稳定 ID、跳读标记。"""
    t = re.sub(r'^#{1,6}\s*', '', raw.strip())
    t = ID_ATTR_TAIL_RE.sub('', t).strip()
    return _READ_MARK_RE.sub('', t).strip()
_GROUP_RE = re.compile(r'^\*\*【([^】]+)】\*\*', re.M)
_ITEM_RE = re.compile(r'^\s*(\d+)[.、)]\s+(.*)$')
_QID_RE = re.compile(r'\{#(q-[^}\s]+)\}')  # 题稳定 ID（编号方案三件套；O2 2026-10）
_BOLD_Q_RE = re.compile(r'^\*\*(\d+)\s*(?:（([^）]*)）)?\s*[.、．]\*\*\s*(.*)$')
_APPX_Q_RE = re.compile(r'^\*{0,2}Q(\d+)\s*(?:（([^）]*)）)?\s*[.、．]?\s*(.*?)\s*\*{0,2}\s*$', re.M)  # 加粗可选（2026-09-15 去粗后）
_H3_RE = re.compile(r'^###\s+(.*)$')
_DETAILS_RE = re.compile(r'<details>\s*<summary>\s*(.*?)\s*</summary>(.*?)</details>', re.S)


@dataclass
class BodyQuestion:
    group: str | None
    number: int
    text: str
    qid: str = ""          # 稳定题 ID（`{#q-cN-组码NN}` 内部名，无花括号）；O2 2026-10


@dataclass
class BodyRegion:
    heading: str          # 最近的上级标题（诊断用）
    chapter: str = ''     # 所属章：文档标题之后的最近 H1；章前区回退最近 H2
    questions: list[BodyQuestion] = field(default_factory=list)


@dataclass
class AnswerRecord:
    group: str | None
    number: int | None
    text: str | None      # 规范形=附录题面；legacy=None（正文题干为准）
    hint: str | None
    answer: str | None


@dataclass
class AppxChapter:
    title: str
    records: list[AnswerRecord] = field(default_factory=list)


@dataclass
class Issue:
    code: str
    message: str
    severity: str = 'error'


# ------------------------------------------------------------------ 解析

def _truthy_fences(lines):
    """yield (line, in_fence)；围栏行本身 in_fence=False。"""
    in_f = False
    for line in lines:
        if _FENCE_RE.match(line):
            yield line, False
            in_f = not in_f
        else:
            yield line, in_f


def _selfcheck_span_range(text: str) -> tuple[int, int] | None:
    """自检附录区间 [start, end) 的字符偏移（含 H1 行首；end 为下一 H1 行首或 EOF）。"""
    lines = text.split('\n')
    # 行首偏移表
    offsets = []
    pos = 0
    for line in lines:
        offsets.append(pos)
        pos += len(line) + 1
    inside = False
    start = -1
    for i, (line, in_f) in enumerate(_truthy_fences(lines)):
        if in_f:
            continue
        if line.strip() == SELFCHECK_HEADING:
            inside = True
            start = offsets[i]
            continue
        if inside and re.match(r'^#\s', line):
            return start, offsets[i]
    if inside:
        return start, len(text)
    return None


def _selfcheck_span(text: str) -> str:
    """截取自检附录 H1 到下一个 H1（围栏感知）；找不到返回空串。"""
    rng = _selfcheck_span_range(text)
    if rng is None:
        return ''
    start, end = rng
    # 去掉标题行本身
    nl = text.find('\n', start)
    return text[nl + 1:end] if nl != -1 else ''


def parse_body(text: str) -> list[BodyRegion]:
    """正文自检区（文档序）：每区收集组名与编号题干。"""
    regions: list[BodyRegion] = []
    cur_heading = ''
    cur_chapter = ''      # 文档标题后的最近 H1
    fallback_h2 = ''      # 章前区（如 用好AI 引子）回退用
    seen_doc_title = False
    cur_region: BodyRegion | None = None
    cur_group: str | None = None
    for line, in_f in _truthy_fences(text.split('\n')):
        if in_f:
            continue
        m = _HEAD_RE.match(line)
        if m:
            if cur_region is not None:
                regions.append(cur_region)
                cur_region = None
            level, title = len(m.group(1)), clean_heading_label(m.group(2))
            cur_heading = title
            if level == 1:
                if seen_doc_title:
                    # 剥掉行尾稳定 ID（编号方案三件套：`{#ch-N}`）——否则它会
                    # 漏进自检题卡正面标签「《用好AI》第1章：… {#ch-1} · 第1题」
                    cur_chapter = title
                else:
                    seen_doc_title = True
            elif level == 2:
                # 同上：H2 回退标题也要剥 ID（它会进卡片的 chapter 字段与 JSON 元数据）
                fallback_h2 = title
            continue
        if _REGION_RE.match(line):
            if cur_region is not None:
                regions.append(cur_region)
            cur_region = BodyRegion(heading=cur_heading,
                                    chapter=cur_chapter or fallback_h2)
            cur_group = None
            continue
        if cur_region is None:
            continue
        gm = _GROUP_RE.match(line)
        if gm:
            cur_group = gm.group(1)
            continue
        bm = _BOLD_Q_RE.match(line)
        if bm:
            _raw = bm.group(3)
            _qm = _QID_RE.search(_raw)
            cur_region.questions.append(BodyQuestion(cur_group, int(bm.group(1)), strip_id_tail(_raw),
                                                     _qm.group(1) if _qm else ""))
            continue
        im = _ITEM_RE.match(line)
        if im:
            _raw = im.group(2)
            _qm = _QID_RE.search(_raw)
            cur_region.questions.append(BodyQuestion(cur_group, int(im.group(1)), strip_id_tail(_raw),
                                                     _qm.group(1) if _qm else ""))
    if cur_region is not None:
        regions.append(cur_region)
    return regions


def parse_appendix(text: str) -> list[AppxChapter]:
    """自检附录解析（规范形）：H3 章 → 可选组标签 → Q 头 + details。"""
    span = _selfcheck_span(text)
    if not span:
        return []
    chapters: list[AppxChapter] = []
    hs = [(m.start(), m.group(1)) for m in re.finditer(r'^### (.+)$', span, re.M)]
    for k, (pos, title) in enumerate(hs):
        end = hs[k + 1][0] if k + 1 < len(hs) else len(span)
        segment = span[pos:end]
        ch = AppxChapter(title=clean_heading_label(title))
        qm_iter = list(_APPX_Q_RE.finditer(segment))
        for j, qm in enumerate(qm_iter):
            block_end = qm_iter[j + 1].start() if j + 1 < len(qm_iter) else len(segment)
            block = segment[qm.start():block_end]
            gm2 = None
            for g in _GROUP_RE.finditer(segment[:qm.start()]):
                gm2 = g.group(1)
            hint = answer = None
            for dm in _DETAILS_RE.finditer(block):
                summary, content = dm.group(1).strip(), dm.group(2).strip()
                if '提示' in summary and hint is None:
                    hint = content
                elif '答案' in summary and answer is None:
                    answer = content
            ch.records.append(AnswerRecord(gm2, int(qm.group(1)), strip_id_tail(qm.group(3)), hint, answer))
        if ch.records:
            chapters.append(ch)
    return chapters


def extra_records(text: str) -> list[AnswerRecord]:
    """自检附录之后题群（如 `# 附录：扩展题`）的 Q/A 记录。"""
    rng = _selfcheck_span_range(text)
    tail = text[rng[1]:] if rng else text
    out: list[AnswerRecord] = []
    for m in re.finditer(r'^#\s+.*$', tail, re.M):
        if '扩展题' not in m.group(0):
            continue
        rest = tail[m.end():]
        nxt = re.search(r'^#\s', rest, re.M)
        section = rest[:nxt.start()] if nxt else rest
        qms = list(_APPX_Q_RE.finditer(section))
        for j, qm in enumerate(qms):
            end = qms[j + 1].start() if j + 1 < len(qms) else len(section)
            block = section[qm.start():end]
            hint = answer = None
            for dm in _DETAILS_RE.finditer(block):
                summary, content = dm.group(1).strip(), dm.group(2).strip()
                if '提示' in summary and hint is None:
                    hint = content
                elif '答案' in summary and answer is None:
                    answer = content
            out.append(AnswerRecord(None, int(qm.group(1)), strip_id_tail(qm.group(3)), hint, answer))
    return out


def count_extra_questions(text: str) -> int:
    """自检附录之后题群（如 `# 附录：扩展题`）的题数（正文无对应题干）。"""
    return len(extra_records(text))


# ------------------------------------------------------------------ 校验

def _flat_body(region: BodyRegion):
    return list(region.questions)


def validate(text: str) -> list[Issue]:
    body = parse_body(text)
    appx = parse_appendix(text)
    issues: list[Issue] = []

    if len(body) != len(appx):
        issues.append(Issue('selfcheck-region-count',
                            f'正文自检区 {len(body)} 个，附录章 {len(appx)} 个'))
    for i, (region, ch) in enumerate(zip(body, appx)):
        qs = _flat_body(region)
        if not qs:
            issues.append(Issue('selfcheck-empty-region',
                                f'第 {i + 1} 个自检区无题（{region.heading}）', 'warning'))
        if len(qs) != len(ch.records):
            issues.append(Issue('selfcheck-count',
                                f'第 {i + 1} 区（{region.heading}）：正文 {len(qs)} 题，'
                                f'附录 {len(ch.records)} 条'))
            continue
        body_groups = [q.group for q in qs]
        rec_groups = [r.group for r in ch.records]
        if any(r.group is not None for r in ch.records) and body_groups != rec_groups:
            issues.append(Issue('selfcheck-count',
                                f'第 {i + 1} 区（{region.heading}）组序不一致：'
                                    f'正文 {body_groups} vs 附录 {rec_groups}'))
        for j, (q, r) in enumerate(zip(qs, ch.records)):
            if not r.answer:
                issues.append(Issue('selfcheck-answer-missing',
                                    f'第 {i + 1} 区第 {j + 1} 题（{q.text[:20]}…）无答案'))
            if r.text is not None:
                if _norm(q.text) != _norm(r.text):
                    issues.append(Issue('selfcheck-text-mismatch',
                                        f'第 {i + 1} 区第 {j + 1} 题面不一致：'
                                        f'正文「{q.text[:24]}」附录「{r.text[:24]}」'))
            if r.number is not None and r.number != q.number:
                issues.append(Issue('selfcheck-number-mismatch',
                                    f'第 {i + 1} 区第 {j + 1} 题：正文号 {q.number} '
                                    f'vs 附录号 {r.number}', 'warning'))
    return issues


_PUNCT = re.compile(r'\s|\*\*|[*_`]|[（(].*?[）)]|<[^>]*>|\[\d+\]')


def _norm(s: str) -> str:
    # 正文题面可带内联支架：括号提示「（提示：…）」或句尾「提示：…」，比对时忽略
    s = re.sub(r'[（(]\s*提示[：:].*?[）)]', '', s)
    s = re.sub(r'\s*提示[：:].*$', '', s)
    # 机器标注不算题面差异：引用绑定 `〔…〕` 只出现在正文侧（附录不进 ID/引用体系），
    # 稳定 ID `{#…}` 同理。2026-09-29 I1-1：基座第2区第18题的正文绑定曾致误报。
    s = re.sub(r'〔[^〕]*〕', '', s)
    s = re.sub(r'\{#[^}\s]*\}', '', s)
    s = _PUNCT.sub('', s)
    return s


# ------------------------------------------------------------------ selftest

_CANON = '''# 书
## 第1章

**本章自检**：

**【知识点】**

1. 第一题？
2. 第二题？

# 附录：自检问题与答案

### 第1章

**【知识点】**

**Q1. 第一题？**

<details>
<summary>卡住再看提示</summary>

提示一
</details>

<details>
<summary>答案</summary>

答案一
</details>

**Q2. 第二题？**

<details>
<summary>答案</summary>

答案二
</details>
'''

def _selftest() -> int:
    cases = []

    def case(name, ok, detail=''):
        cases.append((name, ok, detail))

    # 1. 规范形：零 issue
    case('canonical clean', validate(_CANON) == [], str(validate(_CANON)))

    # 2. 规范形缺答案 → answer-missing
    broken = _CANON.replace('<details>\n<summary>答案</summary>\n\n答案一\n</details>\n\n', '')
    codes = {i.code for i in validate(broken)}
    case('canonical missing answer', 'selfcheck-answer-missing' in codes, str(codes))

    # 3. 规范形题量不匹配 → count
    broken = _CANON.replace('**Q2. 第二题？**', '')
    codes = {i.code for i in validate(broken)}
    case('canonical count mismatch', 'selfcheck-count' in codes, str(codes))

    # 4. 题面不一致 → text-mismatch
    broken = _CANON.replace('**Q2. 第二题？**', '**Q2. 改过的题？**')
    codes = {i.code for i in validate(broken)}
    case('canonical text mismatch', 'selfcheck-text-mismatch' in codes, str(codes))

    # 4b. 内联支架（括号提示 / 句尾提示）两侧归一后可对齐 → 零 issue
    with_hints = _CANON.replace(
        '1. 第一题？', '1. 第一题？（提示：先想定义）').replace(
        '2. 第二题？', '2. 第二题？提示：翻 §1.2。')
    case('inline hints tolerated', validate(with_hints) == [], str(validate(with_hints)))

    # 5. 正文区数与附录章数不一致 → region-count
    broken = _CANON + '\n### 第2章\n\n**Q1. 多出来的？**\n'
    codes = {i.code for i in validate(broken)}
    case('region count mismatch', 'selfcheck-region-count' in codes, str(codes))

    ok = True
    for name, passed, detail in cases:
        print(('PASS ' if passed else 'FAIL ') + name)
        if not passed:
            ok = False
            print('  detail:', detail)
    print('selfcheck selftest:', 'all pass' if ok else 'FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        raise SystemExit(_selftest())
    print(__doc__)
