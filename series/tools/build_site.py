#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""series 阅读版 HTML 构建（从 0 新建；仅 stdlib ＋ pandoc ＋ series/tools/sub_sup_convert）。

设计（2026-10-12 全案并行，B1 落地）：
- 页面模型：Hub（index）＋按章分页（<slug>.html）＋全文打印页（print.html）＋资产索引（assets.html）
- 单章管线：读源稿 → sub_sup 字形转换 → 结构规范化 → 标记（▽○◌◇）预扫
  （剥离字形→徽章 span＋锚点注入 {#slug-sNN}）→ pandoc(markdown-smart) →
  cb 行号 id 加章前缀 → §N 素文链接化（章级，精确匹配）→ assets 路径链接化
  → 章尾 prev/next＋资产卡 → 页壳装配。
- 锚点＝序号制稳定锚（ch<slug>-sNN[-M]）：文本编辑不动锚，增删节触发
  anchors.json 漂移（由 series_check.py 对照 git 历史门禁）。
- 路线层：profiles/routes.json 路线库（2026-10-14 取代三维组合网格）；默认＝自由读
  （变灰/折叠），页内内嵌数据块（剥 `_` 键），运行时 JS 镜像 resolve 切换路径；
  Hub ＝向导/路线图/课表/双进度环/检索；章页 ＝ 档位行/深浅开关/已读/部末提醒。
- B5：depth×节标记（实践档 ○/◌ 节降灰、理论档全亮）与 focus 章非焦点节降灰；
  降灰带 kind（path/depth/focus）供样式与提示分型。
- 无 KaTeX（系列无 $ 数学）、无 npm、file:// 全功能（零外部请求）。
- 打印：print.html 构建期 details 全开；章页 beforeprint JS 展开。

用法：
    python3 series/tools/build_site.py                 # 全量构建（含 assets 拷贝/print/index/anchors）
    python3 series/tools/build_site.py --only ch16 t2  # 只重建指定页（不碰 print/index/anchors/assets）
    python3 series/tools/build_site.py --no-assets     # 跳过资产拷贝（调试）
"""

from __future__ import annotations

import argparse
import math
import datetime
import hashlib
import html as H
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent          # series/tools
SERIES = HERE.parent                            # series/
DIST = SERIES / "dist"
PROFILES = SERIES / "profiles"
ASSETS = SERIES / "assets"
TEMPLATE = HERE / "site_template.html"


def _load_release() -> dict:
    """发布元数据（版本/固定构建日期）；缺失时回退空表。"""
    p = PROFILES / "release.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


RELEASE = _load_release()

sys.path.insert(0, str(HERE))
import sub_sup_convert as ssc  # noqa: E402

MARK_CHARS = "▽○◌◇"
MARK_META = {"▽": "可后读", "○": "支线先补", "◌": "延伸选读", "◇": "主线依赖"}

_HEAD_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_HR_RE = re.compile(r"^\s*(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})\s*$")
_SUMMARY_RE = re.compile(r"^(\s*<summary>)(.*?)(</summary>\s*)$")
_MARK_RUN = re.compile(r"[▽○◌◇](?:\s*[＋+]\s*[▽○◌◇])*")
_ID_TAIL = re.compile(r"\s*\{#[^}]*\}\s*$")

_REF_RE = re.compile(r"§(0\.[123]|\d{1,2})(?![\d.．])")
_ASSET_DIR_S = r"(?:§\d+[a-z]?-体验实验|T\d-体验实验)"
_ASSET_RE = re.compile(
    r"(?:series/)?assets/" + _ASSET_DIR_S + r"(?:/[^\s`<>（）()「」『』“”\"'。，、；：！？]*)?"
)


# ---------------------------------------------------------------- 源稿层

def norm_structure(text: str) -> str:
    """结构规范化（mdprep 思想的本仓最小版）：分隔符统一 ＋ 标题行前补空行（围栏内不动）。"""
    out: list[str] = []
    fence = False
    for ln in text.split("\n"):
        if _FENCE_RE.match(ln):
            fence = not fence
            out.append(ln)
            continue
        if not fence:
            if _HR_RE.match(ln) and ln.strip() != "***":
                ln = "***"
            prev = out[-1] if out else ""
            if prev.strip() and (_HR_RE.match(ln) or _HEAD_RE.match(ln)):
                if not _HR_RE.match(prev) and not _HEAD_RE.match(prev):
                    out.append("")
        out.append(ln)
    return "\n".join(out)


def strip_marks(s: str) -> tuple[str, list[str]]:
    """剥离标题/摘要里的读法标记字形，返回（清洁文字, 标记序列）。"""
    ms: list[str] = []

    def cb(m: re.Match) -> str:
        ms.extend(c for c in m.group(0) if c in MARK_CHARS)
        return ""

    t = _MARK_RUN.sub(cb, s)
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"\s+([：:；;，,。．])", r"\1", t)
    return t.strip(), list(dict.fromkeys(ms))


def badge_html(ms: list[str]) -> str:
    return " ".join(
        f'<span class="mk mk-{c}" title="{MARK_META[c]}">{c}</span>' for c in ms)


def reading_metrics(md: str) -> tuple[int, int]:
    """→（正文字符数, 分钟数）。口径同 B1：去围栏/标签/链接标记，约 350 字/分钟。"""
    s = re.sub(r"```.*?```", "", md, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"[#>*_`|\-~\s〔〕]", "", s)
    n = len(s)
    return n, max(1, round(n / 350))


def reading_stats(md: str) -> str:
    n, mins = reading_metrics(md)
    amount = f"{n / 10000:.1f} 万字" if n >= 10000 else f"{n} 字"
    return f"{amount} · 约 {mins} 分钟"


def section_mins_map(md: str, sections: list[dict]) -> dict[str, int]:
    """按 h2 切分，估算各节阅读分钟（口径同 reading_metrics；focus 章节点显示焦点节合计）。"""
    parts = re.split(r"^## ", md, flags=re.M)
    h2s = [s for s in sections if s["level"] == 2]
    out: dict[str, int] = {}
    for i, sec in enumerate(h2s, start=1):
        body = parts[i] if i < len(parts) else ""
        out[sec["anchor"]] = max(1, reading_metrics("## " + body)[1])
    return out


# ---------------------------------------------------------------- B3 路径层

def strip_underscore(obj):
    """递归剥内部注记键（`_` 前缀，B3 内嵌前剥离）。"""
    if isinstance(obj, dict):
        return {k: strip_underscore(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [strip_underscore(v) for v in obj]
    return obj


def load_routes() -> dict:
    return json.loads((PROFILES / "routes.json").read_text(encoding="utf-8"))


def route_view(route: dict, chapters: list[dict]) -> dict:
    """路线视图：sequence（read/focus）→ 全书处置；未列入的章＝skip（自由读中仍可翻开）。

    → {"disp": {slug: "read"|"dim"|{"focus":[anchors]}},
       "dim_sections": {anchor: {"reason","kind":"focus"}},
       "counts": {"main": n, "branch": n}, "open": bool}
    """
    seq = {e["ch"]: e for e in route.get("sequence", [])}
    disp: dict = {}
    for c in chapters:
        e = seq.get(c["slug"])
        if e is None:
            disp[c["slug"]] = "dim"
        elif e["mode"] == "read":
            disp[c["slug"]] = "read"
        else:
            disp[c["slug"]] = {"focus": list(e.get("sections", []))}
    dim_sections: dict[str, dict] = {}
    sections_of = {c["slug"]: [s["anchor"] for s in c["sections"]] for c in chapters}
    for slug, d in disp.items():
        if isinstance(d, dict):
            foc = set(d["focus"])
            for a in sections_of.get(slug, []):
                if a not in foc:
                    dim_sections[a] = {"reason": "本路线只读所列节", "kind": "focus"}
    counts = {"main": 0, "branch": 0}
    for c in chapters:
        if disp[c["slug"]] == "dim":
            continue
        counts["branch" if c["part"] == "branch" else "main"] += 1
    cards = {c["anchor"]: c["text"] for c in route.get("cards", [])}
    seq_list = [e["ch"] for e in route.get("sequence", [])]
    nxt = {seq_list[i]: seq_list[i + 1] for i in range(len(seq_list) - 1)}
    pos = {slug: i + 1 for i, slug in enumerate(seq_list)}
    return {"disp": disp, "dim_sections": dim_sections, "counts": counts,
            "open": bool(route.get("open_default")), "cards": cards, "next": nxt,
            "pos": pos, "total": len(seq_list)}


def free_view(chapters: list[dict]) -> dict:
    """自由读（默认态）：全 30 章全亮、无节级降灰、折叠默认收起。"""
    return {"disp": {c["slug"]: "read" for c in chapters},
            "dim_sections": {},
            "counts": {"main": sum(1 for c in chapters if c["part"] != "branch"),
                       "branch": sum(1 for c in chapters if c["part"] == "branch")},
            "open": False, "cards": {}, "next": {}, "pos": {}, "total": 0}


def route_pathline(route: dict | None) -> str:
    """章页路径行内容：自由读＝「自由读」；否则路线名＋换路线链接（外层 div#pathLine 由模板提供）。"""
    label = "自由读" if route is None else H.escape(route["title"])
    return f'{label} · <a href="index.html">换路线</a>'
def wrap_sections(html: str) -> str:
    """按 h2 切分并包 <section class="sec" data-anchor="…">（H1/导语在首节之前，不包）。

    details 不跨节是断言（跨节即坏结构，构建报错）。
    """
    parts = re.split(r'(<h2 id="([^"]+)"[^>]*>)', html)
    out: list[str] = [parts[0]]
    for i in range(1, len(parts), 3):
        tag, anchor = parts[i], parts[i + 1]
        body = parts[i + 2] if i + 2 < len(parts) else ""
        if body.count("<details") != body.count("</details>"):
            raise RuntimeError(f"details 跨节：{anchor}")
        out.append(f'<section class="sec" data-anchor="{anchor}">{tag}{body}</section>')
    return "".join(out)


def apply_section_dim(html: str, dim_map: dict) -> str:
    def repl(m: re.Match) -> str:
        anchor = m.group(1)
        info = dim_map.get(anchor)
        if info is not None:
            why = H.escape(info.get("reason", ""), quote=True)
            kind = H.escape(info.get("kind", "path"), quote=True)
            return (f'<section class="sec dim" data-anchor="{anchor}" '
                    f'data-why="{why}" data-kind="{kind}">')
        return f'<section class="sec" data-anchor="{anchor}">'
    return re.sub(r'<section class="sec" data-anchor="([^"]+)">', repl, html)


def migration_callout(ch: dict) -> str:
    """部末章（ch09/14/21）章尾提醒：指向章末含「十题自查」的末节
    （ch21 的十题在 s08「深究：给一篇论文分级」内，不是 s07「三件事」；
    原按「回望/三件事」找节会指错，2026-10-14 修为「取末节」）。"""
    if ch["slug"] not in ("ch09", "ch14", "ch21"):
        return ""
    h2s = [s for s in ch["sections"] if s["level"] == 2]
    if not h2s:
        raise RuntimeError(f"迁移提醒目标节未找到：{ch['slug']}")
    target = h2s[-1]
    return (f'<div class="migration"><b>部末提醒：</b>读完记得做'
            f'<a href="#{target["anchor"]}">部末十题自查</a>（本章三题＋前章回话题）。</div>')


def build_site_data(chapters: list[dict], parts: list[dict], routes: dict,
                    views: dict[str, dict]) -> str:
    """页内数据块（Hub＋章页共用；print/assets 不注）。schema series-site-data/v2。"""
    data = {
        "schema": "series-site-data/v2",
        "default_route": routes.get("default_route", "free"),
        "routes": [dict(r, view=views[r["id"]]) for r in routes["routes"]],
        "rhythm": strip_underscore(routes.get("rhythm", {})),
        "parts": [{"id": p["id"], "label": p["label"]} for p in parts],
        "chapters": [
            {"slug": c["slug"], "label": c["label"], "title": c["title"], "part": c["part"],
             "mins": c["mins"], "sec_mins": c.get("sec_mins", {}),
             "sections": [{"anchor": s["anchor"], "text": s["text"], "level": s["level"],
                           "markers": s["markers"]}
                          for s in c["sections"]]}
            for c in chapters],
    }
    js = json.dumps(strip_underscore(data), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/json" id="series-data">{js}</script>'


ROUTER_GOALS = [("undecided", "还没定，先看看"), ("agent", "应用与智能体（Agent）"),
                ("train", "训练与调参"), ("gen", "生成方向（扩散）"), ("research", "研究与理论")]
ROUTER_TIMES = [("halfday", "一次半天"), ("fast", "两三周集中投入"),
                ("slow", "几个月稳步推进"), ("endless", "长期，越多越好")]


def hub_content(chapters: list[dict], parts: list[dict], routes: dict,
                free: dict) -> str:
    """Hub＝两个问题路由＋路线卡墙＋自由读卡＋节奏示例＋进度环＋检索。默认＝自由读。"""
    out: list[str] = []
    out.append('<div class="hero"><h1>AI 系列读物 · 阅读版</h1>'
               '<p class="doc-meta">24 章主线＋支线六页。应用与 Agent、训练、生成、研究'
               '四条完整线，另有三条快线、尝鲜速览与深究线；也可以随时自由读。'
               '检索用本页底部搜索框或 <a href="print.html">全文版</a>（Ctrl+F）；'
               '查词用 <a href="terms.html">术语总表</a>；上手前看 <a href="env.html">环境指南</a>，'
               '拿不准数学底子做 <a href="selftest.html">数学自修自测</a>；'
               '路线全文与论文清单见 <a href="routes.html">路线卡</a>。</p></div>')
    out.append('<div class="legend">' + " ".join(
        f'<span class="item"><b>{k}</b> {v}</span>' for k, v in MARK_META.items()) + "</div>")
    out.append('<div class="resume" id="resumeBlock" hidden>'
               '<a class="resume-link" id="resumeLink" href="#"></a>'
               '<ul class="recent" id="recentList"></ul></div>')
    out.append('<div class="hub-nav" aria-label="页面分区">'
               '<a href="#hub-start">开始</a> · <a href="#hub-map">路线图</a> · '
               '<a href="#hub-mine">我的</a> · <a href="#hub-ref">参考</a></div>')
    out.append('<section class="hub-sec" id="hub-start"><h2 class="hub-h">开始</h2>')

    # ---- 两个问题 → 推荐路线（JS 落地映射）
    out.append('<div class="wizard" id="router">')
    out.append('<div class="wiz-title">两个问题，推荐一条路线（可随时改）</div>')
    out.append('<div class="wiz-group"><span class="wiz-label">你想用 AI 做什么？</span>'
               f'<select id="routerGoal" aria-label="你想用 AI 做什么">'
               + "".join(f'<option value="{k}">{v}</option>' for k, v in ROUTER_GOALS)
               + '</select></div>')
    out.append('<div class="wiz-group"><span class="wiz-label">你能投入多少时间？</span>'
               f'<select id="routerTime" aria-label="你能投入多少时间">'
               + "".join(f'<option value="{k}">{v}</option>' for k, v in ROUTER_TIMES)
               + '</select></div>')
    out.append(f'<div class="wiz-result" id="routerResult" aria-live="polite"></div>')
    out.append('<div class="selftest-note" id="selftestNote"></div>')
    out.append('<a class="router-start" id="routerStart" hidden href="#"></a></div>')

    # ---- 路线卡墙（自由读卡打头）
    out.append('<div class="route-cards" id="routeCards">')
    out.append('<a class="route-card" data-route="free" href="routes.html#route-free">'
               '<span class="rc-t">自由读</span><span class="rc-tag">默认</span>'
               '<span class="rc-aud">不选路线，30 页全亮，按顺序或按兴趣翻</span>'
               '<span class="rc-exit">出口：无（自由读没有出口承诺，走到哪算哪）</span>'
               '<span class="rc-hours">读 ≈9 小时（全书）· 折叠块默认收起</span></a>')
    for r in routes["routes"]:
        ex = "；".join(r["exit"][:3])
        hrs = (f'读 ≈{r["hours"]["read"]}h ＋ 练 ≈{r["hours"]["practice"]}h'
               f' ＋ 项目 ≈{r["hours"]["project"]}h')
        n_read = sum(1 for e in r["sequence"] if e["mode"] == "read")
        n_focus = len(r["sequence"]) - n_read
        skip = len(chapters) - len(r["sequence"])
        plan = (f'读 {n_read} 章' + (f'（焦点 {n_focus}）' if n_focus else '')
                + (f'＋跳 {skip} 页' if skip else ''))
        out.append(f'<a class="route-card" data-route="{r["id"]}" href="routes.html#route-{r["id"]}">'
                   f'<span class="rc-t">{H.escape(r["title"])}</span>'
                   f'<span class="rc-tag">{H.escape(r["tag"])}</span>'
                   f'<span class="rc-aud">{H.escape(r["audience"])}</span>'
                   f'<span class="rc-plan">{H.escape(plan)}</span>'
                   f'<span class="rc-exit">出口：{H.escape(ex)}</span>'
                   f'<span class="rc-hours">{H.escape(hrs)} · {H.escape(r["pace_note"])}</span></a>')
    out.append('</div>')

    out.append('</section>')
    # ---- 路线图（30 节点；JS 按所选路线更新类）
    out.append('<section class="hub-sec" id="hub-map"><h2 class="hub-h">路线图</h2>')
    out.append('<div class="route" id="route">')
    for part in parts:
        items = [c for c in chapters if c["part"] == part["id"]]
        if not items:
            continue
        out.append(f'<div class="route-part">{H.escape(part["label"])}</div>')
        if part["id"] == "branch":
            out.append('<div class="route-note">由 §9 章末进（导言 → 配方 → T1–T4）；'
                       '不走生成方向的读者可直接过 §10。</div>')
        for c in items:
            out.append(f'<a class="node" data-slug="{c["slug"]}" data-mins="{c["mins"]}" '
                       f'href="{c["slug"]}.html">'
                       f'<span class="node-t">{H.escape(c["label"])} {H.escape(short_title(c["title"], 34))}</span>'
                       f'<span class="node-mins">{c["mins"]} 分钟</span></a>')
    out.append('</div>')

    out.append('<div class="route-note" id="offrouteNote" hidden></div>')
    out.append('</section>')
    # ---- 我的（进度/自证/导出）
    out.append('<section class="hub-sec" id="hub-mine"><h2 class="hub-h">我的</h2>')

    # ---- 双进度环
    out.append('<div class="rings">')
    out.append('<div class="ring" id="ringMain"><svg viewBox="0 0 36 36">'
               '<circle class="ring-bg" cx="18" cy="18" r="15.9"></circle>'
               '<circle class="ring-fg" id="ringMainFg" cx="18" cy="18" r="15.9"></circle></svg>'
               '<div class="ring-txt"><b id="ringMainN">0/24</b><span>主线已读</span></div></div>')
    out.append('<div class="ring" id="ringBranch"><svg viewBox="0 0 36 36">'
               '<circle class="ring-bg" cx="18" cy="18" r="15.9"></circle>'
               '<circle class="ring-fg" id="ringBranchFg" cx="18" cy="18" r="15.9"></circle></svg>'
               '<div class="ring-txt"><b id="ringBranchN">0/6</b><span>支线已读</span></div></div>')
    out.append('</div>')
    out.append('<div class="exit-line" id="exitLine" aria-live="polite" hidden></div>')
    out.append('<label class="focus-toggle"><input type="checkbox" id="focusHideHub"> '
               '隐藏非路线内容（侧栏/路线图/章内）</label>')
    out.append('<div class="review" id="reviewBlock" hidden>'
               '<div class="sched-sub">复习</div>'
               '<p class="doc-meta">从已读的章里抽一章，做章末自查题。</p>'
               '<ul id="reviewList"></ul>'
               '<button type="button" id="reviewRefresh">换一批</button></div>')

    # ---- 我的进度（导出/导入，H2-5）
    out.append('<div class="progress-io" id="progressIO">'
               '<div class="sched-sub">我的进度（存本机）</div>'
               '<p class="doc-meta" id="progSummary"></p>'
               '<textarea id="progText" rows="4" aria-label="进度 JSON" '
               'placeholder="导出后复制这段；导入时粘贴到这里再点导入"></textarea>'
               '<div class="prog-btns">'
               '<button type="button" id="progExport">导出（生成 JSON）</button> '
               '<button type="button" id="progImport">导入（粘贴后点）</button> '
               '<span id="progMsg" class="doc-meta" aria-live="polite"></span></div></div>')

    out.append('</section>')
    # ---- 参考（节奏/检索）
    out.append('<section class="hub-sec" id="hub-ref"><h2 class="hub-h">参考</h2>')
    sch = routes.get("rhythm", {})
    a, b = sch.get("courseA", {}), sch.get("courseB", {})
    lab = {c["slug"]: c["label"] for c in chapters}
    out.append('<div class="schedule" id="schedule">')
    out.append('<div class="sched-sub">节奏示例（完整线用）</div><ul>')
    out.append(f'<li><b>{H.escape(a.get("label", ""))}</b>（{a.get("weeks", "?")} 周）：'
               f'{H.escape(a.get("note", ""))}</li>')
    out.append(f'<li><b>{H.escape(b.get("label", ""))}</b>（{b.get("weeks", "?")} 周）：'
               f'{H.escape(b.get("note", ""))}</li>')
    out.append('</ul><div class="sched-sub">里程碑</div><ul>')
    for m in sch.get("milestones", []):
        links = "、".join(f'<a href="{s}.html">{H.escape(lab[s])}</a>' for s in m["chapters"])
        out.append(f'<li><b>{H.escape(m["weeks"])}</b> {H.escape(m["text"])}（{links}）</li>')
    out.append('</ul>')
    st = sch.get("stations", {})
    slinks = "、".join(f'<a href="{s}.html">{H.escape(lab[s])}</a>' for s in st.get("chapters", []))
    out.append(f'<div class="sched-sub">{H.escape(st.get("label", ""))}</div>'
               f'<p>{H.escape(st.get("note", ""))}（{slinks}）</p>')
    out.append('<div class="sched-sub">结业四件</div><ul>')
    for pr in sch.get("projects", []):
        out.append(f'<li><input type="checkbox" id="proj-{pr["id"]}" data-pid="{pr["id"]}"> '
                   f'<label for="proj-{pr["id"]}">{H.escape(pr["label"])}</label>'
                   f'（<a href="{pr["chapter"]}.html">{H.escape(lab[pr["chapter"]])}</a>）</li>')
    out.append('</ul><div class="exit-line" id="projLine" aria-live="polite" hidden></div></div>')

    # ---- 检索
    out.append('<div class="search-area"><input type="search" id="hubSearch" '
               'placeholder="搜章节与节标题…（如：幂律、KV 显存）" autocomplete="off">'
               '<div class="search-results" id="searchResults" style="display:none"></div></div>')
    out.append('</section>')
    return "\n".join(out)
# ---------------------------------------------------------------- 供给页（批 4）

FOOTER_LINKS = ('<a href="index.html">目录</a> · <a href="print.html">全文打印版</a> · '
                '<a href="terms.html">术语总表</a> · <a href="routes.html">路线与论文清单</a> · '
                '<a href="env.html">环境指南</a> · <a href="selftest.html">数学自修自测</a> · '
                '<a href="assets.html">资产索引</a>')


def route_weeks_text(hrs: dict) -> str:
    """三档节奏估算（每周 5/10/15h → 周数；含练习与项目）。"""
    total = hrs["read"] + hrs["practice"] + hrs["project"]
    return "｜".join(f"每周 {p}h≈{max(1, math.ceil(total / p))} 周" for p in (5, 10, 15))


def _sec_short(text: str, n: int = 10) -> str:
    """节名短形：冒号前 + 截断（路线卡与打印页共用）。"""
    s = text.split("：")[0]
    return s if len(s) <= n else s[:n] + "…"


def footer_html(build_date: str, prefix: str = "") -> str:
    ver = f"v{RELEASE['version']} · " if RELEASE.get("version") else ""
    head = f"{ver}构建 {build_date}" + (f" · {prefix}" if prefix else "")
    return f"{head} · {FOOTER_LINKS}"


ENV_VERIFIED = "2026-10-14"   # 环境指南最后验证日期（重核后更新）


def _slug_of_label(lab: str, chapters: list[dict]) -> str | None:
    lab = (lab or "").strip()
    if lab.startswith("§"):
        num = lab[1:].strip()
        if num.startswith("0."):
            return {"0.1": "s0a", "0.2": "s0b", "0.3": "s0c"}.get(num)
        if num.isdigit():
            return f"ch{int(num):02d}"
        return None
    if len(lab) >= 2 and lab[0] == "T" and lab[1:].isdigit():
        return f"t{lab[1:]}"
    for c in chapters:
        if c["label"] == lab:
            return c["slug"]
    return None


def _ref_anchor(tok: str, chapters: list[dict]) -> str:
    slug = _slug_of_label(tok, chapters)
    if not slug:
        return H.escape(tok)
    return f'<a class="xref" href="{slug}.html">{H.escape(tok)}</a>'


def _link_refs_inline(s: str, chapters: list[dict]) -> str:
    esc = H.escape(s)
    return re.sub(r"(§0\.\d|§\d{1,2}|T[1-4])", lambda m: _ref_anchor(m.group(1), chapters), esc)


def _read_tsv_rows(path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    if not path.exists():
        return rows
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        cols = [c.strip() for c in ln.split("\t")]
        if len(cols) >= 2 and cols[0] != "名词":
            rows.append(cols)
    return rows


_PROC_TOKENS = re.compile(
    r"（[^（）]*(?:冷审|R\d+-\d+|F\d+|兑付站|P\d 批|主编裁决|源书引注|仅存档案)[^（）]*）"
    r"|；?\s*(?:冷审|R\d+-\d+|F\d+|P\d 批补登记|2026-\d+-\d+ P\d 批补登记)[^；]*"
    r"|，?以源书引注为准|【[^】]*删除[^】]*】")


def _clean_note(s: str) -> str:
    """术语页防泄漏：剥编辑过程注记（台账原档不动）。"""
    s = _PROC_TOKENS.sub("", s)
    s = re.sub(r"；{2,}", "；", s).strip("； ")
    return s


def _term_anchor(name: str) -> str:
    return "term-" + hashlib.md5(name.encode("utf-8")).hexdigest()[:10]


def terms_items(chapters: list[dict]) -> list[tuple[str, str, str]]:
    """术语条目（台账＋提案，同名以台账为准，废条剔除）→ [(名词, 首现章, 备注)]。"""
    rows = _read_tsv_rows(SERIES / "edit" / "术语总账.tsv")
    items: list[tuple[str, str, str]] = []
    index: dict[str, int] = {}
    for cols in rows:
        name = cols[0]
        if not name:
            continue
        note = "；".join(c for c in cols[2:] if c)
        if ("删除" in note and "档案" in note) or "已并入" in note or "撤名退役" in note:
            continue  # 已删/已并/撤名的废条不入读者面
        index[name] = len(items)
        items.append((name, cols[1] if len(cols) > 1 else "", note))
    seen_names = {it[0] for it in items}
    for prop in sorted((SERIES / "edit").glob("*.术语登记提案.tsv")):
        for cols in _read_tsv_rows(prop):
            name = cols[0]
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            items.append((name, cols[1] if len(cols) > 1 else "",
                          "；".join(c for c in cols[2:] if c)))
    order = {c["slug"]: i for i, c in enumerate(chapters)}
    items.sort(key=lambda it: (order.get(_slug_of_label(it[1], chapters) or "", 99), it[0]))
    return items


def chapter_terms_block(slug: str, items: list[tuple[str, str, str]], chapters: list[dict]) -> str:
    """章页文末「本章新词」折叠块（按台账首现章）。"""
    mine = [(n, f, note) for (n, f, note) in items if _slug_of_label(f, chapters) == slug]
    if not mine:
        return ""
    lis = "".join(
        f'<li><a href="terms.html#{_term_anchor(n)}">{H.escape(n)}</a></li>' for n, _, _ in mine)
    return (f'<details class="chapter-terms"><summary>本章新词（{len(mine)}）</summary>'
            f'<ul>{lis}</ul></details>')


def terms_content(chapters: list[dict]) -> str:
    items = terms_items(chapters)
    trs = []
    for name, first, note in items:
        slug = _slug_of_label(first, chapters)
        first_html = (f'<a class="xref" href="{slug}.html">{H.escape(first)}</a>'
                      if slug else H.escape(first))
        trs.append(f'<tr id="{_term_anchor(name)}"><td>{H.escape(name)}</td><td>{first_html}</td>'
                   f'<td>{_link_refs_inline(_clean_note(note), chapters)}</td></tr>')
    table = ('<table id="termTable"><thead><tr><th>名词</th><th>首现</th>'
             '<th>说明与门牌</th></tr></thead><tbody>' + "".join(trs) + "</tbody></table>")
    script = ('<script>(function(){var i=document.getElementById("termFilter");'
              'var t=document.getElementById("termTable");if(!i||!t)return;'
              'i.addEventListener("input",function(){var q=i.value.trim().toLowerCase();'
              'var rs=t.querySelectorAll("tbody tr");for(var k=0;k<rs.length;k++){'
              'rs[k].style.display=rs[k].textContent.toLowerCase().indexOf(q)>=0?"":"none";}});'
              'var qs="";try{qs=new URLSearchParams(location.search).get("q")||"";}catch(e){}'
              'if(qs){i.value=qs;i.dispatchEvent(new Event("input"));}'
              'try{if(location.hash){var tr=document.querySelector(location.hash);'
              'if(tr){tr.classList.add("term-hit");}}}catch(e){}'
              '})();</script>')
    return (f'<div class="chapter-head"><h1>术语总表</h1>'
            f'<p class="doc-meta">按词条收录全部术语与门牌，共 {len(items)} 条；'
            f'按首现章排序（同章按字序），「首现」可点跳章。筛词用下方输入框，或浏览器 Ctrl+F。回 <a href="index.html">目录</a>。</p></div>'
            f'<p><input type="search" id="termFilter" placeholder="筛词…（如：注意力、幂律、护栏）" '
            f'autocomplete="off" style="width:100%;max-width:460px;padding:6px 10px;'
            f'border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink)"></p>'
            + table + script)


def env_content(chapters: list[dict], ref_map: dict[str, str]) -> str:
    md = (SERIES / "supply" / "环境指南.md").read_text(encoding="utf-8")
    html = pandoc_html(md, SERIES)
    html, _ = linkify_assets(html)
    html, _ = linkify_refs(html, "env", ref_map, print_mode=False)
    rows = []
    for ch in chapters:
        d = asset_dir_of(ch["slug"])
        if not d:
            continue
        if (ASSETS / d / "预置笔记本.ipynb").is_file():
            rel = quote(f"{d}/预置笔记本.ipynb", safe="/")
            rows.append(f'<li><a class="asset" href="assets/{rel}">'
                        f'{H.escape(ch["label"])} 预置笔记本</a></li>')
    nb = ("<h2>笔记本清单一览</h2><ul>" + "".join(rows) + "</ul>") if rows else ""
    return html + nb


def selftest_content(ref_map: dict[str, str]) -> str:
    md = (SERIES / "supply" / "数学自修自测.md").read_text(encoding="utf-8")
    html = pandoc_html(md, SERIES)
    html, _ = linkify_refs(html, "selftest", ref_map, print_mode=False)
    opts = "".join(f'<option value="{i}">{i}</option>' for i in range(0, 11))
    widget = ('<div class="selftest-save">'
              '<label for="stScore">自评：对了几题？</label> '
              f'<select id="stScore"><option value="">—</option>{opts}</select> '
              '<button type="button" id="stSave">保存</button> '
              '<span id="stSaved" class="st-saved"></span></div>'
              '<p class="doc-meta">自己数、自己存；保存后首页的路线推荐会按你的情况多给一句提示（只存本机）。</p>')
    return html + widget


def routes_content(routes_cfg: dict, chapters: list[dict]) -> str:
    lab = {c["slug"]: c["label"] for c in chapters}
    sec_title = {s["anchor"]: s["text"] for c in chapters for s in c["sections"]}
    out = ['<div class="chapter-head"><h1>路线与论文清单</h1>'
           '<p class="doc-meta">九条路线的全文说明，可打印；每条含读法、出口、自证题、时数与补课卡。'
           '默认自由读，随时可换。回 <a href="index.html">目录</a>。</p></div>']
    out.append('<section class="route-full" id="route-free">'
               '<h2>自由读 <span class="rc-tag">默认</span></h2>'
               '<p class="doc-meta">不选路线：30 页全亮，按顺序或按兴趣翻；没有出口承诺，走到哪算哪。'
               '下面的九条路线是带出口与审计的推荐单，随时可切。</p></section>')
    for r in routes_cfg["routes"]:
        seq = r["sequence"]
        read = [lab[e["ch"]] for e in seq if e["mode"] == "read"]
        focus = []
        for e in seq:
            if e["mode"] != "focus":
                continue
            short = [_sec_short(sec_title.get(a, a.split("-")[-1])) for a in e.get("sections", [])]
            shown = "、".join(short[:3]) + ("…" if len(short) > 3 else "")
            focus.append(f'{lab[e["ch"]]}（{shown}）')
        skipped = len(chapters) - len(read) - len(focus)
        hrs = r["hours"]
        out.append(f'<section class="route-full" id="route-{r["id"]}">')
        out.append(f'<h2>{H.escape(r["title"])} <span class="rc-tag">{H.escape(r["tag"])}</span></h2>')
        weeks = route_weeks_text(hrs)
        out.append(f'<p class="doc-meta">{H.escape(r["audience"])}｜读 ≈{hrs["read"]}h ＋ '
                   f'练 ≈{hrs["practice"]}h ＋ 项目 ≈{hrs["project"]}h｜{H.escape(r["pace_note"])}｜'
                   f'预计：{weeks}（按标称时数估算，含练习与项目）</p>')
        out.append(f'<p class="doc-meta"><a href="route-{r["id"]}.html">打印本路线（单页）→</a></p>')
        out.append(f'<p><b>读完能：</b>{H.escape("；".join(r["exit"]))}</p>')
        checks = "".join(
            f'<label class="exit-check"><input type="checkbox" data-route="{r["id"]}" '
            f'data-idx="{i}"> {H.escape(s)}</label>'
            for i, s in enumerate(r["selfcheck"]))
        out.append(f'<p><b>自证题</b>（勾选只存本机）：</p><div class="exit-list">{checks}</div>')
        line = f'<p><b>读全章：</b>{H.escape("、".join(read)) or "—"}'
        if focus:
            line += f'；<b>只读所列节：</b>{H.escape("；".join(focus))}'
        if skipped > 0:
            line += f'；其余 {skipped} 页不读（自由读中仍可翻开）'
        out.append(line + "</p>")
        if r.get("catchups"):
            out.append('<p><b>补课卡：</b>' + H.escape("；".join(
                f'{c.get("where", "")}→{c.get("fix", "")}' for c in r["catchups"])) + '</p>')
        if r.get("exempt"):
            out.append('<p><b>豁免：</b>' + H.escape("；".join(r["exempt"])) + '</p>')
        out.append('</section>')
    out.append('<h2>论文清单（首批）</h2>'
               '<p>深究线与研究线用：候选论文五篇见 §21「深究：给一篇论文分级」的折叠框；'
               '分级卡按 §14 六类边界表的证据档位交付。发布批扩至十篇。</p>')
    out.append('<h2>节奏示例</h2><p>' + H.escape(routes_cfg["rhythm"]["courseA"]["note"]) + '；'
               + H.escape(routes_cfg["rhythm"]["courseB"]["note"]) + '</p>')
    return "\n".join(out)


def scan_and_rewrite(raw: str, slug: str) -> tuple[str, dict]:
    """标记预扫＋徽章注入＋锚点注入。返回（加工后 md, 扫描信息）。"""
    lines = raw.split("\n")
    out: list[str] = []
    fence = False
    h2i = h3i = 0
    info: dict = {"h1": "", "h1_markers": [], "sections": []}
    for ln in lines:
        if _FENCE_RE.match(ln):
            fence = not fence
            out.append(ln)
            continue
        if fence:
            out.append(ln)
            continue
        m = _HEAD_RE.match(ln)
        if m:
            hashes, body = m.group(1), _ID_TAIL.sub("", m.group(2))
            clean, ms = strip_marks(body)
            if len(hashes) == 1:
                anchor = slug
                info["h1"] = clean
                info["h1_markers"] = ms
            elif len(hashes) == 2:
                h2i += 1
                h3i = 0
                anchor = f"{slug}-s{h2i:02d}"
                info["sections"].append(
                    {"level": 2, "text": clean, "markers": ms, "anchor": anchor})
            elif len(hashes) == 3:
                h3i += 1
                anchor = f"{slug}-s{h2i:02d}-{h3i}"
                info["sections"].append(
                    {"level": 3, "text": clean, "markers": ms, "anchor": anchor})
            else:
                out.append(ln)
                continue
            badges = badge_html(ms)
            tail = f" {badges}" if badges else ""
            out.append(f"{hashes} {clean}{tail} {{#{anchor}}}")
            continue
        sm = _SUMMARY_RE.match(ln)
        if sm:
            head, body, tail = sm.groups()
            clean, ms = strip_marks(body)
            if ms:
                out.append(f"{head}{clean} {badge_html(ms)}{tail}")
            else:
                out.append(ln)
            continue
        out.append(ln)
    return "\n".join(out), info


def route_print_content(r: dict, chapters: list[dict]) -> str:
    """单路线打印页（H2-4）：构建期静态生成，file:// 下最稳。"""
    lab = {c["slug"]: c["label"] for c in chapters}
    sec_title = {s["anchor"]: s["text"] for c in chapters for s in c["sections"]}
    hrs = r["hours"]
    weeks = route_weeks_text(hrs)
    read, focus = [], []
    for e in r["sequence"]:
        if e["mode"] == "read":
            read.append(f'{lab[e["ch"]]}')
        else:
            titles = "、".join(_sec_short(sec_title.get(a, a.split("-")[-1]))
                               for a in e.get("sections", []))
            focus.append(f'{lab[e["ch"]]}（{titles}）')
    skipped = len(chapters) - len(read) - len(focus)
    out = [f'<div class="chapter-head"><h1>{H.escape(r["title"])}</h1>'
           f'<p class="doc-meta">{H.escape(r["audience"])}｜读 ≈{hrs["read"]}h ＋ 练 ≈{hrs["practice"]}h'
           f' ＋ 项目 ≈{hrs["project"]}h｜{H.escape(r["pace_note"])}｜预计：{weeks}</p>'
           f'<p class="doc-meta"><a href="routes.html#route-{r["id"]}">← 回路线卡</a> · '
           f'<a href="index.html">目录</a></p></div>']
    out.append(f'<h2>读全章（{len(read)}）</h2><p>{H.escape("、".join(read)) or "—"}</p>')
    if focus:
        out.append(f'<h2>只读所列节（{len(focus)}）</h2><p>{H.escape("；".join(focus))}</p>')
    if skipped > 0:
        out.append(f'<p class="doc-meta">其余 {skipped} 页不读（自由读中仍可翻开）。</p>')
    if r.get("catchups"):
        out.append('<h2>补课卡</h2><p>' + H.escape("；".join(
            f'{c.get("where", "")}→{c.get("fix", "")}' for c in r["catchups"])) + '</p>')
    if r.get("exempt"):
        out.append('<h2>豁免</h2><p>' + H.escape("；".join(r["exempt"])) + '</p>')
    out.append('<h2>读完能（出口）</h2><ul>' + "".join(
        f'<li>{H.escape(x)}</li>' for x in r["exit"]) + '</ul>')
    out.append('<h2>自证题</h2><ul>' + "".join(
        f'<li>{H.escape(x)}</li>' for x in r["selfcheck"]) + '</ul>')
    out.append('<p class="doc-meta">六站与结业项目按路线卡与正文；勾选进度在阅读版里（本页为打印版）。</p>')
    return "\n".join(out)


# ---------------------------------------------------------------- HTML 后处理层

def pandoc_html(md: str, cwd: Path) -> str:
    r = subprocess.run(
        ["pandoc", "-f", "markdown-smart", "-t", "html5", "--wrap=none"],
        input=md, capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0:
        raise RuntimeError("pandoc 失败：\n" + r.stderr[:2000])
    return r.stdout


def prefix_cb(html: str, slug: str) -> str:
    html = re.sub(r'id="(cb[0-9][^"]*)"', lambda m: f'id="{slug}-{m.group(1)}"', html)
    return re.sub(r'href="#(cb[0-9][^"]*)"', lambda m: f'href="#{slug}-{m.group(1)}"', html)


_SKIP_REF = re.compile(r"<(code|pre|a|style|script|h1)\b|</(code|pre|a|style|script|h1)>")


def linkify_refs(html: str, current: str, ref_map: dict[str, str], print_mode: bool) -> tuple[str, int]:
    """§N 素文链接化（章级；§N.M 形不链，计数上报）。"""
    parts = re.split(r"(<[^>]+>)", html)
    out: list[str] = []
    skip = 0
    skipped_sections = 0
    for p in parts:
        if p.startswith("<"):
            mo = _SKIP_REF.match(p)
            if mo:
                if p.startswith("</"):
                    skip = max(0, skip - 1)
                else:
                    skip += 1
            out.append(p)
            continue
        if skip:
            out.append(p)
            continue
        # 统计未链的节级引用（诚实报告，不打断；排除 §0.x 章级引用——它们会被链接化）
        skipped_sections += len(re.findall(r"§0\.\d\.\d|§(?!0\.[123]\b)\d{1,2}\.\d", p))

        def repl(m: re.Match) -> str:
            num = m.group(1)
            tgt = ref_map.get(num)
            if not tgt:
                return m.group(0)
            href = f"#{tgt}" if (print_mode or tgt == current) else f"{tgt}.html"
            return f'<a class="xref" href="{href}">§{num}</a>'

        out.append(_REF_RE.sub(repl, p))
    return "".join(out), skipped_sections


_SKIP_ASSET = re.compile(r"<(pre|a|style|script)\b|</(pre|a|style|script)>")


def linkify_assets(html: str) -> tuple[str, list[str]]:
    """assets/§N-体验实验/… 路径链接化（代码段内外都做；存在性校验，缺失不链并上报）。"""
    parts = re.split(r"(<[^>]+>)", html)
    out: list[str] = []
    skip = 0
    missing: list[str] = []

    def repl(text: str) -> str:
        def cb(m: re.Match) -> str:
            raw = m.group(0)
            path = raw[len("series/"):] if raw.startswith("series/") else raw
            rel = path[len("assets/"):]
            p = Path(rel)
            target = ASSETS / p
            is_file = target.is_file()
            is_dir = target.is_dir()
            dir_name = rel.split("/")[0]
            if is_dir and not is_file and len(p.parts) > 1:
                # 目录下追加了内容但不是文件（容错）
                is_dir = True
            if is_file:
                href = "assets/" + quote(str(p), safe="/")
                return f'<a class="asset" href="{href}">{raw}</a>'
            if is_dir and len(p.parts) == 1:
                href = "assets.html#" + quote("d-" + dir_name, safe="-")
                return f'<a class="asset" href="{href}">{raw}</a>'
            missing.append(path)
            return raw
        return _ASSET_RE.sub(cb, text)

    for p in parts:
        if p.startswith("<"):
            mo = _SKIP_ASSET.match(p)
            if mo:
                if p.startswith("</"):
                    skip = max(0, skip - 1)
                else:
                    skip += 1
            out.append(p)
            continue
        out.append(p if skip else repl(p))
    return "".join(out), missing


def embed_figures(html: str, slug: str) -> str:
    """把 <p>〔图 X：caption〕</p> 渲染为 <figure>（有图件时）。

    图件注册表：series/figures/manifest.json（generate_figures.py 产出，单一来源）。
    未出图的图注保持原样；覆盖率由 series_check.check_figures 门禁盯。
    """
    man_path = SERIES / "figures" / "manifest.json"
    if not man_path.exists():
        return html
    try:
        man = json.loads(man_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return html

    def repl(m: re.Match) -> str:
        fid = m.group(1).strip()
        cap = m.group(2).strip()
        ent = man.get(fid)
        if not ent:
            return m.group(0)
        f = ent["file"] if isinstance(ent, dict) else ent
        alt = H.escape(re.sub(r"<[^>]+>", "", cap))
        return (f'<figure class="book-fig" id="fig-{slug}-{fid}">'
                f'<img src="figures/{quote(f, safe="/")}" alt="{alt}" loading="lazy">'
                f'<figcaption>图 {fid}：{cap}</figcaption></figure>')

    return re.sub(r"<p>〔图\s*([0-9A-Za-z\-]+)\s*：(.*?)〕</p>", repl, html, flags=re.S)



def wrap_tables(html: str) -> str:
    """表格加容器：宽表（表头 ≥8 列，多为数值扫掠表）走自然宽＋横向滚动；普通表照旧 100%。"""
    def repl(m: re.Match) -> str:
        table = m.group(0)
        first_tr = re.search(r"<tr[^>]*>.*?</tr>", table, re.S)
        ncol = first_tr.group(0).count("<th") if first_tr else 0
        if ncol >= 8 and "<table" in table:
            table = table.replace("<table", '<table class="wide"', 1)
        return f'<div class="table-wrap" tabindex="0">{table}</div>'
    return re.sub(r"<table[^>]*>.*?</table>", repl, html, flags=re.S)

# ---------------------------------------------------------------- 页面装配层

def load_chapters() -> tuple[list[dict], list[dict]]:
    cfg = json.loads((PROFILES / "chapters.json").read_text(encoding="utf-8"))
    return cfg["chapters"], cfg["parts"]


def build_ref_map(chapters: list[dict]) -> dict[str, str]:
    m: dict[str, str] = {}
    for ch in chapters:
        lab = ch["label"]
        if lab.startswith("§"):
            m[lab[1:]] = ch["slug"]
        elif lab.startswith("T"):
            m[lab] = ch["slug"]
    return m


def short_title(t: str, n: int = 22) -> str:
    core = t.split("——")[0]
    core = re.sub(r"^(?:§[\d.]+|T\d|支线导言|支线附录)[:：]?\s*", "", core)
    return core if len(core) <= n else core[: n - 1] + "…"


def sidebar_html(chapters: list[dict], parts: list[dict], current: dict | None,
                 disp: dict | None = None, reasons: dict | None = None,
                 dim_sections: dict | None = None) -> str:
    disp = disp or {}
    reasons = reasons or {}
    dim_sections = dim_sections or {}
    by_part: dict[str, list[dict]] = {}
    for ch in chapters:
        by_part.setdefault(ch["part"], []).append(ch)
    out: list[str] = []
    for part in parts:
        items = by_part.get(part["id"], [])
        if not items:
            continue
        out.append(f'<div class="part">{H.escape(part["label"])}</div>')
        out.append("<ul>")
        for ch in items:
            cls = "ch"
            if current and ch["slug"] == current["slug"]:
                cls += " current"
            d = disp.get(ch["slug"])
            title = ""
            if d == "dim":
                cls += " dim"
                title = (reasons.get("branch_dim", "") if ch["part"] == "branch"
                         else reasons.get("default", ""))
            elif isinstance(d, dict):
                cls += " focus"
                title = "只读所列节"
            tattr = f' title="{H.escape(title, quote=True)}"' if title else ""
            badges = badge_html(ch.get("h1_markers", []))
            out.append(
                f'<li class="{cls}" data-slug="{ch["slug"]}"><a href="{ch["slug"]}.html"{tattr}>'
                f'{H.escape(short_title(ch["title"]))}{badges}</a>')
            if current and ch["slug"] == current["slug"] and ch.get("sections"):
                out.append('<ul class="sub">')
                for sec in ch["sections"]:
                    if sec["level"] != 2:
                        continue
                    scls = ' class="dim"' if sec["anchor"] in dim_sections else ""
                    out.append(
                        f'<li{scls}><a href="#{sec["anchor"]}">{H.escape(sec["text"])}</a></li>')
                out.append("</ul>")
            out.append("</li>")
        out.append("</ul>")
    return "\n".join(out)


def nav_prevnext(prev: dict | None, nxt: dict | None, special: str = "") -> str:
    left = (f'<a class="pv-prev" href="{prev["slug"]}.html">← {H.escape(prev["label"])} '
            f'{H.escape(short_title(prev["title"], 16))}</a>') if prev else "<span></span>"
    right = (f'<a class="pv-next" href="{nxt["slug"]}.html">{H.escape(nxt["label"])} '
             f'{H.escape(short_title(nxt["title"], 16))} →</a>') if nxt else "<span></span>"
    box = f'<nav class="prevnext">{left}{right}</nav>'
    if special:
        box = f'<div class="asset-card">{special}</div>\n' + box
    return box


def asset_dir_of(slug: str) -> str | None:
    if re.fullmatch(r"t[1-9]", slug):
        d = f"T{slug[1:]}-体验实验"
    elif re.fullmatch(r"ch\d{2}", slug):
        d = f"§{int(slug[2:])}-体验实验"
    else:
        return None
    return d if (ASSETS / d).is_dir() else None


def asset_card(slug: str) -> str:
    d = asset_dir_of(slug)
    if not d:
        return ""
    files = sorted(p.name for p in (ASSETS / d).iterdir() if p.is_file())
    names = "、".join(files[:8]) + ("…" if len(files) > 8 else "")
    href = "assets.html#" + quote("d-" + d, safe="-")
    return (f'<div class="asset-card"><b>本章资产：</b>{len(files)} 件（{H.escape(names)}）'
            f' <a href="{href}">全部 →</a></div>')


BRANCH_DOOR = (
    '<div class="asset-card"><b>支线入口：</b>想走生成方向的话，从这里进支线'
    '（<a href="intro.html">导言</a> → <a href="recipe.html">主线速览版配方</a> → T1–T4），'
    '否则 <a href="ch10.html">直接过 §10</a>。</div>'
)


def render_page(template: str, *, title: str, bodyclass: str, sidebar: str,
                content: str, footer: str, pathline: str = "", depth_label: str = "",
                site_data: str = "") -> str:
    return (template.replace("%%TITLE%%", H.escape(title))
                    .replace("%%BODYCLASS%%", bodyclass)
                    .replace("%%PATHLINE%%", pathline)
                    .replace("%%DEPTHLABEL%%", H.escape(depth_label))
                    .replace("%%SIDEBAR%%", sidebar)
                    .replace("%%CONTENT%%", content)
                    .replace("%%SITE_DATA%%", site_data)
                    .replace("%%FOOTER%%", footer))


# ---------------------------------------------------------------- 主流程

def hash8(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def _block_stats(raw: str) -> tuple[int, int]:
    """折叠块统计 →（总块数, ◇/◌ 块数；summary 含标记字形即计）。"""
    total = len(re.findall(r"<details>", raw))
    deep = 0
    for m in re.finditer(r"<summary>(.*?)</summary>", raw, re.S):
        if any(c in m.group(1) for c in "◇◌"):
            deep += 1
    return total, deep


def fmt_size(n: int) -> str:
    return f"{n / 1024:.0f} KB" if n >= 1024 else f"{n} B"


_ASSET_KINDS = ["笔记本", "脚本", "运行记录", "引用卡", "复算表", "讨论题面", "图", "数据", "资料", "文件"]


def asset_kind(name: str) -> str:
    """资产文件类型标签（索引页同类归组）。"""
    lower = name.lower()
    if name.endswith(".ipynb"):
        return "笔记本"
    if name.endswith(".py"):
        return "脚本"
    if name.startswith("run_log") or "运行记录" in name:
        return "运行记录"
    if "引用卡" in name:
        return "引用卡"
    if "复算表" in name:
        return "复算表"
    if "讨论" in name or "discussion" in lower:
        return "讨论题面"
    if name.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
        return "图"
    if name.endswith((".tsv", ".npy", ".csv", ".json")):
        return "数据"
    if name.endswith(".md"):
        return "资料"
    return "文件"


def _nat_key(s: str) -> str:
    """自然序：数字段零填充后按字符串比较（trace_batch4 < trace_batch16）。"""
    return re.sub(r"\d+", lambda m: m.group(0).rjust(12, "0"), s)


def asset_sort_key(p: Path):
    return (_ASSET_KINDS.index(asset_kind(p.name)), _nat_key(p.name))


def asset_li(d: str, sub: str | None, p: Path) -> str:
    rel = "/".join(quote(x, safe="") for x in ([d] + ([sub] if sub else []) + [p.name]))
    return (f'<li><span class="tag">{asset_kind(p.name)}</span>'
            f'<a href="assets/{rel}">{H.escape(p.name)}</a>'
            f' <span class="meta">（{fmt_size(p.stat().st_size)}）</span></li>')


def main() -> int:
    ap = argparse.ArgumentParser(description="series 阅读版 HTML 构建")
    ap.add_argument("--only", nargs="*", metavar="SLUG", help="只重建指定章页（调试）")
    ap.add_argument("--no-assets", action="store_true", help="跳过资产拷贝")
    args = ap.parse_args()

    chapters, parts = load_chapters()
    ref_map = build_ref_map(chapters)
    by_slug = {c["slug"]: c for c in chapters}
    main_flow = [c["slug"] for c in chapters if c["part"] != "branch"]
    branch_flow = [c["slug"] for c in chapters if c["part"] == "branch"]

    # 全量预扫（侧栏与导航需要全书信息）
    for ch in chapters:
        raw = (SERIES / ch["file"]).read_text(encoding="utf-8")
        ch["hash"] = hash8(raw)
        converted = ssc.convert_text(raw, ssc.new_stats())
        processed, info = scan_and_rewrite(norm_structure(converted), ch["slug"])
        ch["md"] = processed
        ch["title"] = info["h1"]
        ch["h1_markers"] = info["h1_markers"]
        ch["sections"] = info["sections"]
        ch["sec_mins"] = section_mins_map(processed, info["sections"])
        ch["stats"] = reading_stats(raw)
        ch["mins"] = reading_metrics(raw)[1]
        ch["blk"] = _block_stats(raw)

    if not all(c["title"] for c in chapters):
        raise RuntimeError("有章节未扫出标题：" + ", ".join(c["slug"] for c in chapters if not c["title"]))
    terms_all = terms_items(chapters)

    DIST.mkdir(exist_ok=True)
    # 全量构建清理旧的顶层生成页，防止删章/改名后残留（--only 不清理）。
    if not args.only:
        for p in DIST.glob("*.html"):
            p.unlink()
        (DIST / "anchors.json").unlink(missing_ok=True)
    (DIST / ".nojekyll").write_text("", encoding="utf-8")
    template = TEMPLATE.read_text(encoding="utf-8")

    # ---- 路线层：默认＝自由读（静态无降灰；JS 按所选路线运行时套用，routes.json 单一来源）
    routes_cfg = load_routes()
    default_route = None  # None＝自由读（裁决 Q1/Q5）
    views_by_route = {r["id"]: route_view(r, chapters) for r in routes_cfg["routes"]}
    free = free_view(chapters)
    default_dim_sections: dict = {}
    site_data_html = build_site_data(chapters, parts, routes_cfg, views_by_route)
    pathline = route_pathline(default_route)
    depth_label = "实践优先（折叠收起）"

    # ---- 导航映射
    def prevnext_of(slug: str) -> tuple[dict | None, dict | None, str]:
        special = ""
        if slug in main_flow:
            i = main_flow.index(slug)
            prev = by_slug[main_flow[i - 1]] if i > 0 else None
            nxt = by_slug[main_flow[i + 1]] if i + 1 < len(main_flow) else None
            if slug == "ch09":
                special = BRANCH_DOOR
            return prev, nxt, special
        i = branch_flow.index(slug)
        prev_slug = branch_flow[i - 1] if i > 0 else "ch09"
        nxt_slug = branch_flow[i + 1] if i + 1 < len(branch_flow) else "ch10"
        return by_slug[prev_slug], by_slug[nxt_slug], ""

    # ---- 渲染（pandoc）
    todo = [c for c in chapters if not args.only or c["slug"] in args.only]
    if args.only:
        unknown = [s for s in args.only if s not in by_slug]
        if unknown:
            print(f"未知 slug：{unknown}", file=sys.stderr)
            return 2

    anchors: dict[str, dict] = {}
    missing_assets: list[str] = []
    skipped_sec_refs = 0
    build_date = RELEASE.get("date") or datetime.date.today().isoformat()

    for ch in todo:
        slug = ch["slug"]
        html = pandoc_html(ch["md"], SERIES)
        html = prefix_cb(html, slug)
        # 资产链接化必须先于 §N 引用链接化：否则 assets/§N-… 路径里的 §N 先被拆链、
        # 资产正则失配（曾致 10 处笔记本链断裂，见 edit/学习路径审读.2026-10-14.md §3.5）。
        html, miss = linkify_assets(html)
        missing_assets.extend(miss)
        html, sk = linkify_refs(html, slug, ref_map, print_mode=False)
        skipped_sec_refs += sk
        html = embed_figures(html, slug)
        html = wrap_tables(html)
        html = wrap_sections(html)
        html = apply_section_dim(html, default_dim_sections)
        prev, nxt, special = prevnext_of(slug)
        footer = footer_html(build_date, f"本章源稿校验和 {ch['hash']}")
        h2s = [s for s in ch["sections"] if s["level"] == 2]
        review_anchor = h2s[-1]["anchor"] if h2s else ""
        review_label = "抽查部末十题" if slug in ("ch09", "ch14", "ch21") else "抽查本章三题"
        review_link = (f'<a class="review-link" id="reviewLink" href="#{review_anchor}" '
                       f'data-anchor="{review_anchor}">{review_label}</a>') if review_anchor else ""
        content = (f'<article class="chapter">\n'
                   f'<div class="route-banner" id="routeBanner" data-slug="{slug}" hidden></div>\n'
                   f'<div class="chapter-meta" id="chapterMeta" data-slug="{slug}">{ch["stats"]}</div>\n'
                   f'<div class="focus-row" id="focusRow" hidden><label><input type="checkbox" '
                   f'id="focusHide"> 隐藏非路线内容</label></div>\n'
                   f'{html}\n'
                   f'{migration_callout(ch)}\n'
                   f'{chapter_terms_block(slug, terms_all, chapters)}\n'
                   f'<div class="read-row"><button type="button" id="readToggle" '
                   f'data-slug="{slug}">标记已读</button>'
                   f'{review_link}'
                   f'<a class="route-next" id="routeNext" data-slug="{slug}" hidden></a></div>\n'
                   f'{nav_prevnext(prev, nxt, special)}\n{asset_card(slug)}\n</article>')
        sidebar = sidebar_html(chapters, parts, ch, free["disp"], {}, default_dim_sections)
        page = render_page(template, title=f"{ch['label']} {short_title(ch['title'], 30)} · AI 系列读物",
                           bodyclass="chapter-page", sidebar=sidebar, content=content, footer=footer,
                           pathline=pathline, depth_label=depth_label, site_data=site_data_html)
        (DIST / f"{slug}.html").write_text(page, encoding="utf-8", newline="\n")
        print(f"✓ {slug}.html ({len(page)//1024} KB)")

        for sec in ch["sections"]:
            anchors[sec["anchor"]] = {"ch": slug, "title": sec["text"], "level": sec["level"]}
        anchors[slug] = {"ch": slug, "title": ch["title"], "level": 1}

    if args.only:
        print(f"（--only 模式：未重建 print/index/assets/anchors；未链节引用 {skipped_sec_refs} 处）")
        return 0

    # ---- print.html（details 全开；§N 同页锚）
    print_frags: list[str] = []
    for ch in chapters:
        html = pandoc_html(ch["md"], SERIES)
        html = prefix_cb(html, ch["slug"])
        # 同章页：资产链接化先于 §N 引用链接化（次序说明见章页构建处注释）。
        html, miss = linkify_assets(html)
        missing_assets.extend(miss)
        html, sk = linkify_refs(html, ch["slug"], ref_map, print_mode=True)
        skipped_sec_refs += sk
        html = embed_figures(html, ch["slug"])
        html = wrap_tables(html)
        html = wrap_sections(html)
        html = html.replace("<details>", "<details open>")
        print_frags.append(f'<article class="chapter" id="p-{ch["slug"]}">\n{html}\n{asset_card(ch["slug"])}\n</article>')
    toc = "\n".join(
        f'<li><a href="#{c["slug"]}">{H.escape(c["label"])} {H.escape(short_title(c["title"], 30))}</a>'
        f'{badge_html(c["h1_markers"])}</li>' for c in chapters)
    print_content = (f'<div class="chapter-head"><h1>AI 系列读物 · 全文版</h1>'
                     f'<p class="doc-meta">本页为全书单页版：适合打印与全文检索（Ctrl+F）。'
                     f'分章阅读请回 <a href="index.html">目录</a>。</p></div>'
                     f'<ul>{toc}</ul><hr>\n' + "\n".join(print_frags))
    print_page = render_page(template, title="AI 系列读物 · 全文版", bodyclass="print-page",
                             sidebar="", content=print_content,
                             footer=footer_html(build_date, "源稿共 30 章"))
    (DIST / "print.html").write_text(print_page, encoding="utf-8", newline="\n")
    print(f"✓ print.html ({len(print_page)//1024} KB)")

    # ---- assets.html
    seen: set[str] = set()
    asset_sections: list[str] = []
    for ch in chapters:
        d = asset_dir_of(ch["slug"])
        if not d or d in seen:
            continue
        seen.add(d)
        top = [p for p in (ASSETS / d).iterdir() if p.is_file()]
        top.sort(key=asset_sort_key)
        rows = "\n".join(asset_li(d, None, p) for p in top)
        extra = ""
        for sub in sorted((p for p in (ASSETS / d).iterdir() if p.is_dir() and p.name != "__pycache__"),
                          key=lambda p: p.name):
            sub_files = [p for p in sub.iterdir() if p.is_file()]
            if not sub_files:
                continue
            sub_files.sort(key=asset_sort_key)
            sub_rows = "\n".join(asset_li(d, sub.name, p) for p in sub_files)
            extra += (f'<p class="meta">{H.escape(sub.name)}/（{len(sub_files)} 个文件）</p>\n'
                      f'<ul>{sub_rows}</ul>')
        asset_sections.append(
            f'<h2 id="{H.escape("d-" + d)}">{H.escape(d)}'
            f'<span class="mk" style="font-size:0.7em"> {ch["label"]} · {len(top)} 文件</span></h2>\n'
            f'<ul>{rows}</ul>' + (("\n" + extra) if extra else ""))
    assets_page = render_page(
        template, title="资产索引 · AI 系列读物", bodyclass="aux-page", sidebar="",
        content=(f'<div class="chapter-head"><h1>资产索引</h1>'
                 f'<p class="doc-meta">各章动手实验的脚本、笔记本与运行记录，同类归组：'
                 f'先看脚本与笔记本，再拿运行记录对账。共 {len(seen)} 个目录。'
                 f'回 <a href="index.html">目录</a>。</p></div>\n'
                 + "\n".join(asset_sections)),
        footer=footer_html(build_date))
    (DIST / "assets.html").write_text(assets_page, encoding="utf-8", newline="\n")
    print(f"✓ assets.html（{len(seen)} 个目录）")

    # ---- 供给页（批 4）：术语/环境/自测/路线
    (DIST / "terms.html").write_text(
        render_page(template, title="术语总表 · AI 系列读物", bodyclass="aux-page", sidebar="",
                    content=terms_content(chapters), footer=footer_html(build_date)),
        encoding="utf-8", newline="\n")
    print("✓ terms.html")
    (DIST / "env.html").write_text(
        render_page(template, title="环境指南 · AI 系列读物", bodyclass="aux-page", sidebar="",
                    content=env_content(chapters, ref_map),
                    footer=footer_html(build_date, f"环境指南最后验证：{ENV_VERIFIED}")),
        encoding="utf-8", newline="\n")
    print("✓ env.html")
    (DIST / "selftest.html").write_text(
        render_page(template, title="数学自修自测 · AI 系列读物", bodyclass="aux-page", sidebar="",
                    content=selftest_content(ref_map), footer=footer_html(build_date),
                    site_data=site_data_html),
        encoding="utf-8", newline="\n")
    print("✓ selftest.html")
    (DIST / "routes.html").write_text(
        render_page(template, title="路线与论文清单 · AI 系列读物", bodyclass="aux-page", sidebar="",
                    content=routes_content(routes_cfg, chapters), footer=footer_html(build_date),
                    site_data=site_data_html),
        encoding="utf-8", newline="\n")
    print("✓ routes.html")
    for r in routes_cfg["routes"]:
        (DIST / f'route-{r["id"]}.html').write_text(
            render_page(template, title=f'{r["title"]} · 打印版 · AI 系列读物',
                        bodyclass="aux-page", sidebar="",
                        content=route_print_content(r, chapters), footer=footer_html(build_date)),
            encoding="utf-8", newline="\n")
    print(f"✓ route-*.html ×{len(routes_cfg['routes'])}")

    # ---- index.html（B3：向导＋路线图＋课表＋进度环＋检索；数据块内嵌）
    index_content = hub_content(chapters, parts, routes_cfg, free)
    index_page = render_page(template, title="AI 系列读物 · 阅读版", bodyclass="hub-page",
                             sidebar="", content=index_content, footer=footer_html(build_date),
                             site_data=site_data_html)
    (DIST / "index.html").write_text(index_page, encoding="utf-8", newline="\n")
    print("✓ index.html")

    # ---- anchors.json（全量构建才刷新；漂移由 series_check 对 git 门禁）
    (DIST / "anchors.json").write_text(
        json.dumps({k: anchors[k] for k in sorted(anchors)}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    print(f"✓ anchors.json（{len(anchors)} 锚）")

    # ---- assets 拷贝
    if not args.no_assets:
        fdst = DIST / "figures"
        if (SERIES / "figures").is_dir():
            shutil.rmtree(fdst, ignore_errors=True)
            shutil.copytree(SERIES / "figures", fdst)
            nf = sum(1 for _ in fdst.rglob("*") if _.is_file())
            print(f"✓ figures/ 拷贝 {nf} 文件")
        dst = DIST / "assets"
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(ASSETS, dst)
        n = sum(1 for _ in dst.rglob("*") if _.is_file())
        print(f"✓ assets/ 拷贝 {n} 文件")

    if missing_assets:
        uniq = sorted(set(missing_assets))
        print(f"⚠ 资产路径缺失 {len(uniq)} 处（未链）：{uniq[:8]}")
    print(f"（§N.M 节级引用未链 {skipped_sec_refs} 处，按设计留素文）")

    # ---- B5 库存报告（◇/◌ 按折叠块计；只报告不裁决）
    print("── B5 库存（◇/◌）──")
    tot_blk = tot_bdeep = tot_sdeep = tot_sec = 0
    for ch in chapters:
        secs = [s for s in ch["sections"] if s["level"] == 2]
        sdeep = sum(1 for s in secs if set(s["markers"]) & set("◇◌"))
        b, bdeep = ch["blk"]
        tot_blk += b
        tot_bdeep += bdeep
        tot_sdeep += sdeep
        tot_sec += len(secs)
        pct = f"{bdeep / b:.0%}" if b else "—"
        print(f"  {ch['slug']:5} 节◇◌ {sdeep:>2}/{len(secs):<2} ｜ 块◇◌ {bdeep:>2}/{b:<2} ({pct})")
    print(f"  合计：块◇◌ {tot_bdeep}/{tot_blk} ｜ 节◇◌ {tot_sdeep}/{tot_sec}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
