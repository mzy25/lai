# -*- coding: utf-8 -*-
"""
eval_min.py —— 结业项目三参考实现：写最小 eval（AI 客服复述订单号）

最小 eval 五件（照 §14 对账记录 §5）：
  1. 任务定义一句话：客服回复必须包含用户消息里的订单号；
  2. 条目级数据集：24 条用例，失败用例区（FAIL 区）先于任何修复写成；
  3. 判定器：规则判定（正则抽取订单号 → 检查回复是否包含）；
  4. 指标：逐项对错 + 分区报表，不只报一个总分；
  5. 基线与门槛：先测"修复前"，门槛 = 24 条至少 22 条通过（≈91.7%）算修好。

被评对象：
  A. rule_bot_v1 —— 规则小模型"修复前"（短问句复述、长问句遗漏）；
  B. rule_bot_v2 —— 同一规则小模型"修复后"（任何情况都复述）；
  C. MiniMind2（可选，本机 CPU）—— 真实 0.1B 指令模型，不提醒它附订单号。

用法：
  python eval_min.py            # 跑 A、B（规则小模型，秒出）
  python eval_min.py --llm      # 追加跑 C（MiniMind2，CPU 约一分钟）
"""

import argparse
import json
import re
import sys
import time

# ---------------------------------------------------------------- 数据集
# 分区：FAIL 区（失败用例，先于任何修复写成）→ PASS 区（常规用例）→ EDGE 区（边界用例）
CASES = [
    # ---- FAIL 区：这 10 条是"失败用例先行"的实物——写它们的时候，被评系统还不存在
    {"id": "F01", "zone": "失败用例", "user": "你好，我上周下的单一直没到，订单号 #A1024，能帮我问问物流吗？物流单号我这边查不到，麻烦尽快。"},
    {"id": "F02", "zone": "失败用例", "user": "订单号 B-2048。我要改地址，原地址写错了，新地址是杭州市西湖区文三路 100 号，收件人电话不变，请帮我更新，谢谢！"},
    {"id": "F03", "zone": "失败用例", "user": "亲，我买了一件外套想退货，订单号 C7788，衣服尺码偏小穿不了，吊牌还在，包装完整，麻烦帮我处理一下退款哦。"},
    {"id": "F04", "zone": "失败用例", "user": "你好，订单号 #D3092，我收到的杯子碎了一个角，外包装是完好的，应该是运输途中磕的，麻烦补发一个或者给我退款，谢谢。"},
    {"id": "F05", "zone": "失败用例", "user": "我的订单号 E-5510，买了三本书只到了两本，缺的那本是《时间简史》，快递面单上写的也是两本，请帮我核实一下仓库发货记录。"},
    {"id": "F06", "zone": "失败用例", "user": "订单号：F6600。请问我的发票什么时候能开？公司报销要用，抬头是'杭州某某科技有限公司'，税号 91330106MA27xxxx33，谢谢！"},
    {"id": "F07", "zone": "失败用例", "user": "你好呀，我想问一下订单号 G-8817 的包裹到哪儿了？显示签收但我没收到，快递员电话也打不通，物业那里也找过了，麻烦帮我查查。"},
    {"id": "F08", "zone": "失败用例", "user": "订单号 H9902，我要投诉！买的耳机左耳没有声音，换了一次还是不行，这已经第二次了，请给我一个说法，要么退款要么换全新的。"},
    {"id": "F09", "zone": "失败用例", "user": "亲，我订单号是 #I1230，买的奶粉一罐瘪了，虽然是外包装瘪但没破，里面的奶粉应该没问题，不过我还是想换一罐，可以吗？"},
    {"id": "F10", "zone": "失败用例", "user": "你好，麻烦帮我取消订单号 J-4476 的订单，才下单五分钟，还没发货，取消原因选'拍错了'，钱原路退回就行，麻烦了。"},
    # ---- PASS 区：常规用例
    {"id": "P01", "zone": "常规用例", "user": "订单号 #A1024 什么时候发货？"},
    {"id": "P02", "zone": "常规用例", "user": "我的订单号是 B-2048，帮我查查物流。"},
    {"id": "P03", "zone": "常规用例", "user": "订单号 C7788，我要退货。"},
    {"id": "P04", "zone": "常规用例", "user": "你好，订单号 #D3092 想改收货地址。"},
    {"id": "P05", "zone": "常规用例", "user": "订单号 E-5510 的发票还没收到。"},
    {"id": "P06", "zone": "常规用例", "user": "亲，订单号 F6600 帮我取消一下。"},
    {"id": "P07", "zone": "常规用例", "user": "我的订单号 G-8817 显示签收了但我没收到。"},
    {"id": "P08", "zone": "常规用例", "user": "订单号 H9902 的耳机有质量问题。"},
    {"id": "P09", "zone": "常规用例", "user": "订单号 #I1230 的奶粉包装瘪了，能换吗？"},
    {"id": "P10", "zone": "常规用例", "user": "你好，订单号 J-4476 退款到账了吗？"},
    # ---- EDGE 区：边界用例（多条数字干扰、格式变体、无订单号）
    {"id": "E01", "zone": "边界用例", "user": "我的订单号是 #K5521，手机号 13812345678，金额 299 元，帮我查一下 3 月 15 日那笔什么时候发货？"},
    {"id": "E02", "zone": "边界用例", "user": "订单号 L8820；另外我还有个问题，赠品能一起退吗？还有积分什么时候到账？"},
    {"id": "E03", "zone": "边界用例", "user": "你好，我想问一下优惠券怎么用？没有订单，先问清楚再下单。"},
    {"id": "E04", "zone": "边界用例", "user": "订单号 m-3355（注意是小写 m），帮我把收货时间改到周末。"},
]

THRESHOLD = 22  # 24 条中至少 22 条通过（≈91.7%）算修好

# ---------------------------------------------------------------- 判定器（规则）
ORDER_RE = re.compile(r"订单号.{0,6}?([-#]?[A-Za-z]{1,2}-?\d{4,6}|\d{4,6})")


def extract_order_no(user_msg):
    """从用户消息里抽出订单号（含 #、字母、连字符前缀，整体参与判定）；没给则返回 None。"""
    m = ORDER_RE.search(user_msg)
    return m.group(1) if m else None


def judge(item, reply):
    """规则判定：用户给了订单号 → 回复必须包含它；没给 → 一律判通过（不强制编造）。"""
    order_no = extract_order_no(item["user"])
    if order_no is None:
        return True, "用户未提供订单号，不强制"
    ok = order_no in reply
    return ok, f"订单号 {order_no} " + ("已复述" if ok else "未复述")


# ---------------------------------------------------------------- 被评对象 A/B：规则小模型
def rule_bot_v1(user_msg):
    """'修复前'的客服：短问句会复述订单号，长问句（>20 字）就忘了。"""
    order_no = extract_order_no(user_msg)
    if order_no is None:
        return "您好，优惠券可以在结算页直接选择使用，如有其他问题随时联系我。"
    if len(user_msg) <= 20:
        return f"您好，已收到您关于订单 {order_no} 的问题，我们马上为您处理。"
    return "您好，您的问题我们已经记录，会尽快为您核实处理，请保持电话畅通。"


def rule_bot_v2(user_msg):
    """'修复后'的客服：任何情况都先复述订单号再答复。"""
    order_no = extract_order_no(user_msg)
    if order_no is None:
        return "您好，优惠券可以在结算页直接选择使用，如有其他问题随时联系我。"
    return f"您好，已收到您关于订单 {order_no} 的问题，我们马上为您处理，请保持电话畅通。"


# ---------------------------------------------------------------- 被评对象 C：MiniMind2（可选）
def load_minimind():
    from modelscope import snapshot_download
    from transformers import AutoModelForCausalLM, AutoTokenizer

    path = snapshot_download("gongjy/minimind2")
    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(path)
    model.eval()
    return tok, model


def minimind_reply(tok, model, user_msg, max_new_tokens=48):
    prompt = (
        "<|im_start|>system\nYou are a helpful assistant<|im_end|>\n"
        f"<|im_start|>user\n你是电商客服，请简洁专业地回复：{user_msg}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    ids = tok(prompt, return_tensors="pt").input_ids
    out = model.generate(ids, max_new_tokens=max_new_tokens, do_sample=False)
    return tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True).strip()


# ---------------------------------------------------------------- 运行与报表
def run_eval(name, respond, cases):
    rows = []
    t0 = time.time()
    for c in cases:
        reply = respond(c["user"])
        ok, note = judge(c, reply)
        rows.append({"id": c["id"], "zone": c["zone"], "pass": ok, "note": note,
                     "user": c["user"], "reply": reply})
    dt = time.time() - t0

    print(f"\n===== {name} =====")
    print(f"耗时 {dt:.1f} s")
    for r in rows:
        mark = "PASS" if r["pass"] else "FAIL"
        print(f"{r['id']} [{r['zone']}] {mark}  {r['note']}")
        print(f"    用户: {r['user']}")
        print(f"    回复: {r['reply']}")

    by_zone = {}
    for r in rows:
        z = by_zone.setdefault(r["zone"], [0, 0])
        z[1] += 1
        z[0] += 1 if r["pass"] else 0
    print("分区统计:", {z: f"{v[0]}/{v[1]}" for z, v in by_zone.items()})
    n_pass = sum(1 for r in rows if r["pass"])
    total = len(rows)
    print(f"总计: {n_pass}/{total} = {n_pass/total:.1%}  门槛 {THRESHOLD}/{len(CASES)} "
          f"→ {'修好' if n_pass >= THRESHOLD else '未修好'}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="追加用 MiniMind2 真跑（CPU）")
    args = ap.parse_args()

    # 判定器自检：判定规则先对自己的数据集过一遍
    print("判定器自检（抽取订单号）：")
    for c in CASES:
        print(f"  {c['id']} -> {extract_order_no(c['user'])}")

    run_eval("被评对象 A：规则小模型 v1（修复前）", rule_bot_v1, CASES)
    run_eval("被评对象 B：规则小模型 v2（修复后）", rule_bot_v2, CASES)

    if args.llm:
        tok, model = load_minimind()
        rows = run_eval("被评对象 C：MiniMind2（真实 0.1B 模型，未提醒附订单号）",
                        lambda u: minimind_reply(tok, model, u), CASES)
        # 进阶题素材：挑出 LLM 答错/答对的代表条目，供"换序评判"体验用
        with open("llm_judge_pairs.json", "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
        print("\nLLM 逐条结果已存 llm_judge_pairs.json（进阶题：换序评判用）")


if __name__ == "__main__":
    sys.exit(main())
