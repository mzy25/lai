#!/usr/bin/env python3
"""§13 体验实验·轨道一：叠加与平均重叠（真跑）。

纯 NumPy 复刻 Toy Models of Superposition（Elhage 等 2022）风格的最小叠加演示：
  1. 生成 m=20 个随机单位方向，分别放进 d=8/20/40 维空间；
  2. 读数"平均重叠"＝任意一对不同特征方向夹角余弦的绝对值，取全部 C(20,2) 对；
  3. 与教科书渐近式 sqrt(2/(pi*d)) 对照（旧版《AI规律》ch6 表值 0.29/0.18/0.13）；
  4. "两个特征是否共居一个方向"的判定演示：每个特征方向用两份带噪样本
     各估一次，同特征两次估计的 |cos|（应接近 1）与异特征之间的 |cos|
     （随 d 变小而升高）摆在一起——重叠度升高时，"分得清"退化成"分不清"。

设定与旧版一致：m=20、d ∈ {8,20,40}、重叠＝|cos| 的期望。固定种子，秒级。
运行：python overlap.py（cwd = 本目录）。stdout 逐字留档 run_log.txt。
"""
import numpy as np

SEED = 13
R_SEEDS = 200               # 主表读数：R 个种子平均（消有限样本涨落，仍秒级）
rng = np.random.default_rng(SEED)
M = 20                      # 特征数（旧版口径 m=20）
DIMS = [8, 20, 40]          # 空间维度 d
NOISE = 0.3                 # 方向估计的观测噪声（判定演示用）
N_HALF = 200                # 每半份样本数（判定演示用）


def random_unit_directions(m, d, rng):
    V = rng.standard_normal((m, d))
    return V / np.linalg.norm(V, axis=1, keepdims=True)


def mean_abs_cos(V):
    """全部特征对 |cos| 的均值（总体口径，非抽样）。"""
    G = V @ V.T
    iu = np.triu_indices(V.shape[0], k=1)
    return float(np.mean(np.abs(G[iu])))


def mean_abs_cos_seeds(m, d, r_seeds, base_seed):
    """R 个种子各抽一份 m×d 方向集，读数取平均（消单种子涨落）。"""
    vals = []
    for s in range(r_seeds):
        r = np.random.default_rng(base_seed + s)
        vals.append(mean_abs_cos(random_unit_directions(m, d, r)))
    return float(np.mean(vals)), float(np.std(vals))


def estimate_direction(true_dir, n, rng, noise=NOISE):
    """用 n 份带噪观测估一个方向：观测 = 真方向 + 噪声，取平均后归一。"""
    obs = true_dir + noise * rng.standard_normal((n, true_dir.shape[0]))
    est = obs.mean(axis=0)
    return est / np.linalg.norm(est)


print("=" * 64)
print(f"轨道一：叠加与平均重叠  seed={SEED}×{R_SEEDS}  m={M}  d={DIMS}")
print("=" * 64)

rows = []
for d in DIMS:
    measured, std = mean_abs_cos_seeds(M, d, R_SEEDS, SEED)
    asym = np.sqrt(2.0 / (np.pi * d))
    rows.append((d, measured, asym))
    print(f"d={d:>2}  实测平均重叠({R_SEEDS}种子) = {measured:.3f} ± {std:.3f}   "
          f"渐近式 sqrt(2/(pi*d)) = {asym:.3f}   "
          f"差 {measured - asym:+.3f}")

print()
print("对照旧版《AI规律》ch6 表值：d=8→0.29，d=20→0.18，d=40→0.13")
src = {8: 0.29, 20: 0.18, 40: 0.13}
ok = all(abs(m - src[d]) <= 0.02 for d, m, _ in rows)
print(f"逐格断言（|实测-旧版| <= 0.02）：{'PASS' if ok else 'FAIL'}")

print()
print("判定演示：两个特征'是否共居一个方向'，靠 |cos| 读数下结论")
print(f"（每个方向用两份 {N_HALF} 份带噪样本各估一次，噪声 sigma={NOISE}）")
print(f"{'d':>4} {'同特征两次估计|cos|':>22} {'异特征平均|cos|':>18} "
      f"{'裕度(同-异)':>14}")
for d in DIMS:
    V = random_unit_directions(M, d, rng)
    ests = [estimate_direction(V[i], N_HALF, rng) for i in range(M)]
    same = [abs(float(ests[i] @ V[i])) for i in range(M)]
    E = np.array(ests)
    G = np.abs(E @ V.T)
    iu = np.triu_indices(M, k=1)
    diff = float(np.mean(G[iu]))
    print(f"{d:>4} {np.mean(same):>22.3f} {diff:>18.3f} "
          f"{np.mean(same) - diff:>14.3f}")

print()
print("读法：d=8 时异特征重叠逼近 0.3，同特征的信号只比混淆高出一截；")
print("d=40 时两数拉开——高维里'共居'才判得稳。m>d 时重叠不可避免。")

# 产出图：复刻图13（实测 vs 渐近式）
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    for f in font_manager.fontManager.ttflist:
        if "CJK" in f.name or "Hei" in f.name or "Song" in f.name:
            plt.rcParams["font.family"] = f.name
            break
    plt.rcParams["axes.unicode_minus"] = False

    ds = np.array([4, 6, 8, 12, 16, 20, 28, 40, 56, 80])
    rng2 = np.random.default_rng(SEED + 1)
    meas = [mean_abs_cos(random_unit_directions(M, int(dd), rng2)) for dd in ds]
    asym_curve = np.sqrt(2.0 / (np.pi * ds))

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(ds, asym_curve, "--", color="#888888",
            label=r"渐近式 $\sqrt{2/(\pi d)}$")
    ax.plot(ds, meas, "o-", color="#1f77b4", label="实测平均重叠（m=20）")
    for d, m, _ in rows:
        ax.annotate(f"{m:.2f}", (d, m), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=9)
    ax.set_xlabel("空间维度 d")
    ax.set_ylabel("平均重叠  E|cos|")
    ax.set_title("图13 复刻：叠加几何——特征方向平均重叠随维度下降")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig("fig13_overlap.png", dpi=150)
    print()
    print("已产出 fig13_overlap.png（图13 复刻）")
except Exception as e:  # 无绘图环境时表格仍完整
    print(f"\n[绘图跳过：{e}]")
