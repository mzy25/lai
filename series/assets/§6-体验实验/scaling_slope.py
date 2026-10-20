# 微实验：对数坐标读 scaling 斜率（§6 动手配对）
# 设计一句话：同一个回归任务，用"前 n 个傅里叶特征对"当模型（参数量 N = 2n+1），
# 目标函数的振幅谱是 k^-2 → 能量谱 k^-4 → 拟合不到的谱尾部 ≈ ½·n^-3，
# 即 loss ∝ N^-3（构造指数 α = 3 已知）。先在普通坐标直看一堆"没规律"的数，
# 再换对数坐标：幂律变成直线，线性回归读出斜率，最后和构造指数对账。
import numpy as np

rng = np.random.default_rng(0)            # 固定种子：任何人重跑，数字逐字相同

K = 100                                   # 目标含 100 个频率成分（相对 n≤12 等效"无穷谱"）
ks = np.arange(1, K + 1, dtype=float)     # 频率编号 1..100
AMP = ks ** -2.0                          # 振幅谱 ∝ k^-2（scaling 的"构造旋钮"）
PHI = rng.uniform(0, 2 * np.pi, K)        # 每个频率的随机相位（任务本体）

def target(x):
    """目标函数：100 个正弦叠加（向量化：一行矩阵乘法）"""
    return (np.sin(np.pi * np.outer(x, ks) + PHI) * AMP).sum(axis=1)

x_tr = np.linspace(-1, 1, 2000)           # 训练集：2000 个等距点
y_tr = target(x_tr)
x_te = np.linspace(-1, 1, 20001)          # 测试集：密网格，近似"总体误差"
y_te = target(x_te)

# ---------- 主循环：模型规模 n = 1..12 个频率对（N = 2n+1 个参数） ----------
print('线性坐标直看（参数越多 loss 越小，但"规律"藏在数字里看不清）')
print(f'{"频率对 n":<10}{"参数量 N":>10}{"测试 loss":>14}{"理论尾部":>14}')
Ns, losses = [], []
for n in range(1, 13):
    kn = np.arange(1, n + 1, dtype=float)
    def feats(x):   # 特征矩阵：sin/cos 各 n 列，再加一列常数 1 当偏置
        return np.column_stack([np.sin(np.pi * np.outer(x, kn)),
                                np.cos(np.pi * np.outer(x, kn)), np.ones_like(x)])
    beta, *_ = np.linalg.lstsq(feats(x_tr), y_tr, rcond=None)  # 最小二乘闭式解
    mse = ((feats(x_te) @ beta - y_te) ** 2).mean()            # 总体均方误差
    tail = 0.5 * sum(k ** -4 for k in range(n + 1, 60))        # 解析尾部 ½·Σ_{k>n} k^-4
    Ns.append(2 * n + 1); losses.append(mse)
    print(f'{n:<10}{2 * n + 1:>10}{mse:>14.6f}{tail:>14.6f}')

# ---------- 对数坐标：loss ∝ N^-α  ⇔  log(loss) = 常数 − α·log N 是一条直线 ----------
slope, _ = np.polyfit(np.log(Ns), np.log(losses), 1)   # log-log 线性回归
alpha = -slope                                         # 直线斜率的相反数就是幂律指数
pred = np.polyval([slope, _], np.log(Ns))
r2 = 1 - np.sum((np.log(losses) - pred) ** 2) / np.sum((np.log(losses) - np.log(losses).mean()) ** 2)
print(f'\n对数坐标拟合（12 个点的 log-log 线性回归，R² = {r2:.6f}）')
print(f'直线斜率 = {slope:.4f}   →   幂律指数 α = {alpha:.4f}   （loss ∝ N^-α）')

# ---------- 与构造指数对账：振幅 k^-2 → 能量 k^-4 → 尾部 ∝ n^-3 ----------
err = abs(alpha - 3) / 3
print(f'\n对账：构造指数 = 3.0000，拟合 α = {alpha:.4f}，相对误差 = {err * 100:.2f}%')
print(f'判定: 相对误差 < 5% → {"PASS" if err < 0.05 else "FAIL"}')
