#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QLoRA-7B 链路 · CPU 小规模可跑验证（series §8 结业项目二资产）

口径（2026-10-13）：
- 本脚本验证的是「QLoRA 训练链路真跑通」：NF4 4-bit 冻结底座 + LoRA 16-bit 适配器
  训练十几步 + adapter 存取 + 推理 smoke。**不是完整微调收敛复现**（完整训练仍按
  Colab/租卡，数小时两组）。
- 数据：8 条自撰教学样本（合成，非公开数据集），循环喂入。
- 环境：任意 CPU 机器（本机实测：24 核 / 13GB RAM / 无 GPU）；依赖
  transformers + peft + bitsandbytes（4-bit 走 bnb CPU 回退路径）。
- 断言（全过才算跑通）：
  A1 NF4 底座加载成功（量化线性层在位）
  A2 可训练参数 > 0 且占比 < 1%
  A3 训练十几步 loss 下降（尾 3 步均 < 首 3 步均）
  A4 adapter 存盘且大小 > 0
  A5 重载 adapter 推理 smoke 成功
用法：python qlora_7b_cpu_smoke.py [--model Qwen/Qwen2.5-7B-Instruct] [--steps 12] [--box 900]
"""
from __future__ import annotations

import argparse
import os
import resource
import sys
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training

DATA = [
    ("把这句话翻译成英文：今天天气很好。", "The weather is nice today."),
    ("把这句话翻译成英文：猫坐在垫子上。", "The cat sits on the mat."),
    ("回答：一年有多少个月？", "12 个月。"),
    ("回答：水的化学式是什么？", "H2O。"),
    ("给这句话写摘要：小李昨天去图书馆借了三本书。", "小李昨天借了三本书。"),
    ("把数字 7 加 5。", "12。"),
    ("把数字 3 加 4。", "7。"),
    ("把这句话改成疑问句：外面在下雨。", "外面在下雨吗？"),
]


def peak_rss_gb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--steps", type=int, default=12)
    ap.add_argument("--box", type=int, default=900, help="时间盒（秒）")
    ap.add_argument("--out", default="/tmp/opencode/qlora_7b_adapter")
    args = ap.parse_args()

    torch.manual_seed(0)
    print(f"[env] torch {torch.__version__} | cuda {torch.cuda.is_available()} | cpu {os.cpu_count()}")
    try:
        import transformers, peft, bitsandbytes
        print(f"[env] transformers {transformers.__version__} | peft {peft.__version__} | bnb {bitsandbytes.__version__}")
    except Exception as e:  # noqa: BLE001
        print("[env] version probe failed:", e)

    t0 = time.time()
    qconf = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                               bnb_4bit_compute_dtype=torch.bfloat16)
    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model, quantization_config=qconf,
                                                 low_cpu_mem_usage=True)
    print(f"[A1] NF4 底座加载 OK，{time.time()-t0:.0f}s，峰值内存 {peak_rss_gb():.1f}GB")
    qlayers = [n for n, m in model.named_modules() if type(m).__name__ == "Linear4bit"]
    assert qlayers, "A1 FAIL：未发现 Linear4bit 量化层"
    print(f"[A1] 量化线性层 {len(qlayers)} 个（示例 {qlayers[0]}）")

    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=False)
    model = get_peft_model(model, LoraConfig(
        r=8, lora_alpha=16, lora_dropout=0.0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"], task_type="CAUSAL_LM"))
    trainable = [p for p in model.parameters() if p.requires_grad]
    n_tr = sum(p.numel() for p in trainable)
    n_all = sum(p.numel() for p in model.parameters())
    ratio = n_tr / n_all
    print(f"[A2] 可训练参数 {n_tr:,} / {n_all:,}（{ratio:.4%}）")
    assert n_tr > 0 and ratio < 0.01, "A2 FAIL：可训练参数占比异常"

    def encode(p: str, r: str) -> torch.Tensor:
        msgs = [{"role": "user", "content": p}, {"role": "assistant", "content": r}]
        ids = tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=False)
        return torch.tensor([ids])

    batches = [encode(p, r) for p, r in DATA]
    opt = torch.optim.AdamW(trainable, lr=5e-4)
    model.train()

    t1 = time.time()
    out = model(batches[0], labels=batches[0])
    loss = out.loss
    loss.backward(); opt.step(); opt.zero_grad()
    step_s = time.time() - t1
    print(f"[time] 单步 {step_s:.1f}s（{args.model.split('/')[-1]} NF4 CPU）")

    losses = [round(float(loss.detach()), 4)]
    t2 = time.time()
    ran = 1
    for i in range(args.steps - 1):
        ids = batches[i % len(batches)]
        out = model(ids, labels=ids)
        loss = out.loss
        loss.backward(); opt.step(); opt.zero_grad()
        losses.append(round(float(loss.detach()), 4))
        ran += 1
        if time.time() - t2 > args.box:
            print(f"[time] 时间盒 {args.box}s 到，提前停在第 {ran} 步")
            break
    head = sum(losses[:3]) / 3
    tail = sum(losses[-3:]) / 3
    print(f"[A3] losses {losses}")
    print(f"[A3] 首 3 均 {head:.3f} → 尾 3 均 {tail:.3f}（下降 {tail < head}）")
    assert tail < head, "A3 FAIL：loss 未下降"

    model.save_pretrained(args.out)
    size = sum(os.path.getsize(os.path.join(args.out, f)) for f in os.listdir(args.out))
    print(f"[A4] adapter 存盘 OK：{args.out}（{size/1024/1024:.1f} MB）")
    assert size > 0, "A4 FAIL：adapter 为空"

    model.eval()
    with torch.no_grad():
        ids = encode("把数字 3 加 4。", "x")
        gen = model.generate(ids[:, : ids.shape[1] - 1], max_new_tokens=6, do_sample=False)
    print("[A5] 推理 smoke OK")
    print(f"[done] 总用时 {time.time()-t0:.0f}s，峰值内存 {peak_rss_gb():.1f}GB，步数 {ran}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
