# 双下降体验实验：沿容量轴扫掠，四段分阶段读数（§10）
# 设定照《AI规律》§1.5。先猜再看：维度扫到 100（=样本数）时，测试误差落在四段的哪一段？
import numpy as np
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC'] + plt.rcParams['font.sans-serif']
plt.rcParams['axes.unicode_minus'] = False
PS = [10, 20, 40, 60, 80, 90, 95, 100, 105, 110, 120, 150, 200, 400, 800]  # 容量轴 15 档

def sweep(noise):  # 造数（信号只在前 3 维）→ 岭回归闭式解 → 逐档读测试误差
    r = np.random.default_rng(0)  # 固定种子：谁跑都是同一条曲线
    X, Xt = r.normal(0, 1, (100, 800)), r.normal(0, 1, (5000, 800))
    w = np.zeros(800); w[:3] = 1.0
    y, yt = X @ w + noise * r.normal(size=100), Xt @ w + noise * r.normal(size=5000)
    out = []
    for p in PS:
        A = X[:, :p]
        b = np.linalg.solve(A.T @ A + 1e-8 * np.eye(p), A.T @ y)  # λ=10⁻⁸ 岭回归闭式解
        out += [float(np.mean((Xt[:, :p] @ b - yt) ** 2))]
    return out

mse, ctl = sweep(0.3), sweep(0.01)  # 主实验噪声标准差 0.3；对照 0.01（方差 10⁻⁴）
for p, e in zip(PS, mse):
    print(f"p={p:<4} 测试 MSE = {e:.3f}")
print(f"四段读数  降—平 p=10→40：{mse[0]:.3f}→{mse[2]:.3f}")
print(f"          升 p=60→95：{mse[3]:.3f}→{mse[6]:.3f}；尖峰 p=100：{mse[7]:.3f}（≈p=10 的 {mse[7]/mse[0]:.0f} 倍）")
print(f"          再降 p=105→110：{mse[8]:.3f}→{mse[9]:.3f}，随后缓升至 p=800 的 {mse[-1]:.3f}")
print(f"对照  低噪声 p=100：{ctl[7]:.3f}，p=800：{ctl[-1]:.3f}，峰值 {max(ctl):.3f}（尖峰几乎消失）")

plt.figure(figsize=(8, 5))
plt.plot(PS, mse, 'o-', label='噪声 0.3（主实验）'); plt.plot(PS, ctl, 's--', label='噪声 0.01（对照）')
plt.axvline(100, color='gray', ls=':', lw=1); plt.xscale('log')
plt.xlabel('特征维度（容量轴，对数刻度）'); plt.ylabel('测试 MSE')
plt.legend(); plt.grid(alpha=0.3)
plt.title('双下降：先升、尖峰、再降（岭回归闭式解，100 个样本，seed 0）')
plt.tight_layout(); plt.savefig('double_descent.png', dpi=150); print('图 → double_descent.png')
