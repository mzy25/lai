#!/usr/bin/env python3
"""路线层 JS 运行时对拍（批 5 立，H1-7 扩面）：
从 site_template.html 抽真实路线层脚本，在 node + 最小 DOM stub 里逐路线执行 applyRoute，
断言页面效果与构建期视图一致：
- viewOf ≡ 内嵌 view（disp/dimSec/counts/open/cards/next）；
- banner 态（dim/focus/read）；节级降灰集合；补课卡出现与文案；
- 路线下一站（href/文案/隐藏）；双环分母；自证行；
- 自由读复原；自证勾选写入后 exitLine 更新。
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERIES = HERE.parent
DIST = SERIES / "dist"

# 测试用章节（含补课卡与下一站覆盖）
STUB_CH = ["ch14", "ch17", "ch21"]


def build_expectations(sd: dict) -> dict:
    exp = {"routes": {}, "free": {}, "exitN": {}}
    chapters = {c["slug"]: c for c in sd["chapters"]}
    stub_anchors = {slug: [s["anchor"] for s in chapters[slug]["sections"]] for slug in STUB_CH}
    all_anchors = set(sum(stub_anchors.values(), []))
    for r in sd["routes"]:
        v = r["view"]
        dims = sorted(set(v["dim_sections"].keys()) & all_anchors)
        cards = {a: t for a, t in (v.get("cards") or {}).items() if a in all_anchors}
        banner = v["disp"]["ch17"]
        exp["routes"][r["id"]] = {
            "banner": ("dim" if banner == "dim" else "focus" if isinstance(banner, dict) else "read"),
            "dims": dims,
            "cards": cards,
            "next": v.get("next", {}).get("ch17"),
            "ring": "0/" + str(v["counts"]["main"]),
            "exitN": len(r["selfcheck"]),
            "meta": ([v["pos"]["ch17"], v["total"]] if "ch17" in (v.get("pos") or {}) else None),
        }
    exp["free"] = {"dims": [], "cards": {}}
    return exp


NODE_TEST = r"""
const fs = require('fs');
const SD = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const EXP = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const STUB_CH = JSON.parse(fs.readFileSync(process.argv[4], 'utf8'));

let bad = 0;
function fail(msg) { bad++; console.log('FAIL ' + msg); }

function mkEl(tag, attrs) {
  const el = {
    tag: tag, attrs: Object.assign({}, attrs || {}), children: [], textContent: '', hidden: false,
    open: false, style: {}, _cls: new Set(), _listeners: {},
    get className() { return Array.from(this._cls).join(' '); },
    set className(v) { this._cls = new Set(String(v).split(/\s+/).filter(Boolean)); },
    get href() { return this.attrs.href || ''; },
    set href(v) { this.attrs.href = String(v); },
    _parent: null,
    classList: {
      add(c) { el._cls.add(c); }, remove(c) { el._cls.delete(c); },
      contains(c) { return el._cls.has(c); }, toggle(c, f) { if (f === undefined ? !el._cls.has(c) : f) el._cls.add(c); else el._cls.delete(c); },
    },
    closest(sel) {
      let n = el;
      while (n) {
        if (sel === 'section.sec' && n.tag === 'section' && n._cls.has('sec')) return n;
        n = n._parent;
      }
      return null;
    },
    scrollIntoView() { el._scrolled = true; },
    setAttribute(k, v) { el.attrs[k] = String(v); },
    getAttribute(k) { return Object.prototype.hasOwnProperty.call(el.attrs, k) ? el.attrs[k] : null; },
    removeAttribute(k) { delete el.attrs[k]; },
    addEventListener(t, fn) { (el._listeners[t] = el._listeners[t] || []).push(fn); },
    dispatch(t) {
      (el._listeners[t] || []).forEach(fn => fn.call(el,
        { ctrlKey: false, metaKey: false, shiftKey: false, altKey: false, button: 0,
          preventDefault() {} }));
    },
    appendChild(c) { c._parent = el; el.children.push(c); return c; },
    insertBefore(c, ref) { c._parent = el; const i = ref ? el.children.indexOf(ref) : -1; if (i >= 0) el.children.splice(i, 0, c); else el.children.unshift(c); return c; },
    removeChild(c) { const i = el.children.indexOf(c); if (i >= 0) el.children.splice(i, 1); },
    remove() { if (el._parent) el._parent.removeChild(el); },
    querySelector(sel) {
      const cls = sel.replace('.', '');
      for (const c of el.children) if (c._cls && c._cls.has(cls)) return c;
      return null;
    },
    querySelectorAll() { return []; },
    get firstChild() { return el.children[0] || null; },
  };
  return el;
}

const byId = {};
function register(id, el) { if (!el) return el; el.attrs = el.attrs || {}; el.attrs.id = id; byId[id] = el; return el; }

// 元素注册
const sdEl = { textContent: JSON.stringify(SD) };
register('series-data', sdEl);
const banner = register('routeBanner', mkEl('div', { 'data-slug': 'ch17' }));
const routeNext = register('routeNext', mkEl('a', { 'data-slug': 'ch17' }));
const pathLine = register('pathLine', mkEl('div'));
const chapterMeta = register('chapterMeta', mkEl('div', { 'data-slug': 'ch17' }));
chapterMeta.textContent = '测试统计文本';
const resumeBlock = register('resumeBlock', mkEl('div'));
const resumeLink = register('resumeLink', mkEl('a'));
const recentList = register('recentList', mkEl('ul'));
register('stScore', mkEl('select'));
register('stSave', mkEl('button'));
register('stSaved', mkEl('span'));
const selftestNote = register('selftestNote', mkEl('div'));
const focusHide = register('focusHide', mkEl('input'));
const focusHideHub = register('focusHideHub', mkEl('input'));
register('focusRow', mkEl('div'));
const offrouteNote = register('offrouteNote', mkEl('div'));
const routerStart = register('routerStart', mkEl('a'));
const reviewBlock = register('reviewBlock', mkEl('div'));
const reviewList = register('reviewList', mkEl('ul'));
register('reviewRefresh', mkEl('button'));
const reviewLink = register('reviewLink', mkEl('a', { 'data-anchor': 'ch17-s01' }));
const selfcheckJump = mkEl('a', { href: '#selfcheck', class: 'selfcheck-jump' });
const pvNext = mkEl('a', { href: 'orig-next.html' });
pvNext.textContent = 'orig-next 文案 →';
const pvPrev = mkEl('a', { href: 'orig-prev.html' });
pvPrev.textContent = '← orig-prev 文案';
const projInputs = ['p1', 'p2', 'p3', 'p4'].map(pid => mkEl('input', { 'data-pid': pid }));
const projLine = register('projLine', mkEl('div'));
register('progSummary', mkEl('p'));
const progText = register('progText', mkEl('textarea'));
const progExport = register('progExport', mkEl('button'));
const progImport = register('progImport', mkEl('button'));
const progMsg = register('progMsg', mkEl('span'));
const exitLine = register('exitLine', mkEl('div'));
register('depthToggle', mkEl('button'));
register('readToggle', mkEl('button', { 'data-slug': 'ch17' }));
register('ringMainFg', mkEl('circle')); register('ringMainN', mkEl('b'));
register('ringBranchFg', mkEl('circle')); register('ringBranchN', mkEl('b'));
register('ringMain', mkEl('div')); register('ringBranch', mkEl('div'));
register('termFilter', null); // 不存在于本 stub 语境

const lis = SD.chapters.map(c => mkEl('li', { 'data-slug': c.slug }));
const nodes = SD.chapters.map(c => mkEl('a', { 'data-slug': c.slug }));
const cards = SD.routes.map(r => {
  const c = mkEl('details', { 'data-route': r.id });
  const start = mkEl('a', { href: '#' });
  start.className = 'rc-start';
  c.appendChild(start);
  return c;
});
const sections = [];
SD.chapters.forEach(c => {
  if (STUB_CH.indexOf(c.slug) < 0) return;
  (c.sections || []).forEach(s => {
    if (s.level !== 2) return;
    const sec = mkEl('section', { 'data-anchor': s.anchor });
    sec.className = 'sec';
    sec.attrs.id = s.anchor;
    byId[s.anchor] = sec;
    sections.push(sec);
  });
});
const selfcheckSec = sections.find(s => s.getAttribute('data-anchor') === 'ch17-s10');
if (!selfcheckSec) throw new Error('stub missing ch17-s10');
const selfcheck = register('selfcheck', mkEl('p'));
selfcheckSec.appendChild(selfcheck);
const exitInputs = SD.routes.map(r => {
  const inp = mkEl('input', { 'data-route': r.id, 'data-idx': '0' });
  inp.checked = false;
  return inp;
});

global.document = {
  body: mkEl('body'),
  getElementById: id => byId[id] || null,
  querySelectorAll: sel => {
    if (sel === '.sidebar li.ch') return lis;
    if (sel === 'article.chapter section.sec') return sections;
    if (sel === '.node[data-slug]') return nodes;
    if (sel === '.route-card') return cards;
    if (sel === '.exit-check input') return exitInputs;
    if (sel === 'input[data-pid]') return projInputs;
    if (sel === 'a.selfcheck-jump') return [selfcheckJump];
    return [];
  },
  createElement: tag => mkEl(tag),
  createTextNode: () => ({}),
  querySelector: sel => {
    if (sel === '.prevnext a.pv-next') return pvNext;
    if (sel === '.prevnext a.pv-prev') return pvPrev;
    const m = /^article\.chapter section\[data-anchor="(.+)"\]$/.exec(sel);
    if (m) return sections.find(s => s.getAttribute('data-anchor') === m[1]) || null;
    return null;
  },
  addEventListener() {},
};
global.window = { addEventListener() {} };
global.location = { href: '' };
global.localStorage = { _m: {}, getItem(k) { return this._m[k] || null; }, setItem(k, v) { this._m[k] = String(v); } };

eval(fs.readFileSync(process.argv[5], 'utf8'));
const T = global.window.__T;

function sectionOf(anchor) { return sections.find(s => s.getAttribute('data-anchor') === anchor); }
function cardOf(anchor) { const s = sectionOf(anchor); if (!s) return null; return s.children.find(c => c._cls && c._cls.has('catchup-card')) || null; }

// 1) viewOf ≡ 内嵌 view
for (const r of SD.routes) {
  const v = T.viewOf(r.id);
  const same = JSON.stringify(v.disp) === JSON.stringify(r.view.disp)
    && JSON.stringify(v.dimSec) === JSON.stringify(r.view.dim_sections)
    && v.counts.main === r.view.counts.main
    && v.open === !!r.view.open
    && JSON.stringify(v.cards || {}) === JSON.stringify(r.view.cards || {})
    && JSON.stringify(v.next || {}) === JSON.stringify(r.view.next || {})
    && JSON.stringify(v.pos || {}) === JSON.stringify(r.view.pos || {})
    && (v.total || 0) === (r.view.total || 0);
  if (!same) fail('VIEW_MISMATCH ' + r.id);
}

// 2) 逐路线 applyRoute 效果
for (const r of SD.routes) {
  const e = EXP.routes[r.id];
  global.localStorage.setItem('series-route-v1', r.id);
  T.applyRoute(r.id);
  const gotBanner = banner.hidden ? 'read' : (banner.textContent.indexOf('不在') >= 0 ? 'dim' : 'focus');
  if (gotBanner !== e.banner) fail(r.id + ' banner ' + gotBanner + ' != ' + e.banner);
  for (const s of sections) {
    const an = s.getAttribute('data-anchor');
    const isDim = s._cls.has('dim');
    const wantDim = e.dims.indexOf(an) >= 0;
    if (isDim !== wantDim) fail(r.id + ' dim ' + an + ' ' + isDim + ' != ' + wantDim);
  }
  for (const a of Object.keys(e.cards)) {
    const c = cardOf(a);
    if (!c || c.textContent.indexOf(e.cards[a]) < 0) fail(r.id + ' card missing ' + a);
  }
  for (const s of sections) {
    const an = s.getAttribute('data-anchor');
    if (!(an in e.cards)) { const c = cardOf(an); if (c) fail(r.id + ' stray card ' + an); }
  }
  const wantNext = e.next || null;
  if (wantNext) {
    if (routeNext.hidden) fail(r.id + ' next hidden');
    else if (routeNext.getAttribute('href') !== wantNext + '.html') fail(r.id + ' next href ' + routeNext.getAttribute('href'));
    else {
      const c = SD.chapters.find(x => x.slug === wantNext);
      const lab = c ? c.label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') : '';
      if (lab && (routeNext.textContent.match(new RegExp(lab, 'g')) || []).length > 1)
        fail(r.id + ' next label duplicated: ' + routeNext.textContent);
    }
  } else if (!routeNext.hidden) fail(r.id + ' next should hide');
  if (byId['ringMainN'].textContent !== e.ring) fail(r.id + ' ring ' + byId['ringMainN'].textContent + ' != ' + e.ring);
  if (exitLine.textContent.indexOf('/' + e.exitN) < 0) fail(r.id + ' exitLine ' + exitLine.textContent);
  if (e.meta) {
    if (chapterMeta.textContent.indexOf('第 ' + e.meta[0] + '/' + e.meta[1] + ' 站') < 0)
      fail(r.id + ' meta ' + chapterMeta.textContent);
  } else if (chapterMeta.textContent !== '测试统计文本') {
    fail(r.id + ' meta should reset: ' + chapterMeta.textContent);
  }
}

// 3.5) 继续阅读/最近（seed → refreshResume）
global.localStorage.setItem('series-last-v1', JSON.stringify({ slug: 'ch17', anchor: 'ch17-s08', at: '2026-10-15' }));
global.localStorage.setItem('series-recent-v1', JSON.stringify(['ch17', 'ch01', 't3']));
T.refreshResume();
if (resumeBlock.hidden) fail('resume block hidden');
if (resumeLink.getAttribute('href') !== 'ch17.html#ch17-s08') fail('resume href ' + resumeLink.getAttribute('href'));
if (resumeLink.textContent.indexOf('§17') < 0) fail('resume text ' + resumeLink.textContent);
if ((resumeLink.textContent.match(/§17/g) || []).length !== 1) fail('resume label duplicated: ' + resumeLink.textContent);
if (recentList.children.length < 2) fail('recent list ' + recentList.children.length);

// 3) 自证勾选 → exitLine 更新（agent-fast idx0）
global.localStorage.setItem('series-route-v1', 'agent-fast');
T.applyRoute('agent-fast');
const inp = exitInputs.find(i => i.getAttribute('data-route') === 'agent-fast');
inp.checked = true; inp.dispatch('change');
if (exitLine.textContent.indexOf('1/') < 0) fail('exit check did not update: ' + exitLine.textContent);

// 3.6) 自测回流（H2-1）
T.refreshSelftestNote();
if (!selftestNote.children.some(c => c.getAttribute && c.getAttribute('href') === 'selftest.html'))
  fail('selftest note empty state');
global.localStorage.setItem('series-selftest-v1', JSON.stringify({ score: 3, at: '2026-10-15' }));
T.refreshSelftestNote();
if (selftestNote.textContent.indexOf('快线') < 0) fail('selftest band catchup: ' + selftestNote.textContent);
global.localStorage.setItem('series-selftest-v1', JSON.stringify({ score: 9, at: '2026-10-15' }));
T.refreshSelftestNote();
if (selftestNote.textContent.indexOf('直接走') < 0) fail('selftest band ready: ' + selftestNote.textContent);

// 3.7) 项目勾选（H2-3）
global.localStorage.setItem('series-projects-v1', JSON.stringify(['p1']));
T.refreshProjLine();
if (projLine.textContent.indexOf('1/4') < 0) fail('projLine ' + projLine.textContent);

// 3.8) 导出/导入（H2-5）
global.localStorage.setItem('series-route-v1', 'agent-fast');
global.localStorage.setItem('series-focus-v1', '"0"');
progExport.dispatch('click');
if (!progText.value || progText.value.indexOf('series-route-v1') < 0) fail('export missing keys');
if (progText.value.indexOf('series-focus-v1') < 0) fail('export missing focus key');
global.localStorage.setItem('series-progress-v1', JSON.stringify(['ch13', 'ch01']));
global.localStorage.setItem('series-route-v1', 'agent-fast');
T.applyRoute('agent-fast');
if (byId['ringMainN'].textContent !== '1/20') fail('ring numerator: ' + byId['ringMainN'].textContent);
progText.value = JSON.stringify({ v: 1, 'series-projects-v1': '["p2"]' });
progImport.dispatch('click');
if (global.localStorage.getItem('series-projects-v1') !== '["p2"]') fail('import did not write');
if (progMsg.textContent.indexOf('已导入') < 0) fail('import msg ' + progMsg.textContent);

// 3.9) 路线聚焦与自动跳站（读者反馈批）
global.localStorage.setItem('series-focus-v1', '"1"');
global.localStorage.setItem('series-route-v1', 'agent-fast');
T.applyRoute('agent-fast');
if (!global.document.body._cls.has('focus-hide')) fail('focus-hide not set');
if (!focusHide.checked) fail('focusHide checkbox not checked');
if (pvNext.getAttribute('href') !== 'ch18.html') fail('pvNext ' + pvNext.getAttribute('href'));
if (pvPrev.getAttribute('href') !== 'ch16.html') fail('pvPrev ' + pvPrev.getAttribute('href'));
if (pvNext.textContent.indexOf('§18') < 0 || pvNext.textContent.indexOf('orig') >= 0)
  fail('pvNext label: ' + pvNext.textContent);
if ((pvNext.textContent.match(/§18/g) || []).length !== 1)
  fail('pvNext label duplicated: ' + pvNext.textContent);
if (pvPrev.textContent.indexOf('§16') < 0 || pvPrev.textContent.indexOf('orig') >= 0)
  fail('pvPrev label: ' + pvPrev.textContent);
if (offrouteNote.textContent.indexOf('页不在路线上') < 0) fail('offrouteNote ' + offrouteNote.textContent);
focusHide.checked = false; focusHide.dispatch('change');
if (global.document.body._cls.has('focus-hide')) fail('focus-hide not cleared');
if ((global.localStorage.getItem('series-focus-v1') || '').indexOf('0') < 0) fail('focus pref not saved');
global.localStorage.setItem('series-progress-v1', JSON.stringify(['s0a', 's0b', 's0c']));
if (T.firstStation('taste') !== 'ch14.html#ch14-s05') fail('firstStation taste: ' + T.firstStation('taste'));
global.localStorage.setItem('series-progress-v1', JSON.stringify(['s0a', 's0b', 's0c', 'ch01']));
if (T.firstStation('agent-fast') !== 'ch02.html') fail('firstStation agent-fast: ' + T.firstStation('agent-fast'));
// §0/支线章标签不得重复前缀（读者反馈：'§0.2 §0.2 …'）
banner.setAttribute('data-slug', 's0a');
global.localStorage.setItem('series-route-v1', 'taste');
T.applyRoute('taste');
if (pvNext.textContent.indexOf('§0.2') < 0) fail('taste pvNext label: ' + pvNext.textContent);
if ((pvNext.textContent.match(/§0\.2/g) || []).length !== 1)
  fail('taste pvNext duplicated: ' + pvNext.textContent);
// 末站收尾出口：ch21 为 agent-fast 末站
banner.setAttribute('data-slug', 'ch21');
routeNext.setAttribute('data-slug', 'ch21');
chapterMeta.setAttribute('data-slug', 'ch21');
global.localStorage.setItem('series-route-v1', 'agent-fast');
T.applyRoute('agent-fast');
if (routeNext.hidden) fail('end station: next hidden');
if (routeNext.textContent.indexOf('收尾') < 0) fail('end station text: ' + routeNext.textContent);
if (routeNext.getAttribute('href') !== 'routes.html#route-agent-fast') fail('end station href: ' + routeNext.getAttribute('href'));
banner.setAttribute('data-slug', 'ch17');
routeNext.setAttribute('data-slug', 'ch17');
chapterMeta.setAttribute('data-slug', 'ch17');

// 3.10) 选线重置深浅偏好（选项 2）
global.localStorage.setItem('series-depth-v1', 'practice');
T.seedDepthFor('deep');
if (global.localStorage.getItem('series-depth-v1') !== 'theory') fail('seed deep: ' + global.localStorage.getItem('series-depth-v1'));
global.localStorage.setItem('series-depth-v1', 'theory');
T.seedDepthFor('agent-fast');
if (global.localStorage.getItem('series-depth-v1') !== 'practice') fail('seed fast: ' + global.localStorage.getItem('series-depth-v1'));
// 直接 applyRoute（模拟翻页/刷新）不应重置
global.localStorage.setItem('series-depth-v1', 'practice');
global.localStorage.setItem('series-route-v1', 'deep');
T.applyRoute('deep');
if (global.localStorage.getItem('series-depth-v1') !== 'practice') fail('applyRoute must not reseed');
// 卡片展开（deep）应选中并重置为 theory；跳转只由卡内“开始”触发
global.localStorage.setItem('series-progress-v1', '[]');
global.localStorage.setItem('series-route-v1', 'agent-fast');
const deepCard = cards.find(c => c.getAttribute('data-route') === 'deep');
global.location.href = '';
deepCard.open = true;
deepCard.dispatch('toggle');
if (global.localStorage.getItem('series-depth-v1') !== 'theory') fail('card open seed: ' + global.localStorage.getItem('series-depth-v1'));
if ((global.location.href || '').indexOf('s0a') >= 0) fail('card open must not navigate: ' + global.location.href);
const deepStart = deepCard.querySelector('.rc-start');
if (!deepStart || (deepStart.getAttribute('href') || '').indexOf('s0a') < 0)
  fail('card start href: ' + (deepStart && deepStart.getAttribute('href')));
if (!deepCard._cls.has('active')) fail('card not active after open');

// 3.11) 复习抽查（P1 缓做项）
global.localStorage.setItem('series-progress-v1', JSON.stringify(['ch01', 'ch05']));
T.refreshReview();
if (reviewBlock.hidden) fail('review block hidden with progress');
if (reviewList.children.length !== 2) fail('review list count: ' + reviewList.children.length);
const rvA = reviewList.children[0].children.find(c => c.tag === 'a');
if (!rvA || !/\.html#/.test(rvA.attrs.href || '')) fail('review link href: ' + (rvA && rvA.attrs.href));
const secA = sectionOf('ch17-s01');
secA.classList.add('dim');
reviewLink.dispatch('click');
if (!secA.classList.contains('offroute-shown')) fail('review link reveal');
secA.classList.remove('dim'); secA.classList.remove('offroute-shown');

// 3.11b) 自查锚在节内：reviewLink 与 selfcheck-jump 都要先展开所属节
selfcheckSec.classList.add('dim');
global.document.body.classList.add('focus-hide');
reviewLink.setAttribute('data-anchor', 'selfcheck');
reviewLink.dispatch('click');
if (!selfcheckSec.classList.contains('offroute-shown')) fail('review selfcheck reveal');
selfcheckSec.classList.remove('offroute-shown');
selfcheckJump.dispatch('click');
if (!selfcheckSec.classList.contains('offroute-shown')) fail('selfcheck jump reveal');
selfcheckSec.classList.remove('dim');
selfcheckSec.classList.remove('offroute-shown');
global.document.body.classList.remove('focus-hide');

// 3.12) 支线理由从数据计算（无 R 编号；含路线名）
const br = T.branchReason();
if (/R[0-9]/.test(br)) fail('branch reason still has R codes: ' + br);
if (br.indexOf('生成方向') < 0 || br.indexOf('深究线') < 0) fail('branch reason names: ' + br);

// 4) 自由读复原
global.localStorage.setItem('series-route-v1', 'free');
T.applyRoute('free');
if (!banner.hidden) fail('free: banner not hidden');
if (sections.some(s => s._cls.has('dim'))) fail('free: dims remain');
if (sections.some(s => cardOf(s.getAttribute('data-anchor')))) fail('free: cards remain');
if (!routeNext.hidden) fail('free: next not hidden');
if (!exitLine.hidden) fail('free: exitLine not hidden');
if (pvNext.textContent.indexOf('orig') < 0) fail('free: pvNext label not restored: ' + pvNext.textContent);
if (pvPrev.textContent.indexOf('orig') < 0) fail('free: pvPrev label not restored: ' + pvPrev.textContent);

console.log(bad ? ('FAIL ' + bad) : 'PASS');
"""


def main() -> int:
    tpl = (HERE / "site_template.html").read_text(encoding="utf-8")
    scripts = re.findall(r"<script>(.*?)</script>", tpl, re.S)
    js = scripts[-1]
    js = js.replace(
        "  applyRoute(getRouteId());\n  setRouteCardOpen(getRouteId());\n})();",
        "  window.__T = { viewOf: viewOf, recommend: recommend, ROUTER_MAP: ROUTER_MAP,\n"
        "                 findRoute: findRoute, nodeMins: nodeMins, freeDisp: freeDisp,\n"
        "                 applyRoute: applyRoute, refreshResume: refreshResume,\n"
        "                 refreshSelftestNote: refreshSelftestNote, refreshProjLine: refreshProjLine,\n"
        "                 refreshProgSummary: refreshProgSummary, firstStation: firstStation,\n"
        "                 focusPref: focusPref, seedDepthFor: seedDepthFor, branchReason: branchReason,\n"
        "                 refreshReview: refreshReview };\n})();")
    assert "window.__T" in js

    sd_m = re.search(r'<script type="application/json" id="series-data">(.*?)</script>',
                     (DIST / "index.html").read_text(encoding="utf-8"), re.S)
    sd = json.loads(sd_m.group(1))
    exp = build_expectations(sd)

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        (tdp / "data.json").write_text(sd_m.group(1), encoding="utf-8")
        (tdp / "exp.json").write_text(json.dumps(exp, ensure_ascii=False), encoding="utf-8")
        (tdp / "stub.json").write_text(json.dumps(STUB_CH), encoding="utf-8")
        (tdp / "chunk.js").write_text(js, encoding="utf-8")
        (tdp / "test.js").write_text(NODE_TEST, encoding="utf-8")
        r = subprocess.run(["node", str(tdp / "test.js"), str(tdp / "data.json"),
                            str(tdp / "exp.json"), str(tdp / "stub.json"), str(tdp / "chunk.js")],
                           capture_output=True, text=True, timeout=120)
    out = (r.stdout or "").strip()
    print(out if out else (r.stderr or "").strip()[-600:])
    if "PASS" in out and r.returncode == 0:
        print("· 路线层 JS 对拍：viewOf≡视图 9/9｜banner/降灰/补课卡/下一站/环/自证/站位/继续阅读 逐路线 ✓｜自查节内锚/自测三档/项目计数/导出导入 ✓｜自由读复原 ✓")
        return 0
    print("route_js_check: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
