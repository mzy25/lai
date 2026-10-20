#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""metaphor_scan：喻体预算与台账健康扫描（2026-10-17 复议论立项）。

只定位不判罚；exit 0（--strict 时 WARN 退 1）。四节：
  A 台账健康：零命中行／重复登记／行号漂移候选（跳过含退役标记的行）
  B 标题含喻：H1/H2 命中在册装置词（节题不装比喻，2026-10-16 第四问）
  C 密度告警：死喻/惯例词超过上限（CAPS）
  D 装置密度：每章命中在册装置的行数 top（口径提示，不是判罚）

用法：
  python3 series/tools/metaphor_scan.py            # 全量扫描
  python3 series/tools/metaphor_scan.py --selftest # 纯函数自测
  python3 series/tools/metaphor_scan.py --strict   # WARN 退 1（默认 exit 0）
"""
from __future__ import annotations

import glob
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # series/
LEDGER = ROOT / "style/喻体台账.md"
SKIP_MARK = re.compile(r"退役|撤册|撤除|出册|转惯用|非喻体|并入|直说化|改名")

# 死喻/惯例词密度上限（复议 2026-10-17 判定，软告警）
CAPS = {
    "考试域": (["考卷", "考场", "卷子", "答卷", "评判员"], 14),  # 首次定档＝现状 14（只减不增；目标 5 列观察）
    "通用墙": (["撞墙", "一堵墙", "同一堵墙", "两道物理墙"], 8),
    "通用打折": (["打折"], 4),
    "橡皮图章": (["橡皮图章"], 3),
    "照猫画虎": (["照猫画虎"], 3),
}

# B 标题含喻白名单（2026-10-17 二轮逐条判：改 2／留 16，理由见复议报告 §八）
TITLE_KEEP = {
    "零件在真实系统里定位": "零件＝工程/行业语（T4 框架词）",
    "岗位出口": "职业出口字面义",
    "成核": "科学术语（机制名）",
    "跑通最小骨架": "骨架＝工程义（代码骨架）",
    "双轴表": "表名非喻",
    "两个出口": "B 伏笔兑付名（F01）",
    "一半是预测": "一半＝数量义近字面",
    "可验证性 razor": "判据专名（节题即术语命名）",
    "影子价格": "经济学术语（与影子喻分立）",
    "脊柱": "全章主线结构名（R11 登记）",
    "能反悔": "章题读者承诺词（R13 判留，正文机制用回滚）",
    "压缩即理解": "章主张本体（A）",
    "两阶段训练配方": "行业惯用（two-stage recipe）",
    "配方能大小通吃": "行业惯用（章题）",
    "从黑箱到配方": "行业惯用",
    "主线速览版 SD 配方": "行业惯用（附录名）",
    "逐词生成的引擎": "通用技术词",
    "正反两个读数": "A 载重核心词（旋钮）题内保留，随定名复判",
    "三级台阶与三问": "跨章指针名（§19×2、§21×1）",
    "半个未决": "跨引名（§14×2）",
    "瘦身": "节题技术惯用（台账在册，登记不更名）",
    "回收地图": "结构名节题（登记行在册，三义分立）",
    "概率速查：四张卡片": "速查装置名（台账在册，非修辞喻）",
    "概率回访：四张卡片": "回访节题（装置名设计内回收，台账行在册）",
}

# A1/A3 已判豁免（描述性行名与历史引用噪声，2026-10-17 二轮）
A1_EXEMPT = {"餐馆追责", "乐器上调节旋钮", "房间白噪音音量", "电视雪花屏",
             "谷底热噪声（势能场）", "广场人群",
             "考试域单点群（同词不同考场／同一张卷子的两面／答卷）", "铺轨／换轨（连接器）"}
A3_EXEMPT = {"钥匙（句）", "铺轨／换轨（连接器）", "原料·喂·口味（喂养簇）",
             "押（下注类动词）", "深潜·上岸"}


def chapter_files() -> list[Path]:
    fs = (sorted(glob.glob(str(ROOT / "§*.md")))
          + sorted(glob.glob(str(ROOT / "T*.md")))
          + sorted(glob.glob(str(ROOT / "支线*.md"))))
    return [Path(f) for f in fs]


def tok(fn: str) -> str:
    return Path(fn).name.split("-")[0]


def split_tokens(name: str) -> list[str]:
    base = re.sub(r"（[^）]*）", "", name).replace("复用备案", "").strip("* ")
    parts = re.split(r"[／、，;；＋]|与", base)
    out: list[str] = []
    for p in parts:
        p = p.strip().strip("*（） ").strip()
        if len(p) >= 2 and not re.search(r"[·—＋]", p):
            out.append(p)
    return out


def load_ledger() -> list[tuple[int, str, bool, list[str], str]]:
    rows = []
    for i, ln in enumerate(LEDGER.read_text(encoding="utf-8").splitlines(), 1):
        t = ln.strip()
        if not t.startswith("|") or "---" in t:
            continue
        cols = [c.strip() for c in t.strip("|").split("|")]
        name = cols[0]
        if not name or name in ("喻体/装置", "喻体", "装置") or re.match(r"第\d+ ?章", name):
            continue
        retired = bool(SKIP_MARK.search(ln))
        rows.append((i, name, retired, split_tokens(name), ln))
    return rows


def load_chapters() -> dict[str, list[str]]:
    return {tok(str(f)): f.read_text(encoding="utf-8").splitlines() for f in chapter_files()}


def scan_zero(rows, corpus):
    out = []
    for i, name, retired, toks, _ln in rows:
        if retired or not toks or name in A1_EXEMPT:
            continue
        hit = sum(1 for tk in toks for L in corpus.values() for l in L if tk in l)
        if hit == 0:
            out.append((i, name, toks))
    return out


def scan_dup(rows):
    prim: dict[str, list[int]] = {}
    for i, name, retired, toks, _ln in rows:
        if retired:
            continue
        prim.setdefault(name.strip("* "), []).append(i)
    return [(k, v) for k, v in prim.items() if len(v) > 1]


def scan_titles(rows, corpus):
    alltoks = sorted({t for *_x, toks, _ln in rows if not _x[2] for t in toks}, key=len, reverse=True)
    out = []
    kept = 0
    for fk, L in sorted(corpus.items()):
        for i, l in enumerate(L, 1):
            if not l.startswith("#"):
                continue
            hits = [t for t in alltoks if t in l]
            if not hits:
                continue
            if any(k in l for k in TITLE_KEEP):
                kept += 1
                continue
            out.append((fk, i, l.strip()[:90], hits))
    return out, kept


def scan_density(rows, corpus):
    alltoks = {t for *_x, toks, _ln in rows if not _x[2] for t in toks}
    per = []
    for fk, L in corpus.items():
        n = sum(1 for l in L if any(t in l for t in alltoks))
        per.append((fk, n))
    return sorted(per, key=lambda x: -x[1])


def scan_caps(corpus):
    out = []
    for label, (words, cap) in CAPS.items():
        n = sum(1 for L in corpus.values() for l in L if any(w in l for w in words))
        if n > cap:
            out.append((label, n, cap, words))
    return out


def scan_drift(rows, corpus):
    out = []
    rx = re.compile(r"(§\d+(?:\.\d+)?|T\d|支线导言|支线附录)\s*L(\d+)")
    for i, name, retired, toks, ln in rows:
        if retired or "复议" in ln or name in A3_EXEMPT or not toks:
            continue
        for m in rx.finditer(ln):
            key, num = m.group(1), int(m.group(2))
            L = corpus.get(key)
            if not L or num > len(L):
                continue
            window = "\n".join(L[max(0, num - 3):num + 2])
            if not near(window, toks):
                out.append((i, name, key, num))
    return out


def near(window: str, toks: list[str]) -> bool:
    """任一装置词整词或其二字切片出现在窗口内即算命中（描述性行名兜底）。"""
    for t in toks:
        if t in window:
            return True
        for j in range(len(t) - 1):
            if t[j:j + 2] in window:
                return True
    return False


def selftest() -> None:
    assert tok("§0.1-大模型.md") == "§0.1"
    assert tok("T2-知道了.md") == "T2"
    assert split_tokens("双胞胎／毛坯／门票与判决书") == ["双胞胎", "毛坯", "门票", "判决书"]
    assert split_tokens("一把时钟（两速度）") == ["一把时钟"]
    assert split_tokens("执照") == ["执照"]
    corpus = {"x": ["价格打折了", "打折"]}
    n = sum(1 for L in corpus.values() for l in L if any(w in l for w in ["打折"]))
    assert n == 2
    assert bool(SKIP_MARK.search("| 合同 | —（退役） |")) is True
    assert bool(SKIP_MARK.search("| 墙 | 建筑 |")) is False
    assert any(k in "## 动手：六站，前五站跑通最小骨架" for k in TITLE_KEEP)
    assert "餐馆追责" in A1_EXEMPT
    print("metaphor_scan selftest OK")


def main() -> int:
    args = set(sys.argv[1:])
    if "--selftest" in args:
        selftest()
        return 0
    rows = load_ledger()
    corpus = load_chapters()
    print(f"metaphor_scan：台账数据行 {len(rows)} ／ 章节文件 {len(corpus)}")
    z = scan_zero(rows, corpus)
    print(f"\n[A1] 零命中行（候退役）{len(z)}（已判豁免 {len(A1_EXEMPT)} 条）：")
    for i, name, toks in z[:20]:
        print(f"  L{i} {name}（词：{'/'.join(toks[:4])}）")
    d = scan_dup(rows)
    print(f"\n[A2] 重复登记 {len(d)}：")
    for k, v in d[:10]:
        print(f"  {k} → L{v}")
    dr = scan_drift(rows, corpus)
    print(f"\n[A3] 行号漂移候选 {len(dr)}：")
    for i, name, key, num in dr[:20]:
        print(f"  L{i} {name} → {key} L{num}")
    ti, kept = scan_titles(rows, corpus)
    print(f"\n[B] 标题含喻候选 {len(ti)}（已判保留 {kept} 条入白名单）：")
    for fk, i, txt, hits in ti[:30]:
        print(f"  {fk} L{i} {txt} ← {'/'.join(hits[:4])}")
    ca = scan_caps(corpus)
    print(f"\n[C] 密度超限 {len(ca)}：")
    for label, n, cap, words in ca:
        print(f"  {label}：{n} ＞ {cap}（{'/'.join(words)}）")
    de = scan_density(rows, corpus)
    print(f"\n[D] 装置密度 top12（命中在册装置词的行数）：")
    for fk, n in de[:12]:
        print(f"  {fk}: {n}")
    warn = len(z) + len(d) + len(dr) + len(ti) + len(ca)
    print(f"\n合计候选 {warn}（只定位；判读按复议报告 §四 治理五件套）")
    if "--strict" in args and warn:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
