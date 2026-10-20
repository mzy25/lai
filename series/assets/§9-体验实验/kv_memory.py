# KV 显存账估算：四档复算脚本（MHA / GQA / MQA / 7B 全账）
# 口径照对账记录 4a：MB/GB 十进制读（67 MB = 64 MiB）；D 档先舍 67.1→2.1 再 ×8 → 16.8。
N_CTX = 4096          # 上下文长度 n
BATCH = 8             # 对拍 batch

def kv_chain(layers, n_kv, d_k, nbytes, n_ctx=N_CTX):
    """每 token 字节 = 2×n_kv×d_k×精度字节；逐级 ×n、×层数。返回字节三元组。"""
    per_token = 2 * n_kv * d_k * nbytes          # 2 = K、V 两份
    per_layer = per_token * n_ctx                # 一层装下整个上下文
    full_model = per_layer * layers
    return per_token, per_layer, full_model

rows = [
    ('A. MHA (g=8)', 80, 8, 128),
    ('B. GQA (g=2)', 80, 2, 128),
    ('C. MQA (g=1)', 80, 1, 128),
    ('D. 7B 账    ', 32, 1, 4096),   # n_kv×d_k=4096（模型维度，MHA）
]
print(f'{"档位":<12}{"层数":>4}{"头数":>4}{"d_k":>6}'
      f'{"每token(B)":>12}{"每层(MB)":>10}{"全模型(MB)":>12}')
print('-' * 64)
for name, L, n_kv, d_k in rows:
    pt, pl, fm = kv_chain(L, n_kv, d_k, 2)
    print(f'{name:<12}{L:>4}{n_kv:>4}{d_k:>6}{pt:>12}{pl/1e6:>10.1f}{fm/1e6:>12.0f}')
print('-' * 64)

# ---- 逐格断言（容差 1%，照笔记 4a 口径）----
_, a_pl, a_fm = kv_chain(80, 8, 128, 2)
_, b_pl, b_fm = kv_chain(80, 2, 128, 2)
_, c_pl, c_fm = kv_chain(80, 1, 128, 2)
d_pt, d_pl, d_fm = kv_chain(32, 1, 4096, 2)

assert abs(a_pl / 1e6 - 16.8) / 16.8 < 0.01          # A 每层 16.8 MB
assert abs(b_pl / 1e6 - 4.2) / 4.2 < 0.01           # B 每层 4.2 MB（=25%）
assert abs(c_pl / 1e6 - 2.1) / 2.1 < 0.01           # C 每层 2.1 MB
assert abs(a_fm / 1e6 - 1344) / 1344 < 0.01         # A×80 ≈ 1344 MB（"约 1.3 GB"）
assert abs(b_fm / 1e6 - 336) < 1 and abs(c_fm / 1e6 - 168) < 1  # 手算链 4.2×80=336、2.1×80=168（整数积）
assert d_pt == 16384                                  # D 每 token 16,384 B = 16 KB
assert abs(d_pl / 1e6 - 67.1) / 67.1 < 0.01           # D 每层 67.1 MB
d_fm_mb = d_fm / 1e6                               # 精算 2147.48 MB
assert abs(d_fm_mb - 2147.5) < 0.1                  # 笔记口径 2,147.5 MB ≈ 2.1 GB

# 舍入口径：先舍 2.1 GB 再 ×8 → 16.8（精算 2.147×8 = 17.2，两笔账勿混用）
d_batch = round(d_fm_mb / 1000, 1) * BATCH
assert abs(d_batch - 16.8) < 1e-9, d_batch
param_gb = 7e9 * 2 / 1e9                              # 参数账 7B×2B = 14 GB
assert d_batch > param_gb                             # 16.8 GB > 14 GB：KV 账反超参数账
assert abs(a_pl / b_pl - 4) < 1e-9 and abs(b_pl / c_pl - 2) < 1e-9  # 三档 8:2:1

print(f'\n对账: A/B/C 每层 16.8/4.2/2.1 MB，×80 = 1344/336/168 MB（约1.3GB/336/168）→ PASS')
print(f'对账: D 档 16,384 B → 67.1 MB → ×32 ≈ 2.1 GB → batch=8 先舍口径 ≈ 16.8 GB'
      f'（精算 17.2，照旧版口径 4c-1）→ PASS')
print(f'对账: 16.8 GB > 参数账 {param_gb:.0f} GB（7B×2B），KV 账反超 → PASS')
print(f'对账: GQA 三档每层 16.8:4.2:2.1 = 8:2:1（g=2 降到 25%）→ PASS')

# ---- 变式两行 ----
print(f'\n变式: 8K→128K，上下文 ×{128 // 8}（16×，显存随上下文线性涨）')
print(f'变式: KV 量化 INT4，D 档 16.8 GB ÷ 4 = {d_batch / 4:.1f} GB')
