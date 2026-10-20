# -*- coding: utf-8 -*-
"""
judge_swap.py —— 结业项目三进阶题：LLM 评判员换序体验（位置偏差）

用 MiniMind2 本地扮演"LLM 评判员"，判断"客服回复有没有复述用户的订单号"。
同一对（用户，回复）各评两次：正序（用户在前）与换序（回复在前）。
若两次结论不一致，就是位置偏差在现场演示。0.1B 评判员很不靠谱，
这本身就是"评判员也要被评估"的实物证据。
"""
import json

from modelscope import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

path = snapshot_download("gongjy/minimind2")
tok = AutoTokenizer.from_pretrained(path)
model = AutoModelForCausalLM.from_pretrained(path)
model.eval()


def ask(prompt, max_new_tokens=8):
    ids = tok(prompt, return_tensors="pt").input_ids
    out = model.generate(ids, max_new_tokens=max_new_tokens, do_sample=False)
    return tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True).strip()


# 三对已知答案的样例（答案取自 eval_min.py 规则判定器的结论）
PAIRS = [
    {"name": "样例1（回复确实复述了订单号，正确答案：是）",
     "user": "订单号 #A1024 什么时候发货？",
     "reply": "您好，已收到您关于订单 #A1024 的问题，我们马上为您处理。"},
    {"name": "样例2（回复没有复述订单号，正确答案：否）",
     "user": "订单号 C7788，我要退货。",
     "reply": "您好，感谢您联系我们。我们非常抱歉给您带来了不便。请您提供订单号，我们将尽快处理退货事宜。"},
    {"name": "样例3（回复没有复述订单号，正确答案：否）",
     "user": "我的订单号是 B-2048，帮我查查物流。",
     "reply": "好的，我已经记录下来了。请问您需要我帮您查询物流信息吗？"},
]

TEMPLATE = (
    "<|im_start|>system\nYou are a helpful assistant<|im_end|>\n"
    "<|im_start|>user\n请判断：客服的回复里是否包含了用户的订单号？只回答一个字，是 或 否。\n"
    "{block_a}\n{block_b}<|im_end|>\n<|im_start|>assistant\n"
)

for p in PAIRS:
    ua = "用户消息：" + p["user"]
    rb = "客服回复：" + p["reply"]
    print("=" * 60)
    print(p["name"])
    for label, a, b in [("正序（用户在前）", ua, rb), ("换序（回复在前）", rb, ua)]:
        ans = ask(TEMPLATE.format(block_a=a, block_b=b))
        print(f"  {label} -> 评判员回答：{ans!r}")

print("=" * 60)
print("对照：规则判定器对三对样例的答案是 是／否／否（不随顺序变）。")
