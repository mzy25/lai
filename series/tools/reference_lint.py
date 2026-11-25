#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reference_lint：跨章回指、定义承诺与旧词残留检查。

只做可验证的引用检查，不判断文笔：
  A 配置中的旧词是否仍出现在指定章节
  B “后文简称 X”之后是否真的再次使用 X
  C 高风险表达式（已知的坏搭配）是否重现
  D “§N 那套 X”这类回指，X 是否还能在 §N 找到（启发式，WARN）
  E 段内前向指针预算：线性读物里指向后章的 §N 引用会打断读者（2026-11-19 立；
    §0.1 全书地图与 §0.2 查阅页豁免；章末回望、表格、details 不计）

用法：
  python3 series/tools/reference_lint.py
  python3 series/tools/reference_lint.py --strict  # WARN 也退 1
  python3 series/tools/reference_lint.py --selftest
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data/引用一致性.tsv"

DEF_RE = re.compile(
    r"(?:后文|下文|后面|以下)(?:简称|称为|叫作|叫)[“\"「]?([^”\"」’，。；：\s]{1,30})"
)
CROSS_RE = re.compile(
    r"§(\d+(?:\.\d+)?)[^。；\n]{0,12}?(?:那套|这套)[ \t]*([^，。；：、\n]{2,20})"
)
RISK_RE = re.compile(r"件套|装配|机器|零件|墙|阶梯|闭环|翻车|长出|台阶")
BAD_PATTERNS = [
    (
        re.compile(r"跨过[^。；\n]{0,8}约束"),
        "“跨过……约束”搭配不顺；约束通常用“满足/受……约束”，障碍或门槛才用“跨过”",
    ),
]
SPLIT_RE = re.compile(r"结构|系统|方案|方法|东西|部件|组件|部分|流程|机制|规则|设置|做法")


def chapter_files() -> list[Path]:
    files = sorted(ROOT.glob("§*.md"))
    files += sorted(ROOT.glob("T*.md"))
    files += [p for p in (ROOT / "intro.md", ROOT / "recipe.md") if p.exists()]
    return files


def label_of(path: Path) -> str:
    m = re.match(r"^§(\d+(?:\.\d+)?)", path.name)
    if m:
        return "§" + m.group(1)
    m = re.match(r"^(T\d+)", path.name)
    if m:
        return m.group(1)
    return path.stem


def in_scope(label: str, scope: str) -> bool:
    scope = scope.strip()
    if not scope or scope.lower() == "global":
        return True
    for part in re.split(r"[,，、]", scope):
        part = part.strip().lstrip("§")
        if part and label.lstrip("§") == part:
            return True
    return False


def load_migrations() -> list[tuple[str, str, str, str]]:
    if not CONFIG.exists():
        return []
    rows = []
    for raw in CONFIG.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#"):
            continue
        cols = raw.split("\t")
        if len(cols) < 4:
            continue
        old, new, scope, note = (c.strip() for c in cols[:4])
        if old:
            rows.append((old, new, scope, note))
    return rows


def check_migrations(files: list[Path]) -> tuple[int, int]:
    migrations = load_migrations()
    errors = warnings = 0
    for path in files:
        label = label_of(path)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            for old, new, scope, note in migrations:
                if old in line and in_scope(label, scope):
                    print(
                        f"ERROR {path.name}:{lineno}: 旧词“{old}”仍在范围内；"
                        f"改用“{new}”（{note}）"
                    )
                    errors += 1
    return errors, warnings


def check_definition_promises(files: list[Path]) -> tuple[int, int]:
    errors = warnings = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        for m in DEF_RE.finditer(text):
            term = m.group(1).strip("“”\"'「」")
            if len(term) < 2:
                continue
            later = text[m.end():]
            if term not in later:
                line = text[: m.start()].count("\n") + 1
                print(
                    f"ERROR {path.name}:{line}: 约定“后文简称 {term}”，"
                    f"但定义之后没有再使用 {term}"
                )
                errors += 1
    return errors, warnings


def check_bad_patterns(files: list[Path]) -> tuple[int, int]:
    errors = warnings = 0
    for path in files:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for pattern, message in BAD_PATTERNS:
                if pattern.search(line):
                    print(f"ERROR {path.name}:{lineno}: {message}")
                    errors += 1
    return errors, warnings


FORWARD_BUDGET = 2
FORWARD_EXEMPT = {"§0.1", "§0.2"}

# 快照词：出现在主线机制句里即 WARN（白名单：同一 <details>、表格、引注括号内豁免）
SNAPSHOT_WORDS = ["U-Net", "DiT", "MM-DiT", "adaLN", "Sora", "AlphaEdit", "WilKE",
                  "Qwen-Scope", "LatentMAS", "SkillDroid", "ARC-Bench", "TaarofBench",
                  "IdeaScientist", "RoboJEPA", "EvoAgentBench"]
SNAPSHOT_SEAL = re.compile(r"截至|快照|早期|202[456] 年|（\d{4} 年|（[^）]{0,60}20[2-6]\d[，,]")


def check_snapshot_position(files: list[Path]) -> tuple[int, int]:
    """快照词出现在未封条的机制句里 → WARN。"""
    errors = warnings = 0
    for path in files:
        lab = label_of(path)
        if lab in FORWARD_EXEMPT:
            continue
        text = path.read_text(encoding="utf-8")
        # 只扫正文（去 details），不去回望（回收地图里的快照词合法）
        head = text.split("\n## 回望")[0]
        head = re.sub(r"<details.*?</details>", "", head, flags=re.S)
        # 去表格行
        head = re.sub(r"^\|.*$", "", head, flags=re.M)
        # 去图注行
        head = re.sub(r"^〔图.*$", "", head, flags=re.M)
        for lineno, line in enumerate(head.splitlines(), 1):
            for w in SNAPSHOT_WORDS:
                if w not in line:
                    continue
                if SNAPSHOT_SEAL.search(line):
                    continue
                # 同段（±2 行）有封条就放过
                lines = head.splitlines()
                ctx = "\n".join(lines[max(0, lineno - 10):lineno + 10])
                if SNAPSHOT_SEAL.search(ctx):
                    continue
                print(
                    f"WARN {path.name}:{lineno}: 快照词『{w}』出现在机制句里，"
                    f"且无日期封条；改法：角色名承担机制，快照词降为括号例证并补封条"
                )
                warnings += 1
    return errors, warnings


def _label_num(label: str) -> float:
    return float(label[1:])


def forward_refs(text: str, labels: list[str], own: str) -> list[str]:
    """正文段内指向后章的 §N 引用（不计回望、表格、details）。"""
    head = text.split("\n## 回望")[0]
    head = re.sub(r"<details.*?</details>", "", head, flags=re.S)
    head = re.sub(r"^\|.*$", "", head, flags=re.M)
    head = re.sub(r"^〔图.*$", "", head, flags=re.M)
    out = []
    for m in re.finditer(r"§(\d+(?:\.\d+)?)", head):
        lab = "§" + m.group(1)
        if lab in labels and _label_num(lab) > _label_num(own):
            out.append(lab)
    return out


def check_forward_budget(files: list[Path]) -> tuple[int, int]:
    labels = sorted(
        {label_of(p) for p in files if re.match(r"^§\d", label_of(p))},
        key=_label_num,
    )
    errors = 0
    for path in files:
        lab = label_of(path)
        if lab not in labels or lab in FORWARD_EXEMPT:
            continue
        refs = forward_refs(path.read_text(encoding="utf-8"), labels, lab)
        if len(refs) > FORWARD_BUDGET:
            print(
                f"ERROR {path.name}: 段内前向指针 {len(refs)} 处 > 预算 {FORWARD_BUDGET}"
                f"（{','.join(refs)}）；改法见系列写作规范·互引纪律"
            )
            errors += 1
    return errors, 0


def check_cross_refs(files: list[Path]) -> tuple[int, int]:
    errors = warnings = 0
    texts = {label_of(p): p.read_text(encoding="utf-8") for p in files}
    for path in files:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for m in CROSS_RE.finditer(line):
                target = "§" + m.group(1)
                phrase = m.group(2).strip()
                if target not in texts or len(phrase) < 2:
                    continue
                target_text = texts[target]
                if phrase in target_text:
                    continue
                parts = [x for x in SPLIT_RE.split(phrase) if len(x) >= 2]
                if any(x in target_text for x in parts):
                    continue
                if RISK_RE.search(phrase):
                    print(
                        f"WARN {path.name}:{lineno}: 回指“{target} 那套 {phrase}”，"
                        f"但 {target} 中找不到该说法；请确认是否已改名"
                    )
                    warnings += 1
    return errors, warnings


def selftest() -> int:
    assert DEF_RE.search('后文简称“地板”；').group(1) == "地板"
    assert DEF_RE.search("以下简称三件套。").group(1) == "三件套"
    assert CROSS_RE.search("还是 §6 那套三件套，等比缩小").groups() == ("6", "三件套")
    assert in_scope("§6", "§6,§7")
    assert not in_scope("§8", "§6,§7")
    labels = [f"§{i}" for i in range(1, 4)] + ["§0.1", "§9"]
    assert forward_refs("这里见 §9 的专页。", labels, "§1") == ["§9"]
    assert forward_refs("§1 已经立过。", labels, "§9") == []
    assert forward_refs("§9 先记。\n\n## 回望与下一章\n\n§3 见。", labels, "§1") == ["§9"]
    print("reference_lint selftest OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="跨章引用与定义承诺检查")
    ap.add_argument("--strict", action="store_true", help="WARN 也退 1")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    files = chapter_files()
    errors = warnings = 0
    for check in (check_migrations, check_definition_promises, check_bad_patterns, check_cross_refs, check_forward_budget, check_snapshot_position):
        e, w = check(files)
        errors += e
        warnings += w
    if errors or warnings:
        print(f"reference_lint: {errors} 错 / {warnings} 警")
    else:
        print("reference_lint: 0 问题")
    return 1 if errors or (warnings and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
