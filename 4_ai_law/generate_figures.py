"""《AI规律：从现象到预见》配图生成脚本（Phase 3）

全书 16 张图。风格与四篇一致：轻填充、粗边框、低饱和度、高清晰度、CJK 字体。
每张图的数据要么来自一次性真实模拟（脚本内重放）、要么来自可复算的演示轨迹文件
（如 demo_edge_of_stability_trace.tsv，由同目录 demo_edge_of_stability.py 生成），
要么内嵌正文表格（这些表格本身就是各章模拟的真实输出，脚本注明了来源）。

用法：  python3 generate_figures.py
输出：  figures/fig_chN_*.png
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))
import fig_common  # noqa: E402
from fig_common import setup_rc  # noqa: E402


def save(fig, name):
    """保存并返回路径——run_all() 靠返回值判断这张图是否真的落盘，必须 return。"""
    return fig_common.save_fig(fig, name, OUTPUT_DIR, dpi=200, facecolor='white')


OUTPUT_DIR = Path(__file__).resolve().parent / "figures"

# 全蓝系 + 两个低饱和高亮
BLUE = "#2F6FB3"
BLUE_L = "#8FB8DE"
BLUE_LL = "#C7DBEF"
ORANGE = "#E8A33D"
RED = "#C07B6E"

pALETTE = [BLUE, ORANGE, RED, BLUE_L, "#7B9E6B"]


def fig_ch1_bias_variance():
    """图1 偏差-方差 U 形——独立模拟：n=120、真函数 u³-0.6u、σ=0.5、400 次（非多项式拟合表数据）"""
    rng = np.random.default_rng(0)
    n = 120
    x = rng.uniform(-1.5, 1.5, n)
    noise_std = 0.5
    f = lambda u: u ** 3 - 0.6 * u  # noqa: E731 真实函数（三次）
    degs = range(1, 11)
    n_trials, n_te = 400, 5000
    xt = np.linspace(-1.6, 1.6, n_te)
    ft = f(xt)
    bias2, var, tot = [], [], []
    for d in degs:
        preds = []
        for _ in range(n_trials):
            y = f(x) + noise_std * rng.normal(size=n)
            c = np.polyfit(x, y, d)
            p = np.polyval(c, xt)
            preds.append(p)
        P = np.array(preds)
        mean_p = P.mean(axis=0)
        bias2.append(np.mean((mean_p - ft) ** 2))
        var.append(np.mean(((P - mean_p) ** 2).mean(axis=0)))
        tot.append(np.mean((P - ft) ** 2) + noise_std ** 2)  # +σ²：对含噪 y 的测试 MSE
    fig, ax = plt.subplots(figsize=(7, 4.6))
    ax.plot(list(degs), tot, "-", color=ORANGE, lw=2.6, label="总误差 (total)")
    ax.plot(list(degs), bias2, "--", color=BLUE, lw=2, label="偏差² (bias$^2$)")
    ax.plot(list(degs), var, "-.", color=BLUE, lw=2, label="方差 (variance)")
    ax.axhline(noise_std ** 2, color="gray", ls=":", lw=1.4, label="不可约噪声 $\\sigma^2$")
    ax.axvline(3, color=RED, ls="--", lw=1.6)
    ax.annotate("谷底≈次数 3（真实函数为三次）", xy=(3, tot[2]), xytext=(4.4, 0.28),
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.2), fontsize=9, color=RED)
    ax.set_xlabel("多项式次数（容量）"); ax.set_ylabel("测试 MSE")
    ax.set_ylim(0, max(tot) * 1.05); ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)
    ax.set_title("偏差-方差 U 形：容量太少欠拟合、太多过拟合", fontsize=12)
    return save(fig, "fig_ch1_bias_variance.png")


def fig_ch1_double_descent():
    """图2 双下降（插值阈值尖峰 + 第二次下降）—— 直接读双下降复算轨迹。

    轨迹由 demo_double_descent.py 生成（n=100、d=800、最小范数最小二乘、噪声标准差 0.3）。
    """
    trace = np.loadtxt(Path(__file__).resolve().parent / "demo_double_descent_trace.tsv",
                       delimiter="\t", skiprows=1)
    ps, tr, te = trace[:, 0], np.maximum(trace[:, 1], 1e-6), trace[:, 2]
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.plot(ps, te, "-o", color=ORANGE, ms=5, lw=2.2, label="测试 MSE")
    ax.plot(ps, tr, "--s", color=BLUE, ms=4, lw=1.6, label="训练 MSE")
    ax.axvline(100, color=RED, ls=":", lw=1.6)
    ax.annotate("插值阈值 $p \\approx n=100$", xy=(100, te.max() * 0.55), xytext=(6, te.max() * 0.55),
                fontsize=9, color=RED)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("参数量（特征数 p）"); ax.set_ylabel("MSE")
    ax.grid(True, alpha=0.3, which="both")
    ax.legend(fontsize=9)
    ax.set_title("双下降：插值阈值尖峰 → 骤降 → 缓升", fontsize=12)
    return save(fig, "fig_ch1_double_descent.png")


def fig_ch2_saddle_escape():
    """图3 鞍点逃逸：逃逸速率（左）与扰动敏感性（右）——鞍点逃逸，真实 GD 重放。

    左：y(t) 半对数，两条近直线（斜率 0.020 vs 0.100/步，约 5 倍）。
    右：走出邻域步数 vs 初始扰动（对数横轴）——每减半，无动量 +35 步、动量 +7 步。
    """
    eta, beta, x0, y0, thr, steps = 0.01, 0.9, 0.008, 0.001, 0.3, 60

    def traj(mom, steps=steps):
        x, y = x0, y0
        vx = vy = 0.0
        xs, ys = [x], [y]
        for _ in range(steps):
            gx, gy = 2 * x, -2 * y
            if mom:
                vx = beta * vx - eta * gx; vy = beta * vy - eta * gy
                x += vx; y += vy
            else:
                x -= eta * gx; y -= eta * gy
            xs.append(x); ys.append(y)
        return np.array(xs), np.array(ys)

    def escape_steps(mom, y_ini, cap=100000):
        x, y = x0, y_ini
        vx = vy = 0.0
        for k in range(1, cap + 1):
            gx, gy = 2 * x, -2 * y
            if mom:
                vx = beta * vx - eta * gx; vy = beta * vy - eta * gy
                x += vx; y += vy
            else:
                x -= eta * gx; y -= eta * gy
            if abs(y) >= thr:
                return k
        return None

    _, y1 = traj(False); _, y2 = traj(True)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))

    ax = axes[0]
    ax.semilogy(range(steps + 1), y1, "--", color=BLUE_L, lw=2.2,
                marker="o", markevery=5, ms=4, label="无动量（×1.02/步）")
    ax.semilogy(range(steps + 1), y2, "-", color=BLUE, lw=2.4,
                marker="s", markevery=5, ms=4, label="动量 $\\beta=0.9$（×1.10/步）")
    ax.axhline(thr, color="gray", ls=":", lw=1.4)
    ax.text(1, thr * 1.25, "走出邻域（$|y|=0.3$）", fontsize=9, color="gray")
    ax.annotate("60步0.003", xy=(60, y1[-1]), xytext=(14, 0.0007),
                fontsize=9, color=BLUE_L,
                arrowprops=dict(arrowstyle="->", color=BLUE_L, lw=1))
    ax.annotate("60步0.313", xy=(60, y2[-1]), xytext=(8, 0.16),
                fontsize=9, color=BLUE,
                arrowprops=dict(arrowstyle="->", color=BLUE, lw=1))
    ax.set_xlabel("步数"); ax.set_ylabel("$y$（不稳定方向，对数）")
    ax.set_title("逃逸速率：斜率差约5倍", fontsize=12)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.18))

    y0s = np.logspace(-3, -1, 9)
    no = np.array([escape_steps(False, v) for v in y0s], dtype=float)
    mo = np.array([escape_steps(True, v) for v in y0s], dtype=float)
    ax = axes[1]
    ax.semilogx(y0s, no, "--", color=BLUE_L, lw=2.2, marker="o", ms=4, label="无动量")
    ax.semilogx(y0s, mo, "-", color=BLUE, lw=2.4, marker="s", ms=4,
                label="动量 $\\beta=0.9$")
    ax.annotate(f"{no[0]:.0f}步", xy=(y0s[0], no[0]), xytext=(0.0016, 300),
                fontsize=9, color=BLUE_L)
    ax.annotate(f"{no[-1]:.0f}步", xy=(y0s[-1], no[-1]), xytext=(0.055, 90),
                fontsize=9, color=BLUE_L)
    ax.annotate(f"{mo[0]:.0f}步", xy=(y0s[0], mo[0]), xytext=(0.0016, 75),
                fontsize=9, color=BLUE)
    ax.annotate(f"{mo[-1]:.0f}步", xy=(y0s[-1], mo[-1]), xytext=(0.055, 8),
                fontsize=9, color=BLUE)
    ax.set_ylim(0, no.max() * 1.15)
    ax.set_xlabel("初始扰动 $y_0$（对数）"); ax.set_ylabel("走出邻域步数")
    ax.set_title("扰动越小，走得越慢（每减半 +35步 / +7步）", fontsize=12)
    ax.grid(True, which="both", alpha=0.3); ax.legend(fontsize=9, loc="upper right")
    return save(fig, "fig_ch2_saddle_escape.png")


def fig_ch2_edge_of_stability():
    """图6 edge of stability —— 直接读 EoS 复算轨迹（与正文 §2.5 表格同源）。

    轨迹由 demo_edge_of_stability.py 生成（2-24-1 tanh、全批量 GD、η=0.5，600 步）；
    记录点即正文表格的 6 个里程碑。
    """
    trace = np.loadtxt(Path(__file__).resolve().parent / "demo_edge_of_stability_trace.tsv",
                       delimiter="\t", skiprows=1)
    k = trace[:, 0].astype(int); loss = trace[:, 1]; sharp = trace[:, 2]
    frontier = 4.0
    miles = np.isin(k, [0, 30, 60, 100, 300, 600])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    axes[0].plot(k, loss, "-", color=BLUE, lw=2.2)
    axes[0].set_xlabel("训练步数"); axes[0].set_ylabel("训练损失")
    axes[0].set_title("训练损失：总体下降", fontsize=12); axes[0].grid(True, alpha=0.3)
    axes[1].plot(k, sharp, "-", color=ORANGE, lw=1.8)
    axes[1].axhline(frontier, color="gray", ls="--", lw=1.5, label=f"$2/\\eta = {frontier:g}$")
    axes[1].plot(k[miles], sharp[miles], "o", color=RED, ms=6, label="实验记录点")
    axes[1].set_xlabel("训练步数"); axes[1].set_ylabel("锐度 $\\lambda_{\\max}$")
    axes[1].set_title("锐度：升破 $2/\\eta$ 后被压回附近震荡", fontsize=12)
    axes[1].grid(True, alpha=0.3); axes[1].legend(fontsize=9)
    return save(fig, "fig_ch2_edge_of_stability.png")


def fig_ch3_grokking():
    """图8 grokking 曲线（记录值，训练/测试准确率 + 表示变化率）"""
    steps = [500, 1000, 1500, 2000, 3000, 4000, 5000, 6000, 7000,
             10000, 20000, 30000, 50000]
    tr = [0.352, 0.799, 0.988, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    te = [0.001, 0.003, 0.063, 0.187, 0.473, 0.689, 0.820, 0.898, 0.937,
          0.981, 0.997, 0.999, 1.0]
    rep = [3.06, 0.90, 0.39, 0.19, 0.10, 0.09, 0.08, 0.07, 0.06, 0.05, 0.04, 0.03, 0.0]
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    ax.plot(steps, tr, "--", color=BLUE_L, lw=2.2, label="训练准确率")
    ax.plot(steps, te, "-", color=ORANGE, lw=2.8, label="测试准确率")
    ax.set_xscale("log")
    ax.set_xlabel("训练步数（对数）"); ax.set_ylabel("准确率")
    ax.set_ylim(0, 1.05); ax.grid(True, alpha=0.3, which="both")
    ax2 = ax.twinx()
    ax2.plot(steps, rep, "-.", color=BLUE, lw=2, label="表示变化率")
    ax2.set_ylabel("表示变化率"); ax2.set_ylim(0, 3.3)
    ax.annotate("测试 2000→7000 步陡升", xy=(2100, 0.5), xytext=(7000, 0.35),
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.2), fontsize=9, color=ORANGE)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=9, loc="center right")
    ax.set_title("grokking：训练早饱和、测试长滞后、随后陡升（表示在平台期仍变）", fontsize=11)
    return save(fig, "fig_ch3_grokking.png")


def fig_ch5_lazy_rich():
    """图11 lazy vs rich（记录值：初始化尺度 → 表示移动与方向余弦）"""
    sig = [0.005, 0.05, 0.5, 1.0]
    feat = [28.5, 2.8, 0.08, 0.08]
    cos = [0.125, 0.628, 0.991, 0.994]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot(sig, feat, "-o", color=BLUE, lw=2.4, ms=6, label="表示相对移动（左轴）")
    ax.set_xscale("log")
    ax.set_xlabel("初始化标准差 $\\sigma$（对数）"); ax.set_ylabel("表示相对移动")
    ax.grid(True, alpha=0.3)
    ax.annotate("rich：特征被重新塑造", xy=(0.005, 28.5), xytext=(0.0035, 26),
                fontsize=9, color=BLUE)
    # 方向余弦走右轴：与表示移动量纲不同，同轴会把余弦压在轴底
    ax2 = ax.twinx()
    ax2.plot(sig, cos, "-s", color=ORANGE, lw=2.4, ms=6, label="第一层方向余弦（右轴）")
    ax2.set_ylabel("第一层方向余弦"); ax2.set_ylim(0, 1.05)
    ax.annotate("lazy：特征几乎不动", xy=(1.0, 0.9), xytext=(0.12, 1.6),
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.2), fontsize=9, color=ORANGE)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=9, loc="center right")
    ax.set_title("lazy 与 rich：同样是学会，表示动不动差 350 倍", fontsize=11)
    return save(fig, "fig_ch5_lazy_rich.png")


def fig_ch5_mup_heatmap():
    """图12 宽度-学习率热力图：SP 与 μP（宽度扫描实测网格，SGD 2000 步，y=x1*x2）"""
    etas = [1e-3, 3e-3, 1e-2, 3e-2, 1e-1, 3e-1, 1e0, 3e0]
    widths = [32, 128, 512]
    spinf = np.array([
        [0.089, 0.054, 0.005, 0.002, 0.001, 0.008, np.nan, np.nan],
        [0.047, 0.008, 0.003, 0.002, np.nan, np.nan, np.nan, np.nan],
        [0.004, 0.003, 0.002, np.nan, np.nan, np.nan, np.nan, np.nan],
    ])
    mupinf = np.array([
        [0.116, 0.086, 0.038, 0.006, 0.002, 0.001, 0.000, 0.000],
        [0.136, 0.097, 0.035, 0.008, 0.003, 0.001, 0.000, 0.000],
        [0.078, 0.052, 0.019, 0.006, 0.003, 0.001, 0.000, 0.000],
    ])
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4))
    for ax, mat, title in ((axes[0], np.log10(spinf + 1e-12), "标准参数化 (SP)"),
                           (axes[1], np.log10(mupinf + 1e-12), "μP")):
        masked = np.ma.masked_invalid(mat)
        im = ax.imshow(masked, aspect="auto", origin="lower",
                       extent=[np.log10(etas[0]), np.log10(etas[-1]),
                               np.log10(widths[0]), np.log10(widths[-1])],
                       cmap="Blues", vmin=-3.5, vmax=0)
        ax.set_xticks(np.log10(etas)); ax.set_xticklabels([f"{e:.0e}" for e in etas], rotation=45, fontsize=8)
        ax.set_yticks(np.log10(widths)); ax.set_yticklabels(widths, fontsize=9)
        ax.set_xlabel("学习率 $\\eta$"); ax.set_ylabel("宽度 $m$")
        ax.set_title(title, fontsize=12)
    fig.colorbar(im, ax=axes, fraction=0.03, label=r"$\log_{10}$ 训练误差")
    fig.suptitle("最优学习率随宽度的走向：SP 下滑（右下），μP 平坦（最右列=发散前的稳定区）", y=1.04, fontsize=12)
    return save(fig, "fig_ch5_mup_heatmap.png")


def fig_ch4_powerlaw():
    """图9 参数-损失幂律与外推（慢尾谱外推 seed0 实测 + 拟合/外推）"""
    ps = np.array([8, 16, 32, 64, 128, 256, 512, 1024])
    L = np.array([0.538, 0.3786, 0.2737, 0.2118, 0.1693, 0.1393, 0.1197, 0.1114])
    Linf = 0.09
    small = ps[:4]; fit = np.polyfit(np.log(small), np.log(L[:4] - Linf), 1)
    al, c = -fit[0], np.exp(fit[1])
    xs = np.logspace(np.log10(6), np.log10(1400), 400)
    model = Linf + c * xs ** (-al)
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.loglog(xs, model, "-", color=BLUE_L, lw=2, label=f"拟合 $L=L_\\infty+c\\,p^{{-{al:.2f}}}$（仅 $p\\leq 64$）")
    ax.loglog(ps[:4], L[:4], "o", color=BLUE, ms=7, label="拟合用实测点")
    ax.loglog(ps[4:], L[4:], "s", color=ORANGE, ms=8, label="外推目标（有实测）")
    ax.axhline(Linf, color="gray", ls=":", lw=1.3, label="$L_\\infty=0.09$")
    ax.set_xlabel("参数量 $p$"); ax.set_ylabel("测试损失 $L$")
    ax.grid(True, alpha=0.3, which="both")
    ax.text(120, 0.145, "外推误差 ≤ 2.5%", fontsize=10, color=ORANGE)
    ax.legend(fontsize=9)
    ax.set_title("参数-损失幂律：小规模拟合，大规模外推几乎重合", fontsize=11)
    return save(fig, "fig_ch4_powerlaw.png")


def fig_ch4_allocation():
    """图10 数据受限 U 形曲线（配比实验 n=800 实测）"""
    p = [32, 64, 128, 192, 256, 512]
    L = [0.297, 0.236, 0.205, 0.202, 0.222, 0.351]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot(p, L, "-o", color=BLUE, lw=2.4, ms=6)
    ax.axvspan(128, 192, color=BLUE_LL, alpha=0.6)
    ax.axhline(0.2, color="gray", ls=":", lw=1.2)
    ax.set_xlabel("参数量 $p$"); ax.set_ylabel("测试 MSE（n=800 固定）")
    ax.set_xlim(16, 560); ax.grid(True, alpha=0.3)
    ax.annotate("谷底 $p\\approx128$–$192$", xy=(160, 0.2), xytext=(210, 0.24),
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.2), fontsize=9, color=RED)
    ax.annotate("参数太少：欠拟合 +47%", xy=(32, 0.297), xytext=(40, 0.32),
                fontsize=9, color=BLUE)
    ax.annotate("参数太多：过拟合 +75%", xy=(512, 0.351), xytext=(330, 0.37),
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.2), fontsize=9, color=RED)
    ax.set_title("数据受限下的最优配比：U 形谷底", fontsize=12)
    return save(fig, "fig_ch4_allocation.png")


def fig_ch6_superposition():
    """图13 叠加几何（重叠实验实测 + 理论曲线）"""
    d = np.linspace(3, 60, 200)
    theory = np.sqrt(2.0 / (np.pi * d))
    md = [8, 20, 40]; mv = [0.29, 0.18, 0.13]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot(d, theory, "-", color=BLUE_L, lw=2, label="$\\sqrt{2/(\\pi d)}$（理论）")
    ax.plot(md, mv, "o", color=ORANGE, ms=9, label="实测平均重叠")
    for x_, y_ in zip(md, mv):
        ax.annotate(f"{y_:.2f}", (x_, y_), textcoords="offset points", xytext=(-14, 10), fontsize=9)
    ax.axvline(20, color="gray", ls=":", lw=1.2)
    ax.text(21, 0.26, "$m=20$ 个特征\n$d<20$ 时必然叠加", fontsize=9, color="gray")
    ax.set_xlabel("空间维度 $d$"); ax.set_ylabel("平均重叠 $E|\\cos|$")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)
    ax.set_title("叠加几何：维度越低、特征越挤，平均重叠越高", fontsize=11)
    return save(fig, "fig_ch6_superposition.png")


def fig_ch6_sparse_recovery():
    """图14 稀疏恢复相变（稀疏恢复实验实测）"""
    s = [1, 2, 3, 5, 8]
    acc = [1.00, 0.89, 0.56, 0.08, 0.00]
    corr = [1.00, 0.94, 0.78, 0.55, 0.46]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot(s, acc, "-o", color=ORANGE, lw=2.6, ms=7, label="支撑+符号恢复率")
    ax.plot(s, corr, "--s", color=BLUE, lw=2, ms=6, label="平均恢复相关")
    ax.axvspan(4, 9, color=BLUE_LL, alpha=0.6)
    ax.text(4.2, 0.9, "相变：$s\\geq 4$ 后崩溃", fontsize=9, color="gray")
    ax.set_xlabel("每个观察含的特征数 $s$（稀疏度，越小越稀疏）")
    ax.set_ylabel("恢复指标"); ax.set_ylim(-0.05, 1.1)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)
    ax.set_title("稀疏恢复：特征越稀疏越可恢复，超过临界点崩溃", fontsize=11)
    return save(fig, "fig_ch6_sparse_recovery.png")


def fig_ch7_skills():
    """图16 基准→技能（技能分解：A/B 总分并列但剖面相反）"""
    skills = ["代数推理", "事实检索", "指令跟随"]
    A = [0.95, 0.30, 0.30]; B = [0.30, 0.95, 0.30]
    x = np.arange(3); w = 0.36
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.4))
    ax = axes[0]
    ax.bar(x - w / 2, A, w, color=BLUE, label="模型 A（代数强）")
    ax.bar(x + w / 2, B, w, color=ORANGE, label="模型 B（事实强）")
    ax.set_xticks(x); ax.set_xticklabels(skills)
    ax.set_ylabel("技能剖面强度"); ax.set_ylim(0, 1.1)
    ax.legend(fontsize=8); ax.grid(True, axis="y", alpha=0.3)
    ax.set_title("剖面：一个偏代数、一个偏事实", fontsize=11)
    ax = axes[1]
    tot = ax.bar(["A", "B"], [0.370, 0.383], color=[BLUE, ORANGE], width=0.5)
    for bar, v in zip(tot, [0.370, 0.383]):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.008, f"{v:.3f}", ha="center", fontsize=10)
    ax.set_ylim(0, 0.5); ax.set_ylabel("总分（400 条平均正确率）")
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_title("总分：只差 0.013，几乎并列", fontsize=11)
    fig.suptitle("基准→技能：SVD 前 3 奇异值占能量 93.5%——总分背后有 3 个技能维度", y=1.03, fontsize=11)
    return save(fig, "fig_ch7_skills.png")



def fig_ch2_singular_order():
    """图7 奇异值顺序学习——Saxe 2014 动力学示意（4 个奇异值；奇异值实验的两维情形同理，表值另源）"""
    t = np.logspace(0.0, 4.0, 400)
    sv0 = [1.6, 1.2, 0.8, 0.4]
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    for i, s0 in enumerate(sv0, 1):
        tau = 40.0 / (s0 * s0)
        sv = s0 * np.tanh(t / tau)
        ax.plot(t, sv, lw=2.2, label="奇异值 σ%d" % i)
    ax.axhline(0, color="gray", lw=1, ls=":")
    ax.set_xscale("log")
    ax.set_xlabel("训练步数（对数）")
    ax.set_ylabel("有效矩阵 $W_1 W_2$ 的奇异值")
    ax.set_ylim(0, 1.75); ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9, title="大奇异值先学")
    ax.set_title("顺序学习：奇异值按大小逐级追平（Saxe 2014）", fontsize=12)
    return save(fig, "fig_ch2_singular_order.png")

def fig_ch6_induction_circuit():
    """图15 induction head 匹配-复制电路示意图（induction 构造补图，非模拟数据）"""
    import matplotlib.patches as mpatches
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 5); ax.axis("off")
    def box(x, text, color, y=2.8):
        w, hh = 0.9, 0.8
        ax.add_patch(mpatches.FancyBboxPatch((x - w/2, y), w, hh,
                     boxstyle="round,pad=0.03", linewidth=1.6,
                     edgecolor=color, facecolor="white"))
        ax.text(x, y + hh/2, text, ha="center", va="center", fontsize=13)
    box(1.2, "A", BLUE); box(3.0, "B", BLUE); box(5.0, "C", BLUE_L)
    box(7.0, "D", BLUE); box(8.4, "B", ORANGE)
    ax.text(9.2, 3.2, "?", fontsize=15, ha="center")
    ax.text(5.2, 4.35, "输入序列（上一处 B 的后随 token 是 C）", ha="center", fontsize=10, color="#555")
    # 匹配：query B(8.4) -> key B(3.0)
    ax.annotate("", xy=(3.0, 4.05), xytext=(8.4, 4.05),
                arrowprops=dict(arrowstyle="->", color=BLUE, lw=2.0, ls="--"))
    ax.text(5.6, 4.05, "匹配 (Q·K)", fontsize=9, color=BLUE)
    # 复制：value C(5.0) -> 输出位置(9.2, 1.2)
    ax.annotate("", xy=(9.2, 1.4), xytext=(5.0, 1.4),
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=2.2))
    ax.text(7.1, 1.0, "复制 (V)", fontsize=9, color=ORANGE)
    ax.text(9.2, 1.0, "输出 C", ha="center", fontsize=12, color="#8a5a00", fontweight="bold")
    ax.set_title("induction head：匹配前文相同 token，复制其后随 token（机制示意，序列化简自 §6.4 的构造）", fontsize=12)
    return save(fig, "fig_ch6_induction_circuit.png")

def _henon_escape(a, b, x0, y0, n_steps, esc=6.0):
    """带逃逸区的 Hénon 映射（经典二维混沌映射）的逃逸时间：|x|>esc 或 |y|>esc 记逃逸；未逃逸返回 n_steps+1。"""
    x = np.array(x0, dtype=float)
    y = np.array(y0, dtype=float)
    t = np.full(x.shape, n_steps + 1)
    alive = np.ones(x.shape, bool)
    for k in range(1, n_steps + 1):
        x, y = 1 - a * x * x + y, b * x
        out = (np.abs(x) > esc) | (np.abs(y) > esc)
        t[alive & out] = k
        alive &= ~out
        x = np.where(alive, x, 0.0)
        y = np.where(alive, y, 0.0)
    return t


def fig_ch2_chaotic_saddle_basin():
    """图4 带逃逸区的 Hénon 映射（经典二维混沌映射，a=1.46, b=0.3）的逃逸时间盆地，初值网格数值重放。"""
    import matplotlib.colors as mcolors
    a, b, N = 1.46, 0.3, 200
    xs = np.linspace(-1.7, 1.7, 800)
    ys = np.linspace(-0.55, 0.55, 320)
    X, Y = np.meshgrid(xs, ys)
    t = _henon_escape(a, b, X, Y, N)
    frac_esc = float((t <= N).mean())
    med = float(np.median(t[t <= N]))
    survive = float((t > N).mean())
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "blues_seq", [BLUE_LL, BLUE_L, BLUE, "#123B66"])
    cmap.set_bad("white")
    fig, ax = plt.subplots(figsize=(8.8, 3.5))
    im = ax.pcolormesh(X, Y, np.ma.masked_where(t > N, t.astype(float)),
                       cmap=cmap, norm=mcolors.LogNorm(vmin=1, vmax=N),
                       shading="auto")
    cb = fig.colorbar(im, ax=ax, pad=0.012)
    cb.set_label("逃逸步数（对数色标）", fontsize=9)
    ax.set_xlabel("初始 $x_0$")
    ax.set_ylabel("初始 $y_0$")
    ax.set_title(
        f"逃逸时间盆地：{frac_esc:.0%}在{N}步内逃逸（中位{med:.0f}步）；"
        f"白色留存集占{survive:.1%}", fontsize=10.5)
    print(f"[图4] 逃逸占比 {frac_esc:.3f}，中位 {med:.0f}，留存 {survive:.3f}")
    return save(fig, "fig_ch2_chaotic_saddle_basin.png")


def fig_ch2_chaotic_saddle_escape_stats():
    """图5 滞留时间的生存曲线与指数尾拟合（同参数，随机初值 30 万个）。"""
    a, b, N = 1.46, 0.3, 200
    rng = np.random.default_rng(7)
    n = 300000
    t = _henon_escape(a, b, rng.uniform(-1.7, 1.7, n),
                      rng.uniform(-0.55, 0.55, n), N)
    ks = np.arange(0, 121)
    P = np.array([(t > k).mean() for k in ks])
    m = (ks >= 20) & (ks <= 100)
    sl = np.polyfit(ks[m], np.log(P[m]), 1)
    kappa = -sl[0]
    med = int(np.median(t[t <= N]))
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.semilogy(ks, P, "-", color=BLUE, lw=2.6, label="尚未逃逸的比例 $P(t>k)$")
    ax.semilogy(ks, np.exp(np.polyval(sl, ks)), "--", color="#123B66",
                lw=1.8, label=f"指数尾拟合：逃逸率 $\\kappa\\approx{kappa:.3f}$/步")
    ax.annotate(f"中位滞留{med}步", xy=(med, P[med]), xytext=(32, 0.22),
                fontsize=9, color=BLUE,
                arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.1))
    ax.set_xlabel("步数 $k$")
    ax.set_ylabel("尚未逃逸的比例（对数）")
    ax.set_xlim(0, 120)
    ax.set_title("滞留时间的生存曲线：尾部按指数衰减", fontsize=12)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=9)
    print(f"[图5] κ≈{kappa:.4f}/步，中位 {med} 步")
    return save(fig, "fig_ch2_chaotic_saddle_escape_stats.png")


def main():
    setup_rc(dpi=200)
    print(f"输出目录: {OUTPUT_DIR}")
    funcs = [
        fig_ch1_bias_variance, fig_ch1_double_descent,
        fig_ch2_saddle_escape, fig_ch2_edge_of_stability,
        fig_ch3_grokking, fig_ch5_lazy_rich, fig_ch5_mup_heatmap,
        fig_ch4_powerlaw, fig_ch4_allocation,
        fig_ch6_superposition, fig_ch6_sparse_recovery, fig_ch7_skills,
        fig_ch2_singular_order, fig_ch6_induction_circuit,
        fig_ch2_chaotic_saddle_basin, fig_ch2_chaotic_saddle_escape_stats,
    ]
    from fig_common import run_all
    return run_all(funcs, "AI规律：从现象到预见", expected=16)


if __name__ == "__main__":
    sys.exit(main())  # 失败张数作为退出码，CI 才能真的拦住