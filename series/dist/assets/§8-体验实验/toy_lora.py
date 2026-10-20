# §8 toy LoRA：低秩真值 W* = B*·A*（d=64，真秩 4），r=1..16 最小二乘拟合
# 验证两条：① 拟合误差随 r 单调不增；② r 达到真秩 4 后出现"低秩饱和"——
# 对真值 W* 的误差不降（再加大 r 拟合到的只是噪声）。口径与对账记录 §8 4a 同源。
import numpy as np

rng = np.random.default_rng(8)             # 固定种子，结果可复现
d, R_TRUE, N = 64, 4, 256                  # 维度 / 真秩 / 线性观测条数

B_star = rng.normal(size=(d, R_TRUE))      # 高瘦：64×4
A_star = rng.normal(size=(R_TRUE, d))      # 矮胖：4×64
W_star = B_star @ A_star                   # 合成真值：64×64，秩恰好为 4
X = rng.normal(size=(N, d))                # 线性观测输入
Y = X @ W_star + 0.05 * rng.normal(size=(N, d))  # 观测含少量高斯噪声

# 第一步：最小二乘估计全矩阵  Ŵ = argmin‖Y − XW‖F（正规方程的数值稳态解）
W_hat_full = np.linalg.lstsq(X, Y, rcond=None)[0]

# 第二步：对每个 r 做 rank≤r 的最优拟合 = 对 Ŵ 截断 SVD（Eckart–Young 定理：
# 同秩近似里 Frobenius 误差最小者就是保留前 r 个奇异值）
U, s, Vt = np.linalg.svd(W_hat_full)
print(f'd={d}, 真秩={R_TRUE}, 观测={N} 条（含少量噪声）')
print(f'{"r":>3} {"‖Ŵ−BA‖F(拟合目标)":>20} {"‖W*−BA‖F(真值误差)":>20}')
print('-' * 45)
obj, true_err = [], []
for r in range(1, 17):
    BA = (U[:, :r] * s[:r]) @ Vt[:r]      # rank ≤ r 的最优低秩近似
    obj.append(np.linalg.norm(W_hat_full - BA, 'fro'))
    true_err.append(np.linalg.norm(W_star - BA, 'fro'))
    print(f'{r:>3} {obj[-1]:>20.4f} {true_err[-1]:>20.4f}')
print('-' * 45)

# 断言一：拟合目标随 r 单调不增（容差 1e-8，应对浮点抖动）
assert all(obj[i + 1] <= obj[i] + 1e-8 for i in range(15)), '拟合误差应随 r 单调不增'

# 断言二：低秩饱和——r=真秩 4 时取到最小真值误差；r>4 后误差不降反微升
#（拟合目标仍在下降，但拟合到的是噪声），与 r=1 欠拟合形成量级对比
best = true_err[3]                         # r=4 的真值误差
assert true_err[15] > best, 'r>真秩后应出现过拟合：真值误差回升'
assert best < 0.02 * obj[0], 'r=真秩时误差应降到 r=1 欠拟合的 2% 以内'

print(f'\n低秩饱和：r=4（=真秩）时真值误差最小 ≈{best:.3f}；r>4 后误差不降反微升'
      f'（拟合目标仍在降，但拟合到的是噪声）；r=1 欠拟合 {obj[0]:.3f}，'
      f'为 r=4 误差的 {obj[0] / best:.0f} 倍')
print('→ PASS：误差单调不增，且 r=4（=真秩）后饱和——r 决定修正丰富程度，'
      '过小不够、过大浪费（对账记录 §8 4a，旧版 L215/L258；QLoRA 论文见引用卡）')
