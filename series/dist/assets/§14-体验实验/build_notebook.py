# -*- coding: utf-8 -*-
"""生成 预置笔记本.ipynb（与 eval_min.py 同一份代码的笔记本入口）。"""
import json


def md(s):
    return {"cell_type": "markdown", "metadata": {}, "source": s.splitlines(keepends=True)}


def code(s):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": s.splitlines(keepends=True)}


nb = {
    "cells": [
        md("# 结业项目三预置笔记本：写最小 eval\n\n"
           "题面：你的 AI 客服总是忘了附订单号。写个最小 eval，量化它到底多经常忘。\n\n"
           "最小 eval 五件：任务定义一句话｜条目级数据集（失败用例先行）｜判定器（优先规则）｜"
           "条目级报表｜基线与门槛。本笔记本与同目录 eval_min.py 是同一份代码的两个入口，"
           "任何一处改动两边同步。"),
        md("## 1. 任务定义与数据集\n\n"
           "任务定义一句话：客服回复必须包含用户消息里的订单号；用户没给订单号则不强制。\n\n"
           "24 条用例分三区：失败用例区 F01–F10（先于任何修复写成）、常规用例区 P01–P10、"
           "边界用例区 E01–E04。门槛：24 条至少 22 条（≈91.7%）算修好。"),
        code("from eval_min import CASES, THRESHOLD, extract_order_no\n"
             "print(f'用例总数 {len(CASES)}，门槛 {THRESHOLD}/{len(CASES)}')\n"
             "from collections import Counter\n"
             "print(Counter(c['zone'] for c in CASES))"),
        md("## 2. 判定器自检\n\n"
           "规则判定：抽出订单号，检查回复是否包含它。判定器自己也要先验货，这步叫判定器自检。"),
        code("for c in CASES:\n    print(c['id'], '->', extract_order_no(c['user']))"),
        md("## 3. 基线：规则小模型 v1（修复前）"),
        code("from eval_min import rule_bot_v1, run_eval\n"
             "rows_v1 = run_eval('规则小模型 v1（修复前）', rule_bot_v1, CASES)"),
        md("## 4. eval-driven：失败用例先于改动存在，改动由失败用例驱动\n\n"
           "看 v1 的分区报表：失败用例区全挂，就是改动的清单。修完用同一批用例裁定。"),
        code("from eval_min import rule_bot_v2, run_eval\n"
             "rows_v2 = run_eval('规则小模型 v2（修复后）', rule_bot_v2, CASES)"),
        md("## 5. 被评对象换成真实模型：MiniMind2（本机 CPU，可选）\n\n"
           "不提醒它附订单号，贪心解码可复现。没有 modelscope 环境时本格会自动跳过。"),
        code("try:\n"
             "    from eval_min import load_minimind, minimind_reply, run_eval\n"
             "    tok, model = load_minimind()\n"
             "    rows_llm = run_eval('MiniMind2（未提醒附订单号）',\n"
             "                        lambda u: minimind_reply(tok, model, u), CASES)\n"
             "except ModuleNotFoundError as e:\n"
             "    print('跳过：本环境缺依赖', e)"),
        md("## 6. 进阶：把判定器换成 LLM 评判员，亲身体会三偏差\n\n"
           "judge_swap.py 用 MiniMind2 扮演评判员做换序测试。2026-10-09 本机实测：0.1B 评判员不守指令、"
           "两对答错、结论随顺序漂移，整体不合格。这本身就是评判员也要被评估的证据。"),
        code("import subprocess, sys\n"
             "r = subprocess.run([sys.executable, 'judge_swap.py'],\n"
             "                   capture_output=True, text=True, encoding='utf-8')\n"
             "print(r.stdout[-1500:])"),
    ],
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12.14"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

with open('预置笔记本.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print('written')
