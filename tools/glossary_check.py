#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C4 术语一致性检测 v2:
1) 词卡释义 vs 各书"定义句"(句内含术语+定义词)
2) 同书内疑似二次定义(术语+定义词 的句数 > 1)
3) 覆盖缺口(高频术语未入卡)
"""
import re, json, pathlib
from collections import Counter
ROOT = pathlib.Path(__file__).resolve().parent.parent
BOOKS = ["1_ai_math/AI数学_从起步到前沿.md", "1a_diffusion/扩散_从噪声生成.md",
         "2_foundation/基座模型_从咿呀到行动.md", "3_use_ai/用好AI_从有用到好用.md",
         "4_ai_law/AI_law_从现象到规律.md"]
g = json.load(open(ROOT / "tools" / "glossary.json", encoding="utf-8"))["terms"]
DEF_WORDS = r"指|就是|称为|叫做|意思是|指的是|即|意味着|表示"
out = []
out.append("== 1) 词卡 vs 各书定义句（句内含术语+定义词；空=该书无定义句） ==")
for term, card in g:
    row = ["[%s] 卡:%s" % (term, card[:38])]
    for fn in BOOKS:
        txt = open(ROOT / fn, encoding="utf-8").read()
        cut = txt.find("# 附录：参考文献")
        prose = re.sub(r"\$[^$]*?\$", " ", txt[:cut] if cut != -1 else txt)
        sents = [s.strip() for s in re.split(r"[。！？]|\n", prose) if term in s and re.search(DEF_WORDS, s) and len(s) > 10]
        if sents:
            row.append("·" + sents[0][:58])
        else:
            row.append("·—")
    out.append(" | ".join(row))
out.append("")
out.append("== 2) 同书疑似二次定义(术语+定义词 的句数>1；可能需引用式瘦身) ==")
n2 = 0
for fn in BOOKS:
    txt = open(ROOT / fn, encoding="utf-8").read()
    cut = txt.find("# 附录：参考文献")
    prose = re.sub(r"\$[^$]*?\$", " ", txt[:cut] if cut != -1 else txt)
    sents = re.split(r"[。！？]|\n", prose)
    for term, _ in g:
        n = sum(1 for s in sents if term in s and re.search(DEF_WORDS, s))
        if n > 1:
            out.append("  %s [%s]: %d 句" % (fn.split("/")[0], term, n))
            n2 += 1
out.append("  小计: %d" % n2)
out.append("")
out.append("== 3) 覆盖缺口(跨书高频词未入卡, top 14) ==")
ALL = " ".join(open(ROOT / fn, encoding="utf-8").read() for fn in BOOKS)
words = re.findall(r"[A-Za-z][A-Za-z0-9+\-]*(?: [A-Za-z][A-Za-z0-9]+)*", ALL)
cnt = Counter(w for w in words if len(w) >= 5)
cards = set(t for t, _ in g)
cand = [(w, c) for w, c in cnt.most_common(120) if w not in cards and c >= 15][:14]
for w, c in cand:
    out.append("  %s x%d" % (w, c))
open(ROOT / "tools" / "glossary_report.txt", "w", encoding="utf-8").write("\n".join(out))
print("report -> tools/glossary_report.txt, lines:", len(out))
