#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""series 阅读版产物门禁（build_site 后运行）。

检查项（exit 1 = 有硬伤）：
1. chapters.json ↔ series 章文件双射（防新章忘登记/删章幽灵）
2. 每页：id 全站页内唯一；href="#…" 同页可达；href="X.html[#…]" 目标页与锚存在
   （含 assets.html 的 d-<dir> 锚）；资产链接落到 dist/assets 真实文件
3. 每页：details 配对；标题行（h1–h3）剥徽章后无裸标记字形；标题锚以章 slug 开头
4. print.html：30 章锚齐全；assets.html：series/assets 全目录在列
5. anchors.json 漂移门（对照 git HEAD 版本，--accept 刷新；缺 git/首版则跳过）

用法：
    python3 series/tools/series_check.py            # 全量检查
    python3 series/tools/series_check.py --accept   # 漂移复核通过后刷新快照
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
SERIES = HERE.parent
DIST = SERIES / "dist"
PROFILES = SERIES / "profiles"
ASSETS = SERIES / "assets"
MARK_CHARS = "▽○◌◇"

sys.path.insert(0, str(HERE))
import build_site as bs  # noqa: E402  （B3 真值表单一源）

FAILS: list[str] = []


def fail(msg: str) -> None:
    FAILS.append(msg)


def page_files() -> list[Path]:
    return sorted(p for p in DIST.glob("*.html"))


def check_bijection(chapters: list[dict]) -> None:
    declared = {c["file"] for c in chapters}
    on_disk = set()
    for pat in ("§*.md", "T*.md", "支线*.md"):
        on_disk.update(p.name for p in SERIES.glob(pat))
    if declared != on_disk:
        fail(f"章文件双射失败：登记未落盘 {sorted(declared - on_disk)}；"
             f"未登记 {sorted(on_disk - declared)}")


def check_source_terms() -> None:
    """正文禁内部工作词（2026-10-13 源书脱钩批）：读者面对改写的成品，
    「源书」（输入材料的内部称呼）不可解；出处一律一手来源或转引限定语。"""
    banned = ("源书",)
    for pat in ("§*.md", "T*.md", "支线*.md"):
        for p in sorted(SERIES.glob(pat)):
            txt = p.read_text(encoding="utf-8")
            for term in banned:
                if term in txt:
                    fail(f"{p.name}: 正文出现内部工作词「{term}」")


def collect_ids(html: str) -> set[str]:
    return set(re.findall(r'id="([^"]+)"', html))


AUX_SUPPLY = {"terms.html", "env.html", "selftest.html", "routes.html"}
NON_CHAPTER = {"index.html", "print.html", "assets.html"} | AUX_SUPPLY


def is_chapter_page(p: Path) -> bool:
    return p.name not in NON_CHAPTER and not p.name.startswith("route-")


def check_page(path: Path, chapters: list[dict], pages: set[str]) -> None:
    html = path.read_text(encoding="utf-8")
    name = path.name
    ids = re.findall(r'id="([^"]+)"', html)
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        fail(f"{name}: 重复 id {sorted(dup)[:5]}")
    id_set = set(ids)

    # href 可达性
    for m in re.finditer(r'href="([^"]+)"', html):
        href = m.group(1)
        if href.startswith(("#", "http://", "https://", "mailto:")):
            tgt = unquote(href[1:])
            if tgt and tgt not in id_set:
                fail(f"{name}: 同页锚不可达 #{tgt[:40]}")
            continue
        path_part, _, frag = href.partition("#")
        frag = unquote(frag)
        if path_part.startswith("assets/"):
            # 资产先行分支：raw/ 里可含 .html 存证文件，按资产解码校验，
            # 不做页面判定（2026-10-14 索引页 raw 列表引入后修正误报）。
            rel = unquote(path_part)
            if not (DIST / rel).exists():
                fail(f"{name}: 资产文件不存在 {rel}")
        elif path_part.endswith(".html"):
            if path_part not in pages:
                if not (DIST / path_part).exists():
                    fail(f"{name}: 目标页不存在 {path_part}")
            elif frag:
                tgt_html = (DIST / path_part).read_text(encoding="utf-8")
                if frag not in collect_ids(tgt_html):
                    fail(f"{name}: {path_part} 中锚不可达 #{frag[:40]}")

    # details 配对
    if html.count("<details") != html.count("</details>"):
        fail(f"{name}: details 未配对（{html.count('<details')}/{html.count('</details>')}）")

    # 裸标记残留（标题与 summary 内，刨掉徽章 span）；供给 aux 页不做徽章注入，豁免
    if name not in AUX_SUPPLY:
        for m in re.finditer(r"<(h[1-3]|summary)\b[^>]*>(.*?)</\1>", html, re.S):
            inner = re.sub(r'<span class="mk[^"]*"[^>]*>[^<]*</span>', "", m.group(2))
            raw = [c for c in inner if c in MARK_CHARS]
            if raw:
                fail(f"{name}: <{m.group(1)}> 残留裸标记 {raw}：{inner[:50]}")

    # $（系列数学体例＝Unicode/代码段；剥脚本/样式/代码块后正文不应出现美元数学）
    prose = re.sub(r"<script\b.*?</script>", "", html, flags=re.S)
    prose = re.sub(r"<style\b.*?</style>", "", prose, flags=re.S)
    prose = re.sub(r"<pre\b.*?</pre>", "", prose, flags=re.S)
    prose = re.sub(r"<code\b.*?</code>", "", prose, flags=re.S)
    n_dollar = prose.count("$")
    if n_dollar:
        fail(f"{name}: 代码块外出现 {n_dollar} 个 $（系列无 $ 数学体例）")


def check_anchors_prefix(chapters: list[dict]) -> None:
    for ch in chapters:
        p = DIST / f"{ch['slug']}.html"
        if not p.exists():
            fail(f"缺页：{ch['slug']}.html")
            continue
        html = p.read_text(encoding="utf-8")
        for m in re.finditer(r'<(h[1-3])\b[^>]*id="([^"]*)"', html):
            if not m.group(2).startswith(ch["slug"]):
                fail(f"{ch['slug']}.html: 标题 id 异常 {m.group(2)}")


def check_print(chapters: list[dict]) -> None:
    p = DIST / "print.html"
    if not p.exists():
        fail("缺 print.html")
        return
    html = p.read_text(encoding="utf-8")
    ids = collect_ids(html)
    for ch in chapters:
        if ch["slug"] not in ids:
            fail(f"print.html 缺章锚 #{ch['slug']}")


def check_assets_page() -> None:
    p = DIST / "assets.html"
    if not p.exists():
        fail("缺 assets.html")
        return
    html = p.read_text(encoding="utf-8")
    dirs = sorted(d.name for d in ASSETS.iterdir() if d.is_dir())
    for d in dirs:
        if f'id="d-{d}"' not in html:
            fail(f"assets.html 缺目录 {d}")


def check_figures(chapters: list[dict]) -> None:
    """配图门禁：图注 ↔ 图件对账（覆盖率报告；孤儿/坏文件红）。

    - 已出图数 / 未出图列表：P0–P1 期间只报告，不判红（P1 收口后转硬门禁另行裁决）
    - manifest 有而正文无图注（孤儿）、或注册文件缺失/近空：一律红。
    """
    man_path = SERIES / "figures" / "manifest.json"
    man: dict = {}
    if man_path.exists():
        try:
            man = json.loads(man_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            fail(f"配图 manifest.json 损坏：{exc}")
            return
    declared: dict[str, int] = {}
    for ch in chapters:
        md = (SERIES / ch["file"]).read_text(encoding="utf-8")
        for m in re.finditer(r"〔图\s*([0-9A-Za-z\-]+)\s*：", md):
            declared[m.group(1)] = declared.get(m.group(1), 0) + 1
    dset, drawn = set(declared), set(man)
    missing = sorted(dset - drawn, key=lambda x: (x[0].isdigit() is False, x))
    orphan = sorted(drawn - dset)
    bad = []
    for fid, ent in man.items():
        f = ent["file"] if isinstance(ent, dict) else ent
        path = SERIES / "figures" / f
        if (not path.exists()) or path.stat().st_size < 5000:
            bad.append(f"{fid}→{f}")
    done = len(dset & drawn)
    detail = "（全部完成）" if not missing else "（未出：%s）" % "、".join(missing)
    print(f"· 配图：图注 {len(dset)}｜已出图 {done}｜未出图 {len(missing)}{detail}")
    if missing:
        fail(f"配图未出（P1 收口后为硬门禁）：{missing}")
    if orphan:
        fail(f"配图孤儿：manifest 有而正文无图注 {orphan}")
    if bad:
        fail(f"配图坏文件（缺失或过小）：{bad}")


def check_routes(chapters: list[dict]) -> None:
    """路线库校验（fail-closed，2026-10-14 批 2）：schema、章/锚可达、出口/自证/时数、命名合规。"""
    rp = PROFILES / "routes.json"
    if not rp.exists():
        fail("缺 profiles/routes.json（路线库）")
        return
    try:
        cfg = json.loads(rp.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"routes.json 解析失败：{e}")
        return
    if cfg.get("schema") != "series-routes/v1":
        fail(f"routes.json schema 非 series-routes/v1：{cfg.get('schema')!r}")
        return
    slugs = {c["slug"] for c in chapters}
    if cfg.get("default_route", "free") != "free":
        fail("default_route 应为 free（自由读为默认态，裁决 Q5）")
    ap = DIST / "anchors.json"
    if not ap.exists():
        fail("缺 anchors.json：无法校验路线选择器")
        return
    anchors = json.loads(ap.read_text(encoding="utf-8"))
    routes = cfg.get("routes", [])
    if len(routes) < 5:
        fail(f"路线库少于 5 条：{len(routes)}（批 0 定稿 9 条）")
    ids = [r.get("id") for r in routes]
    if len(ids) != len(set(ids)) or any(not i for i in ids):
        fail("路线 id 缺失或重复")
    for r in routes:
        if "标准" in (r.get("title") or ""):
            fail(f"路线 {r.get('id')} 标题含旧档位词「标准」（命名纪律）")
    for r in routes:
        rid = r.get("id", "?")
        if not r.get("exit"):
            fail(f"路线 {rid} 缺出口清单（G1）")
        if len(r.get("selfcheck", [])) < 2:
            fail(f"路线 {rid} 自证题 <2（G1）")
        if not (r.get("hours") or {}).get("read"):
            fail(f"路线 {rid} 缺时数（G3）")
        if not r.get("note"):
            fail(f"路线 {rid} 缺 note（两问路由推荐短语，模板不再硬编码）")
        for e in r.get("sequence", []):
            if e.get("ch") not in slugs:
                fail(f"路线 {rid} 引用未登记章 {e.get('ch')}")
            if e.get("mode") == "focus":
                secs = e.get("sections") or []
                if not secs:
                    fail(f"路线 {rid}·{e.get('ch')} focus 清单为空")
                for a in secs:
                    if a not in anchors:
                        fail(f"路线 {rid}·{e.get('ch')} 结论节锚不存在 {a}")
            elif e.get("mode") != "read":
                fail(f"路线 {rid}·{e.get('ch')} mode 非法 {e.get('mode')!r}")
        for card in r.get("cards", []):
            if card.get("anchor") not in anchors:
                fail(f"路线 {rid} 补课卡锚不存在 {card.get('anchor')}")
    print(f"· 路线库：{len(routes)} 条（{'、'.join(ids)}）——章/锚可达，出口/自证/时数齐备，命名合规")


def check_b3(chapters: list[dict]) -> None:
    """路线层视图校验（2026-10-14 批 2 起）：默认＝自由读、Hub 组件、路线卡、
    内嵌数据对等、节包裹/details 配对、迁移提醒、锚漂移门配套。"""
    cfg = json.loads((PROFILES / "routes.json").read_text(encoding="utf-8"))
    routes = cfg["routes"]
    idx = (DIST / "index.html").read_text(encoding="utf-8")

    def load_data(h: str):
        m = re.search(r'<script type="application/json" id="series-data">(.*?)</script>', h, re.S)
        if not m:
            return None
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            return None

    ref = load_data(idx)
    if ref is None:
        fail("Hub 缺内嵌 series-data（或 JSON 非法）")
        return
    if ref.get("schema") != "series-site-data/v2":
        fail(f"内嵌数据 schema 异常：{ref.get('schema')!r}")
    if ref.get("default_route") != "free":
        fail("内嵌 default_route ≠ free（默认应为自由读）")

    cards = re.findall(r'class="route-card" data-route="([^"]+)"', idx)
    if cards != ["free"] + [r["id"] for r in routes]:
        fail(f"Hub 路线卡序列异常：{cards}")
    emb = {r["id"] for r in ref.get("routes", [])}
    if emb != {r["id"] for r in routes}:
        fail("内嵌 routes 与 routes.json 的 id 集合不一致")
    for r in ref.get("routes", []):
        if not r.get("view", {}).get("disp"):
            fail(f"内嵌路线 {r['id']} 缺 view（构建期未算）")
    for eid, n in (("routerGoal", 5), ("routerTime", 4)):
        sel = re.search(rf'<select id="{eid}"[^>]*>(.*?)</select>', idx, re.S)
        if not sel:
            fail(f"Hub 缺路由选择器 #{eid}")
        elif len(re.findall(r"<option ", sel.group(1))) != n:
            fail(f"路由 {eid} 选项数 ≠ {n}")
    if 'id="routerResult"' not in idx:
        fail("Hub 缺路由结果位")
    if idx.count("rc-plan") < len(routes) + 1:
        fail("Hub 路线卡缺读法明细（rc-plan）")
    if 'id="exitLine"' not in idx:
        fail("Hub 缺自证行 #exitLine")
    for eid in ("resumeBlock", "resumeLink", "recentList"):
        if f'id="{eid}"' not in idx:
            fail(f"Hub 缺继续阅读元素 #{eid}")
    if "terms.html?q=" not in idx:
        fail("Hub 搜索缺术语兜底链（terms.html?q=）")
    if "copy-btn" not in idx or "fig-dialog" not in idx:
        fail("模板缺代码复制/图放大脚本（copy-btn/fig-dialog）")
    for eid in ("selftestNote", "projLine", "progressIO", "progText", "progExport", "progImport"):
        if f'id="{eid}"' not in idx:
            fail(f"Hub 缺 H2 元素 #{eid}")
    if len(re.findall(r'data-pid="', idx)) != 4:
        fail("Hub 结业项目勾选数 ≠ 4")
    for sid in ("hub-start", "hub-map", "hub-mine", "hub-ref"):
        if f'id="{sid}"' not in idx:
            fail(f"Hub 缺分区 #{sid}")
    if 'class="hub-nav"' not in idx:
        fail("Hub 缺分区导航 hub-nav")
    if idx.count('href="routes.html#route-') < len(routes) + 1:
        fail("Hub 路线卡缺 routes 兜底 href（修饰键/无 JS 用）")
    for eid in ("focusHideHub", "routerStart", "offrouteNote"):
        if f'id="{eid}"' not in idx:
            fail(f"Hub 缺聚焦元素 #{eid}")
    for eid in ("reviewBlock", "reviewList", "reviewRefresh", "readProgress"):
        if f'id="{eid}"' not in idx:
            fail(f"Hub 缺复习/进度元素 #{eid}")
    if "focus-hide" not in idx:
        fail("模板缺 focus-hide 规则（隐藏非路线内容）")
    if idx.count('aria-live') < 3:
        fail("Hub aria-live 不足（<3）")

    nodes = re.findall(r'data-slug="([^"]+)"', idx)
    if len(nodes) != 30:
        fail(f"Hub 路线图节点 {len(nodes)} ≠ 30")
    if 'class="node dim"' in idx:
        fail("默认自由读视图 Hub 不应有 dim 节点")
    for eid in ("ringMainFg", "ringBranchFg", "hubSearch", "searchResults"):
        if f'id="{eid}"' not in idx:
            fail(f"Hub 缺元素 #{eid}")
    for needle in ("节奏示例", "巩固半周", "梯度检查", "六站拆批", "MiniMind-V", "MiniMind-O"):
        if needle not in idx:
            fail(f"Hub 节奏块缺：{needle}")

    mig_pages = [p for p in page_files() if 'class="migration"' in p.read_text(encoding="utf-8")]
    if {p.name for p in mig_pages} != {"ch09.html", "ch14.html", "ch21.html"}:
        fail(f"迁移提醒页异常：{sorted(p.name for p in mig_pages)}")
    for slug in ("ch09", "ch14", "ch21"):
        h = (DIST / f"{slug}.html").read_text(encoding="utf-8")
        m = re.search(r'class="migration".*?href="#([^"]+)"', h, re.S)
        if not m or f'id="{m.group(1)}"' not in h:
            fail(f"{slug} 迁移提醒锚不可达")

    chapter_pages = [p for p in page_files() if is_chapter_page(p)]
    dim_anchors: set[str] = set()
    for p in chapter_pages:
        h = p.read_text(encoding="utf-8")
        n_h2 = len(re.findall(r'<h2 id="', h))
        secs = re.findall(r'<section class="sec( dim)?" data-anchor="([^"]+)"[^>]*>\s*<h2 id="([^"]+)"', h)
        if len(secs) != n_h2:
            fail(f"{p.name}: 包裹节 {len(secs)} ≠ h2 {n_h2}")
        bad = [a for _, a, hid in secs if a != hid]
        if bad:
            fail(f"{p.name}: data-anchor 与 h2 id 不一致 {bad[:3]}")
        for m2 in re.finditer(r'<section class="sec( dim)?" data-anchor="([^"]+)"[^>]*>(.*?)</section>', h, re.S):
            if m2.group(1):
                dim_anchors.add(m2.group(2))
            body = m2.group(3)
            if body.count("<details") != body.count("</details>"):
                fail(f"{p.name}: 节内 details 不配对")
        if "<details open>" in h:
            fail(f"{p.name}: 默认实践档不应有 open 的折叠块")
        if f'id="routeBanner"' not in h:
            fail(f"{p.name}: 缺 routeBanner 位")
        if f'id="routeNext"' not in h:
            fail(f"{p.name}: 缺 routeNext 位")
        if f'id="chapterMeta"' not in h:
            fail(f"{p.name}: 缺 chapterMeta 信息条")
        if 'pv-next' not in h and 'pv-prev' not in h:
            fail(f"{p.name}: 缺翻章类 pv-next/pv-prev")
        if f'id="focusHide"' not in h:
            fail(f"{p.name}: 缺聚焦开关 #focusHide")
        # 支线导言没有章末自查，不挂抽查链接；其余有 H2 的页都要有。
        if f'id="reviewLink"' not in h and '<h2 id="' in h and p.name != "intro.html":
            fail(f"{p.name}: 缺抽查链接 #reviewLink")
    if dim_anchors:
        fail(f"默认自由读视图不应有节级降灰：{sorted(dim_anchors)[:5]}")

    # 内嵌数据：章页与 Hub 对等、节数与 anchors 对账
    anchors = json.loads((DIST / "anchors.json").read_text(encoding="utf-8"))
    n_sec = sum(len(c.get("sections", [])) for c in ref["chapters"])
    if n_sec != len(anchors) - len(chapters):
        fail(f"内嵌节索引 {n_sec} ≠ anchors 节数 {len(anchors) - len(chapters)}")
    for ch in chapters:
        if load_data((DIST / f"{ch['slug']}.html").read_text(encoding="utf-8")) != ref:
            fail(f"{ch['slug']}.html 内嵌数据与 Hub 不一致")
            break
    print("· 路线层视图：默认自由读/路线卡/两问路由/环/检索/迁移/内嵌数据——逐项校验")


def chapters_cfg() -> list[dict]:
    return json.loads((PROFILES / "chapters.json").read_text(encoding="utf-8"))["chapters"]


def check_supply_pages() -> None:
    """批 4 供给页：术语/环境/自测/路线的存在性与最低内容量（fail-closed）。"""
    tp = DIST / "terms.html"
    if not tp.exists():
        fail("缺 terms.html（术语总表）")
    else:
        h = tp.read_text(encoding="utf-8")
        n = len(re.findall(r"<tr[\s>]", h))
        if n < 600:
            fail(f"terms.html 词条行 {n} < 600")
        if h.count('id="term-') < 600:
            fail(f"terms.html 行锚 < 600：{h.count('id="term-')}")
        if 'id="termFilter"' not in h:
            fail("terms.html 缺筛词框")
        if "location.search" not in h:
            fail("terms.html 缺 ?q= 预填支持")
    stp = DIST / "selftest.html"
    if stp.exists():
        h = stp.read_text(encoding="utf-8")
        for eid in ("stScore", "stSave", "stSaved"):
            if f'id="{eid}"' not in h:
                fail(f"selftest.html 缺评分控件 #{eid}")
    rp2 = (DIST / "routes.html").read_text(encoding="utf-8")
    routes_cfg2 = json.loads((PROFILES / "routes.json").read_text(encoding="utf-8"))
    n_r = len(routes_cfg2["routes"])
    if rp2.count("每周 5h≈") != n_r:
        fail(f"routes.html 节奏三档行 {rp2.count('每周 5h≈')} ≠ {n_r}")
    if rp2.count("打印本路线") != n_r:
        fail(f"routes.html 打印链 {rp2.count('打印本路线')} ≠ {n_r}")
    for r in routes_cfg2["routes"]:
        pp = DIST / f'route-{r["id"]}.html'
        if not pp.exists():
            fail(f"缺打印页 route-{r['id']}.html")
        else:
            hh = pp.read_text(encoding="utf-8")
            if "自证题" not in hh or r["title"] not in hh:
                fail(f"route-{r['id']}.html 内容不齐")
    ep = DIST / "env.html"
    if not ep.exists():
        fail("缺 env.html（环境指南）")
    else:
        h = ep.read_text(encoding="utf-8")
        if "最后验证" not in h or "2026-" not in h:
            fail("env.html 缺最后验证日期")
        if h.count('class="asset" href="assets/') < 6:
            fail("env.html 笔记本链接 < 6")
    sp = DIST / "selftest.html"
    if not sp.exists():
        fail("缺 selftest.html（数学自修自测）")
    else:
        h = sp.read_text(encoding="utf-8")
        if h.count("<details>") < 8:
            fail(f"selftest.html 答案折叠 < 8：{h.count('<details>')}")
        if "结果映射" not in h:
            fail("selftest.html 缺结果映射")
    rp = DIST / "routes.html"
    if not rp.exists():
        fail("缺 routes.html（路线与论文清单）")
    else:
        h = rp.read_text(encoding="utf-8")
        for needle in ("尝鲜速览", "应用与 Agent", "训练与调参", "生成方向",
                       "研究与理论", "深究线", "论文清单", "自证题"):
            if needle not in h:
                fail(f"routes.html 缺：{needle}")
    # 章页「本章新词」：与台账首现章对账（有词的章必须有块）
    items = bs.terms_items(chapters_cfg())
    per = {}
    for name, first, note in items:
        slug = bs._slug_of_label(first, chapters_cfg())
        if slug:
            per[slug] = per.get(slug, 0) + 1
    for slug, n in per.items():
        page = DIST / f"{slug}.html"
        if not page.exists():
            continue
        h = page.read_text(encoding="utf-8")
        if 'class="chapter-terms"' not in h:
            fail(f"{slug}.html 缺「本章新词」块（台账 {n} 条）")
    # 自证勾选数 = 各路线 selfcheck 总数
    routes_cfg = json.loads((PROFILES / "routes.json").read_text(encoding="utf-8"))
    want = sum(len(r.get("selfcheck", [])) for r in routes_cfg["routes"])
    got = rp.read_text(encoding="utf-8").count('class="exit-check"')
    if got != want:
        fail(f"routes.html 自证勾选 {got} ≠ {want}")
    print("· 供给页：术语/环境/自测/路线——存在性、新词块对账、自证勾选数校验")


def check_part_answers(chapters: list[dict]) -> None:
    """部末答案完整性：源答案块计数 = 部末折叠数；章页不再留内联答案。"""
    summary_re = re.compile(
        r'<details>\s*<summary>\s*先写，再看：答案与去处\s*</summary>', re.S)
    expected: dict[str, list[tuple[dict, int]]] = {}
    for ch in chapters:
        src = (SERIES / ch["file"]).read_text(encoding="utf-8")
        n = len(summary_re.findall(src))
        if n:
            expected.setdefault(ch["part"], []).append((ch, n))

    for part, entries in expected.items():
        end = bs.PART_END.get(part)
        if not end:
            fail(f"有答案的部没有 PART_END：{part}")
            continue
        page = DIST / f"{end}.html"
        if not page.exists():
            fail(f"缺部末页：{page.name}（{part}）")
            continue
        html = page.read_text(encoding="utf-8")
        want = sum(n for _, n in entries)
        got = html.count('class="selfcheck-answer part-answer"')
        if got != want:
            fail(f"{page.name}: 部末答案 {got} ≠ 源答案 {want}（{part}）")
        if f'id="answers-{part}"' not in html:
            fail(f"{page.name}: 缺部末答案锚 #answers-{part}")
        for ch, _ in entries:
            if ch["slug"] == end:
                continue
            chapter_page = DIST / f"{ch['slug']}.html"
            if not chapter_page.exists():
                continue
            chapter_html = chapter_page.read_text(encoding="utf-8")
            if f'{end}.html#answers-{part}' not in chapter_html:
                fail(f"{ch['slug']}.html: 缺部末答案链接 {end}.html#answers-{part}")
            if '<details class="selfcheck-answer">' in chapter_html:
                fail(f"{ch['slug']}.html: 答案仍在章内，未搬到部末")

    print_page = DIST / "print.html"
    if print_page.exists():
        total = sum(n for entries in expected.values() for _, n in entries)
        got = print_page.read_text(encoding="utf-8").count('class="selfcheck-answer part-answer"')
        if got != total:
            fail(f"print.html: 部末答案 {got} ≠ 源答案 {total}")
    print("· 部末答案：源块计数、部末折叠、章页指路、print 收口——逐项校验")


def check_route_lint() -> None:
    """路线断链审计（tools/route_lint.py --check）：后向候选/供给/G1G3 未过即拦。"""
    tool = HERE / "route_lint.py"
    r = subprocess.run([sys.executable, str(tool), "--check"],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        tail = "；".join(((r.stdout or "") + "\n" + (r.stderr or "")).strip().splitlines()[-3:])
        fail(f"route_lint 未过：{tail[:300]}")
    else:
        first = ((r.stdout or "").strip().splitlines() or [""])[0]
        print(f"· 路线断链审计：{first}")


def check_route_js() -> None:
    """路线层 JS 对拍（tools/route_js_check.py）：viewOf≡内嵌视图、路由映射、焦点分钟。"""
    tool = HERE / "route_js_check.py"
    r = subprocess.run([sys.executable, str(tool)], capture_output=True, text=True, timeout=240)
    if r.returncode != 0:
        tail = "；".join(((r.stdout or "") + "\n" + (r.stderr or "")).strip().splitlines()[-3:])
        fail(f"route_js_check 未过：{tail[:300]}")
    else:
        print("· 路线层 JS 对拍：PASS（viewOf 9/9、路由 20/20、free 全亮）")


def _tracked_tools() -> list[Path]:
    """仓内 tracked 的 tools/*.py；忽略本地私有脚本（.gitignore 里的仪器）。"""
    r = subprocess.run(["git", "ls-files", "*.py"], cwd=HERE,
                       capture_output=True, text=True)
    if r.returncode == 0:
        names = sorted({Path(x).name for x in r.stdout.splitlines() if x.strip()})
        return [HERE / n for n in names if (HERE / n).is_file()]
    return sorted(HERE.glob("*.py"))


def check_tools_index() -> None:
    """tools/README.md 必须收录每个 tracked tools/*.py，防索引随新增工具腐烂。"""
    idx = HERE / "README.md"
    if not idx.exists():
        fail("tools/README.md 缺失")
        return
    text = idx.read_text(encoding="utf-8")
    tools = _tracked_tools()
    tracked = {p.name for p in tools}
    missing = sorted(n for n in tracked if n not in text)
    if missing:
        fail(f"tools/README.md 未收录：{', '.join(missing)}")
    stale = sorted(n for n in set(re.findall(r"`([A-Za-z0-9_]+\.py)`", text))
                   if n not in tracked)
    if stale:
        fail(f"tools/README.md 提到不存在的脚本：{', '.join(stale)}")


def anchors_drift(accept: bool) -> None:
    p = DIST / "anchors.json"
    if not p.exists():
        fail("缺 anchors.json")
        return
    cur = json.loads(p.read_text(encoding="utf-8"))
    # 根仓内的 series/ 子目录：git 路径需带 prefix（独立 series 仓时 prefix 为空）。
    prefix = subprocess.run(["git", "rev-parse", "--show-prefix"],
                            cwd=SERIES, capture_output=True, text=True).stdout.strip()
    r = subprocess.run(["git", "show", f"HEAD:{prefix}dist/anchors.json"],
                       cwd=SERIES, capture_output=True, text=True)
    if r.returncode != 0:
        print("· anchors 漂移门：HEAD 无旧快照（首版或未提交），跳过")
        return
    old = json.loads(r.stdout)
    gone = sorted(set(old) - set(cur))
    added = sorted(set(cur) - set(old))
    changed = sorted(k for k in set(old) & set(cur)
                     if old[k].get("title") != cur[k].get("title")
                     or old[k].get("ch") != cur[k].get("ch"))
    if not (gone or changed):
        print(f"· anchors 漂移门：通过（新增 {len(added)}）")
        return
    print(f"· anchors 漂移：消失 {len(gone)}｜换主/换题 {len(changed)}｜新增 {len(added)}")
    for k in (gone + changed)[:12]:
        print(f"    {k}: {old.get(k, {}).get('title', '')[:30]} → {cur.get(k, {}).get('title', '（消失）')[:30]}")
    if accept:
        print("· --accept：已以当前产物为准（快照即 dist/anchors.json，无需额外动作）")
    else:
        fail(f"anchors 漂移 {len(gone) + len(changed)} 处（复核后重跑 --accept 不消除本报告，仅供台账）")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--accept", action="store_true", help="确认漂移（留档用，不自动改文件）")
    args = ap.parse_args()

    cfg = json.loads((PROFILES / "chapters.json").read_text(encoding="utf-8"))
    chapters = cfg["chapters"]
    check_bijection(chapters)
    check_source_terms()
    check_tools_index()

    pages = {p.name for p in page_files()}
    for p in page_files():
        check_page(p, chapters, pages)
    check_anchors_prefix(chapters)
    check_print(chapters)
    check_assets_page()
    check_supply_pages()
    check_part_answers(chapters)
    check_routes(chapters)
    check_route_lint()
    check_route_js()
    check_figures(chapters)
    check_b3(chapters)

    prh = re.sub(r"<script\b.*?</script>", "", (DIST / "print.html").read_text(encoding="utf-8"), flags=re.S)
    for leak in ('id="routeNext"', 'id="chapterMeta"', 'class="catchup-card"',
                 'class="exit-check"', 'id="progressIO"', 'id="resumeBlock"'):
        if leak in prh:
            fail(f"print.html 泄漏运行时块：{leak}")

    if not args.accept:
        anchors_drift(accept=False)
    else:
        anchors_drift(accept=True)

    if FAILS:
        print(f"\nseries_check: {len(FAILS)} 项未过")
        for f in FAILS[:25]:
            print(" ✗", f)
        return 1
    print("series_check: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
