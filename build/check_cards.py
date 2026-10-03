#!/usr/bin/env python3
"""学习卡校验与清晰度报告（防断章取义的人工校对入口）。

检查：
- 计数：四堆分书断言（与 build_cards 相同）
- 来源：每张卡来源锚点是否在 html/index.html 可达
- 引用：背面 §X.Y 是否全部解析成链接（未解析清单供人工裁决）
- 自含性：误解卡/自检卡背面回显是否在场；指代开头、过短背面、空背面
- 覆盖：cards_overrides.json 是否有孤儿 id
- 产物：cards.html 内嵌卡片数、TSV 行数与卡片数一致

用法::

    .venv/bin/python build/check_cards.py                 # 出报告（退出码：致命问题非零）
    .venv/bin/python build/check_cards.py --report path.md
    .venv/bin/python build/check_cards.py --selftest      # 夹具回归
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import build_cards as bc  # noqa: E402

DEICTIC_START = ('两者', '两种', '这两', '这条', '这些', '这样', '它们', '它', '该', '上述', '上文', '前者', '二者', '此')
MIN_BACK = {'core': 20, 'myth': 40, 'quiz': 40, 'term': 8}
REVIEW = HERE / 'cards_review.json'


def load_accepted() -> dict:
    if not REVIEW.exists():
        return {}
    data = json.loads(REVIEW.read_text(encoding='utf-8'))
    return data.get('accepted', {})


def strip_tags(html: str) -> str:
    return re.sub(r'<[^>]+>', '', html or '').strip()


def detect_orphans(override_ids, card_ids) -> list[str]:
    return sorted(set(override_ids) - set(card_ids))


def waiver_orphans(accepted: dict, card_ids) -> list[str]:
    """复核豁免名单必须闭合：指向不存在的卡即报错。"""
    ids = set(card_ids)
    union = set()
    for key in ('short_back', 'deictic_echo_ok'):
        union |= set(accepted.get(key, []))
    return sorted(union - ids)


def starts_deictic(text: str) -> bool:
    t = strip_tags(text)
    return any(t.startswith(d) for d in DEICTIC_START)


def analyze():
    accepted = load_accepted()
    acc_short = set(accepted.get('short_back', []))
    acc_deictic = set(accepted.get('deictic_echo_ok', []))
    anchors = bc.load_anchors()
    cards = bc.collect_cards(anchors)
    n_ov, orphans, ov_conflicts, ov_problems = bc.apply_overrides(cards)
    ref_warnings = bc.convert_cards(cards, anchors)
    # 复核豁免键同样支持题 ID：裸 qid（全局唯一时）与限定 `q-…@book`（O2/R 批 2026-10）
    ids = ({c["id"] for c in cards}
           | {c["qid"] for c in cards if c.get("qid")}
           | {f"{c['qid']}@{c['book']}" for c in cards if c.get("qid")})

    anchor_missing = [c for c in cards if not c.get("anchor")]
    empty_back = [c["id"] for c in cards if not strip_tags(c.get("back_html"))]
    short_back = [(c["id"], len(strip_tags(c.get("back_html"))))
                  for c in cards if strip_tags(c.get("back_html")) and
                  len(strip_tags(c.get("back_html"))) < MIN_BACK.get(c["deck"], 40)]
    echo_missing = [c["id"] for c in cards
                    if c["deck"] in ("myth", "quiz") and not strip_tags(c.get("echo_html"))]
    deictic = [c["id"] for c in cards if c["deck"] == "myth" and starts_deictic(c.get("back_html"))]
    deictic_open = [i for i in deictic if i not in acc_deictic]
    short_open = [(i, n) for i, n in short_back if i not in acc_short]
    front_dupes = {}
    for c in cards:
        key = strip_tags(c.get("front_html"))
        front_dupes.setdefault(key, []).append(c["id"])
    dupes = {k: v for k, v in front_dupes.items() if len(v) > 1}

    by_deck = {}
    for c in cards:
        by_deck.setdefault(c["deck"], 0)
        by_deck[c["deck"]] += 1
    acc_orphans = waiver_orphans(accepted, ids)

    artifact = {}
    if not (bc.CARDS_HTML.exists() and bc.CARDS_TSV.exists()):
        artifact_bad = "missing"  # 产物缺失必须致命（旧逻辑跳过检查→空转绿，2026-10-02 修复）
    else:
        h = bc.CARDS_HTML.read_text(encoding="utf-8")
        artifact["html_cards"] = len(re.findall(r'\{"id":"', h))
        artifact["tsv_rows"] = sum(1 for _ in bc.CARDS_TSV.open(encoding="utf-8")) - 1
        artifact_bad = None
        hc, tr = artifact.get("html_cards"), artifact.get("tsv_rows")
        if hc is not None and tr is not None and (hc != tr or hc != len(cards)):
            artifact_bad = (hc, tr, len(cards))

    return dict(cards=cards, by_deck=by_deck, n_ov=n_ov, orphans=orphans,
                ov_conflicts=ov_conflicts, ov_problems=ov_problems,
                artifact_bad=artifact_bad,
                anchor_missing=anchor_missing, ref_warnings=ref_warnings,
                empty_back=empty_back, short_back=short_back, echo_missing=echo_missing,
                acc_orphans=acc_orphans,
                deictic=deictic, deictic_open=deictic_open,
                short_open=short_open, acc_short=len(acc_short), acc_deictic=len(acc_deictic),
                dupes=dupes, artifact=artifact)


def report_text(r) -> str:
    L = []
    L.append('# 学习卡清晰度报告（check_cards.py）')
    L.append('')
    L.append('## 计数')
    per = {}
    for c in r["cards"]:
        per.setdefault(c["deck"], {})
        per[c["deck"]][c["book_label"]] = per[c["deck"]].get(c["book_label"], 0) + 1
    for deck, cnt in sorted(per.items()):
        L.append(f'- {deck}: {sum(cnt.values())}（' +
                 '、'.join(f'{k} {v}' for k, v in cnt.items()) + '）')
    L.append(f'- 覆盖：{r["n_ov"]} 张')
    L.append('')
    L.append('## 致命/需处理')
    L.append(f'- 空背面：{len(r["empty_back"])} {r["empty_back"][:8]}')
    L.append(f'- override 孤儿：{len(r["orphans"])} {r["orphans"][:8]}')
    L.append(f'- override 冲突/重复 qid（失败项）：{len(r["ov_conflicts"])} {r["ov_conflicts"][:8]}')
    L.append(f'- override 配置问题（未知字段/非对象，仅报告）：'
             f'{len(r["ov_problems"])} {r["ov_problems"][:5]}')
    L.append(f'- 正面重复：{len(r["dupes"])} 组')
    L.append(f'- 复核豁免孤儿（cards_review.json 指向不存在的卡）：'
             f'{len(r["acc_orphans"])} {r["acc_orphans"][:8]}')
    L.append(f'- 产物一致性（cards.html 内嵌 / TSV 行 / 卡片数）：'
             f'{r["artifact_bad"] or "一致"}')
    L.append('')
    L.append('## 来源与引用')
    L.append(f'- 来源锚点缺失：{len(r["anchor_missing"])}')
    for c in r["anchor_missing"][:20]:
        L.append(f'  - {c["id"]}（{c["deck"]}·{c["book_label"]}）'
                 f' 章节={c.get("chapter")} 来源={c.get("source_label")}')
    L.append(f'- § 引用未解析：{len(r["ref_warnings"])} 处')
    for cid, field, secs in r["ref_warnings"][:30]:
        L.append(f'  - {cid} [{field}] §{sorted(set(secs))}')
    L.append('')
    L.append('## 自含性（人工校对队列）')
    L.append(f'- 回显缺失（误解/自检）：{len(r["echo_missing"])} {r["echo_missing"][:8]}')
    L.append(f'- 误解纠正以指代开头：{len(r["deictic_open"])} 未复核'
             f'（已复核接受 {r["acc_deictic"]}）{r["deictic_open"][:12]}')
    L.append(f'- 背面过短（core/myth/quiz<40、term<8）：{len(r["short_open"])} 未复核'
             f'（已复核接受 {r["acc_short"]}）')
    for cid, n in r["short_open"][:20]:
        L.append(f'  - {cid}（{n} 字）')
    L.append('')
    L.append('## 产物一致性')
    L.append(f'- cards.html 内嵌卡片：{r["artifact"].get("html_cards")}')
    L.append(f'- TSV 数据行：{r["artifact"].get("tsv_rows")}')
    L.append(f'- 模型卡片数：{len(r["cards"])}')
    return '\n'.join(L) + '\n'


def _selftest() -> int:
    ok = True
    def case(name, cond):
        nonlocal ok
        print(('PASS ' if cond else 'FAIL ') + name)
        ok = ok and cond
    case('orphan detection', detect_orphans(['a', 'b'], ['b', 'c']) == ['a'])
    case('waiver closure', waiver_orphans({'short_back': ['x']}, ['y']) == ['x'])
    case('waiver closed', waiver_orphans({'short_back': ['y']}, ['y']) == [])
    case('deictic detection', starts_deictic('<div>两者是同一个东西</div>'))
    case('deictic negative', not starts_deictic('梯度下降是走路策略'))
    # § 链接诊断：不存在的 §9.9 必须报未解析
    anchors = bc.load_anchors()
    _, un = bc.link_section_refs('见 §9.9。', anchors, 'doc-1')
    case('unresolved ref detection', '9.9' in un)
    _, un2 = bc.link_section_refs('见 §1.1。', anchors, 'doc-1')
    case('resolved ref detection', not un2)
    print('check_cards selftest:', 'all pass' if ok else 'FAILED')
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description='学习卡校验与清晰度报告')
    ap.add_argument('--report', default=None, help='报告输出路径（默认只打印摘要）')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    r = analyze()
    text = report_text(r)
    if args.report:
        Path(args.report).write_text(text, encoding='utf-8')
        print(f'报告 → {args.report}')
    print(text.split('## 致命/需处理')[1].split('## 来源与引用')[0].strip())
    fatal = bool(r['empty_back'] or r['orphans'] or r['dupes'] or r['acc_orphans']
                or r['artifact_bad'] or r['ov_conflicts'])
    return 1 if fatal else 0


if __name__ == '__main__':
    raise SystemExit(main())
