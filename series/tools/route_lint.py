#!/usr/bin/env python3
"""route_lint.py — 路线质量闸工具（2026-10-14 批 3，G1–G4）。

对 9 条路线做：
- G1/G3：出口清单、自证题、时数（与 check_routes 互证，导出报告）；
- G2：断链候选——路线「保留文本」中出现的跨章引用（§N／§N.M／第 N 章／TN），
  凡指向路线未读内容且未在 routes.json 的 catchups/exempt/supply 里声明者，列为候选中；
- G4：供给存在性（terms.html/env.html 等路由声明）。

注意：routes.json 的 exempt/catchups 文本中出现的 §N 显式 token 是 G2 的探针输入——
改写豁免措辞时必须保留对应 token（先例：R5 改「§15–§20 全覆盖」后 ch21 的 §18 后向转红）。

输出：series/.tmp/route_lint.md（报告）＋控制台摘要。
退出码：--check 时，有未声明候选或 G1/G3/G4 未过 → 1；否则 0。
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_site as bs  # noqa: E402

SERIES = bs.SERIES
DIST = bs.DIST
PROFILES = bs.PROFILES

CHAPTER_REF = re.compile(r"§(0\.\d|\d{1,2}(?:\.\d+)?)")
BRANCH_REF = re.compile(r"\bT([1-4])\b")
CHAP_CN_REF = re.compile(r"第\s?(\d{1,2})\s?章")
FENCE = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`]*`")

S0_MAP = {"0.1": "s0a", "0.2": "s0b", "0.3": "s0c"}


def strip_noise(text: str) -> str:
    text = FENCE.sub("", text)
    text = INLINE.sub("", text)
    return text


def load_chapters():
    chapters, parts = bs.load_chapters()
    for ch in chapters:
        raw = (SERIES / ch["file"]).read_text(encoding="utf-8")
        _, info = bs.scan_and_rewrite(bs.norm_structure(raw), ch["slug"])
        ch["sections"] = info["sections"]
        ch["raw"] = raw
    return chapters


def section_texts(raw: str) -> tuple[str, dict[int, tuple[int, str]]]:
    """→（章首导语, {h2 序: (起始行号, 正文)}）。h2 序从 1 起，与 sections level==2 顺序一致。"""
    lines = raw.split("\n")
    lead: list[str] = []
    secs: dict[int, list] = {}
    cur = None
    for i, ln in enumerate(lines, start=1):
        if ln.startswith("## "):
            cur = len(secs) + 1
            secs[cur] = [i, []]
        elif cur is None:
            lead.append(ln)
        else:
            secs[cur][1].append(ln)
    return "\n".join(lead), {k: (v[0], "\n".join(v[1])) for k, v in secs.items()}


def kept_text(route: dict, chapters: list[dict]) -> list[tuple[str, str, int]]:
    """路线保留文本 → [(slug, 文本块, 起始行号)]；含 read 全章与 focus 所列节。"""
    seq = {e["ch"]: e for e in route["sequence"]}
    out: list[tuple[str, str, int]] = []
    for ch in chapters:
        e = seq.get(ch["slug"])
        if e is None:
            continue
        lead, secs = section_texts(ch["raw"])
        if e["mode"] == "read":
            out.append((ch["slug"], ch["raw"], 1))
            continue
        h2s = [s for s in ch["sections"] if s["level"] == 2]
        for i, s in enumerate(h2s, start=1):
            if s["anchor"] in (e.get("sections") or []):
                line, body = secs.get(i, (0, ""))
                out.append((ch["slug"], body, line))
    return out


def route_declared_text(route: dict) -> str:
    return json.dumps(route, ensure_ascii=False)


def resolve_ref(tok: str, chapters_by_slug: dict) -> tuple[str, str] | None:
    """引用 token →（目标章 slug, 目标节锚 or ""）。"""
    if tok in S0_MAP:
        return S0_MAP[tok], ""
    if "." in tok:
        num, sec = tok.split(".", 1)
        slug = f"ch{int(num):02d}"
        anchor = f"{slug}-s{int(sec):02d}"
        return slug, anchor
    slug = f"ch{int(tok):02d}"
    return slug, ""


def lint_route(route: dict, chapters: list[dict], fwd_policy: str = "") -> tuple[list[dict], list[str]]:
    by_slug = {c["slug"]: c for c in chapters}
    order = {c["slug"]: i for i, c in enumerate(chapters)}
    seq = {e["ch"]: e for e in route["sequence"]}
    declared = route_declared_text(route)
    candidates: list[dict] = []
    seen: set[tuple] = set()

    def add_cand(slug: str, tok: str, tgt: str, reason: str, line: int, probe: list[str]) -> None:
        key = (slug, tok, tgt)
        if key in seen:
            return
        seen.add(key)
        cls = "fwd" if order.get(tgt, 0) > order.get(slug, 0) else "back"
        declared_hit = any(p and p in declared for p in probe)
        if cls == "fwd" and not declared_hit and fwd_policy:
            declared_hit = True
            reason = (reason or "") + "｜前向门牌（政策豁免）"
        candidates.append({"route": route["id"], "where": f"{slug}:{line}",
                           "ref": tok, "target": tgt, "reason": reason,
                           "cls": cls, "declared": declared_hit, "probe": probe})

    def kept_state(slug: str) -> str:
        e = seq.get(slug)
        if e is None:
            return "skip"
        return "read" if e["mode"] == "read" else "focus"

    for slug, text, offset in kept_text(route, chapters):
        clean = strip_noise(text)
        def line_at(pos: int) -> int:
            return offset + clean[:pos].count("\n")
        for m in CHAPTER_REF.finditer(clean):
            tok = m.group(1)
            r = resolve_ref(tok, by_slug)
            if not r:
                continue
            tgt, anchor = r
            if tgt not in by_slug:
                continue
            state = kept_state(tgt)
            reason = None
            if state == "skip":
                reason = "目标章未读"
            elif state == "focus" and anchor:
                focus = set((seq.get(tgt) or {}).get("sections") or [])
                if anchor not in focus:
                    reason = "目标节不在焦点清单"
            if reason is None:
                continue
            probe = [f"§{tok}", f"ch{tgt.replace('ch', '')}", tgt]
            if anchor:
                probe.append(anchor)
            add_cand(slug, f"§{tok}", tgt, reason, line_at(m.start()), probe)
        for m in BRANCH_REF.finditer(clean):
            tgt = f"t{m.group(1)}"
            if tgt not in by_slug:
                continue
            state = kept_state(tgt)
            if state != "skip":
                continue
            add_cand(slug, f"T{m.group(1)}", tgt, "目标章未读", line_at(m.start()), [f"T{m.group(1)}"])
        for m in CHAP_CN_REF.finditer(clean):
            num = int(m.group(1))
            if num < 1 or num > 21:
                continue
            tgt = f"ch{num:02d}"
            state = kept_state(tgt)
            if state != "skip":
                continue
            add_cand(slug, f"第 {num} 章", tgt, "目标章未读", line_at(m.start()),
                     [f"第 {num} 章", f"第{num}章", f"§{num}"])

    supply_issues = []
    for s in route.get("supply", []):
        if s.endswith(".html") and not (DIST / s).exists():
            supply_issues.append(s)
    return candidates, supply_issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="有未声明候选时退出码 1")
    args = ap.parse_args()

    cfg = json.loads((PROFILES / "routes.json").read_text(encoding="utf-8"))
    fwd_policy = (cfg.get("lint") or {}).get("fwd_policy", "")
    chapters = load_chapters()

    rows: list[dict] = []
    supply_all: dict[str, list[str]] = {}
    g1g3 = []
    for r in cfg["routes"]:
        if not r.get("exit") or len(r.get("selfcheck", [])) < 2 or not r["hours"]["read"]:
            g1g3.append(r["id"])
        cand, sup = lint_route(r, chapters, fwd_policy)
        rows.extend(cand)
        if sup:
            supply_all[r["id"]] = sup

    undeclared = [c for c in rows if not c["declared"]]
    back = [c for c in undeclared if c["cls"] == "back"]
    fwd = [c for c in undeclared if c["cls"] == "fwd"]
    declared = [c for c in rows if c["declared"]]

    lines = ["# route_lint 报告（批 3）", "",
             f"- 路线：{len(cfg['routes'])} 条；候选引用：{len(rows)}（已声明 {len(declared)}／"
             f"未声明·后向 {len(back)}／未声明·前向 {len(fwd)}）",
             f"- G1/G3（出口/自证/时数）：{'全部通过' if not g1g3 else '未过：' + ', '.join(g1g3)}",
             f"- G4（供给存在性）：{'通过' if not supply_all else '缺：' + json.dumps(supply_all, ensure_ascii=False)}",
             ""]
    if back:
        lines.append("## 未声明·后向（必办：补课卡/豁免/调正文）")
        lines.append("")
        lines.append("| 路线 | 位置 | 引用 | 目标 | 原因 |")
        lines.append("|---|---|---|---|---|")
        for c in sorted(back, key=lambda x: (x["route"], x["where"])):
            lines.append(f"| {c['route']} | {c['where']} | {c['ref']} | {c['target']} | {c['reason']} |")
        lines.append("")
    if fwd:
        lines.append("## 未声明·前向（承诺类：复核是否留下悬空承诺）")
        lines.append("")
        lines.append("| 路线 | 位置 | 引用 | 目标 | 原因 |")
        lines.append("|---|---|---|---|---|")
        for c in sorted(fwd, key=lambda x: (x["route"], x["where"])):
            lines.append(f"| {c['route']} | {c['where']} | {c['ref']} | {c['target']} | {c['reason']} |")
        lines.append("")
    if declared:
        lines.append("## 已声明（catchups/exempt 覆盖，抽样 40 条）")
        lines.append("")
        lines.append("| 路线 | 位置 | 引用 | 目标 |")
        lines.append("|---|---|---|---|")
        for c in declared[:40]:
            lines.append(f"| {c['route']} | {c['where']} | {c['ref']} | {c['target']} |")
        lines.append("")
    report = "\n".join(lines)
    (SERIES / ".tmp").mkdir(exist_ok=True)
    (SERIES / ".tmp" / "route_lint.md").write_text(report, encoding="utf-8")
    print(f"route_lint：候选 {len(rows)}（未声明 后向 {len(back)}／前向 {len(fwd)}）｜"
          f"G1/G3 {'OK' if not g1g3 else 'FAIL'}｜G4 {'OK' if not supply_all else 'FAIL'}"
          f"｜报告 series/.tmp/route_lint.md")
    for c in back[:25]:
        print(f"  ✗[后向] {c['route']:12s} {c['where']:12s} {c['ref']:8s} → {c['target']}（{c['reason']}）")
    if args.check and (back or g1g3 or supply_all):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
