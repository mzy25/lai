#!/usr/bin/env python3
"""AI数学：从起步到前沿 —— 配图生成脚本
生成21张dpi=200的教学配图

使用方法:
    python3 generate_figures.py

输出: figures/目录下的21张PNG图片
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))
import fig_common  # noqa: E402  (sys.path 就绪后再导入共享模块)
from fig_common import CJK_FONT_NAME, setup_rc  # noqa: E402
# 语义色板（改图/新图一律从本表取色，禁止表外独点色）
from fig_common import (  # noqa: E402
    ROLE_DANGER, ROLE_SUCCESS, ROLE_WARNING, ROLE_PRIMARY,
    BLUE, RED, GREEN, ORANGE, GRAY, INK, WHITE,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "figures"


def save(fig, name):
    """保存并返回路径。

    必须 return —— run_all() 靠返回值判断这张图是否真的落盘，
    不返回会让"生成成功"的统计形同虚设。
    """
    return fig_common.save_fig(fig, name, OUTPUT_DIR, dpi=200)


setup = lambda: (setup_rc(dpi=200), print(f"输出目录: {OUTPUT_DIR}"), print("开始生成21张配图..."))

# ============================================================
# Ch0 - 1张图
# ============================================================

def fig_ch0_ai_panorama():
    """图0: AI 全景——训练回路（左）与损失地形（右）

    与正文第0章严格对应：
      左：输入 x → 带旋钮的函数 f(x; θ) → 预测 ŷ → 与训练数据里的真实答案 y 比一比
          → 损失 L → 损失回头告诉旋钮"往哪边拧、拧多少"（闭环反复跑）。
      右：损失随旋钮 θ₀ 变化——本例钉死 θ₁=3、真实房价 y=330 万，
          L = (ŷ - y)² = (θ₀ - 120)²，是一条开口向上的抛物线；
          红点是从 θ₀=100 出发、一步步走到碗底 θ₀=120 的调整轨迹。
    """
    from matplotlib.patches import FancyBboxPatch

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2))

    # ============ 左：训练回路 ============
    ax = axes[0]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis('off')

    def box(xc, yc, w, h, text, fc, tc=INK, fs=11.5, bold=False):
        ax.add_patch(FancyBboxPatch(
            (xc - w / 2, yc - h / 2), w, h,
            boxstyle="round,pad=0.06,rounding_size=0.18",
            linewidth=1.5, edgecolor=GRAY["d"], facecolor=fc, zorder=2))
        ax.text(xc, yc, text, ha='center', va='center', fontsize=fs, color=tc,
                fontproperties=CJK_FONT_NAME,
                fontweight='bold' if bold else 'normal', zorder=3)

    box(1.15, 4.5, 1.9, 1.0, '输入 $x$\n（面积 70m²）', BLUE["l"])
    box(4.35, 4.5, 3.3, 1.0, '带旋钮的函数\n$\\hat{y}=f(x;\\ \\theta)$', GREEN["l"], bold=True)
    box(7.85, 4.5, 1.9, 1.0, '预测 $\\hat{y}$\n（猜 310 万）', ORANGE["l"])
    box(7.85, 2.1, 3.4, 1.2, '比一比：$\\hat{y}$ 与真实 $y$ 差多少\n'
                             '损失 $L=(\\hat{y}-y)^2$', ORANGE["l"], bold=True)
    box(1.35, 2.1, 2.3, 1.0, '训练数据\n真实答案 $y$=330 万', GRAY["l"])

    def arrow(xy, xytext, color, rad=0.0, lw=1.8, ls='-'):
        ax.annotate('', xy=xy, xytext=xytext, zorder=4,
                    arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                                    linestyle=ls,
                                    connectionstyle=f"arc3,rad={rad}"))

    arrow((2.75, 4.5), (2.15, 4.5), GRAY["d"])          # 输入 → 函数
    arrow((6.85, 4.5), (6.05, 4.5), GRAY["d"])          # 函数 → 预测
    arrow((7.85, 2.8), (7.85, 3.9), GRAY["d"])         # 预测 → 比一比（头在比一比方，向下）
    arrow((6.1, 2.1), (2.55, 2.1), GRAY["d"])          # 真实答案 → 比一比（跨空隙，头在比一比方）
    arrow((4.35, 4.0), (6.05, 2.4), ROLE_DANGER, rad=0.35, lw=2.0)  # 损失 → 旋钮（反馈，头落在函数盒下缘、指向盒内）

    ax.text(1.55, 1.05, '损失回头告诉旋钮："往哪边拧、拧多少"',
            fontsize=10.5, color=ROLE_DANGER, fontproperties=CJK_FONT_NAME,
            ha='center')
    ax.text(5.0, 5.75, '这个回路要反复跑成千上万遍', fontsize=12,
            color=INK, fontproperties=CJK_FONT_NAME, ha='center',
            fontweight='bold')
    ax.set_title('左：训练回路', fontsize=13, fontproperties=CJK_FONT_NAME,
                 loc='left', y=-0.02)

    # ============ 右：损失地形 ============
    ax = axes[1]
    th = np.linspace(100, 140, 400)
    ax.plot(th, (th - 120) ** 2, color=BLUE["m"], lw=2.6,
            label=r'损失 $L=(\theta_0-120)^2$')

    # 红点轨迹：从 θ₀=100 出发，每步朝碗底走一截（一次次调整旋钮）
    path = [100.0]
    for _ in range(7):
        path.append(path[-1] + 0.5 * (120 - path[-1]))
    path.append(120.0)
    ax.plot(path, [(p - 120) ** 2 for p in path], 'o-', color=ROLE_DANGER,
            ms=7, lw=1.8, zorder=5, label='一次次调整旋钮的轨迹')

    ax.plot(120, 0, '*', color='gold', ms=22, mec=INK, mew=1.2, zorder=6)
    ax.annotate('碗底 = 损失最小\n最优旋钮 $\\theta_0^*=120$', xy=(120, 0),
                xytext=(121.5, 95), fontsize=10.5, color=GREEN["d"],
                fontproperties=CJK_FONT_NAME,
                arrowprops=dict(arrowstyle='->', color=GREEN["d"], lw=1.6))
    ax.annotate('起点：随便猜的旋钮\n$\\theta_0=100$，损失 400',
                xy=(100, 400), xytext=(101.2, 300), fontsize=10.5,
                color=ROLE_DANGER, fontproperties=CJK_FONT_NAME,
                arrowprops=dict(arrowstyle='->', color=ROLE_DANGER, lw=1.6))

    ax.set_xlabel('旋钮 $\\theta_0$（本节钉死 $\\theta_1=3$ 不动）', fontsize=12,
                  fontproperties=CJK_FONT_NAME)
    ax.set_ylabel('损失 $L$', fontsize=12)
    ax.set_title('右：损失地形——山高 = 错得多离谱', fontsize=13,
                 fontproperties=CJK_FONT_NAME)
    ax.set_ylim(-45, 480)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=9.5, loc='upper right', prop=CJK_FONT_NAME)

    plt.tight_layout()
    return save(fig, 'fig_ch0_ai_panorama.png')


# ============================================================
# Ch1 - 4张图
# ============================================================

def fig_ch1_gradient_path():
    """图1: 梯度下降路径 (x₀=3, η=0.3)"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    
    ax1 = axes[0]
    x = np.linspace(-4, 4, 200)
    ax1.plot(x, x**2, 'b-', lw=2, label=r'$f(x)=x^2$', alpha=0.7)
    
    x0, eta = 3.0, 0.3
    px, py = [x0], [x0**2]
    for i in range(6):
        grad = 2 * px[-1]
        px.append(px[-1] - eta * grad)
        py.append(px[-1]**2)
    
    ax1.scatter(px, py, c='red', s=60, zorder=5)
    for i in range(len(px)):
        # x3..x6 挤在原点附近，标签扇形错开防叠
        off = (8, 8) if i < 2 else (10 + 15 * (i - 2), 6 + 12 * (i - 2))
        ax1.annotate(f'$x_{i}$', (px[i], py[i]), textcoords="offset points", xytext=off, fontsize=11)
    for i in range(len(px)-1):
        ax1.annotate('', xy=(px[i+1], py[i+1]), xytext=(px[i], py[i]),
                    arrowprops=dict(arrowstyle='->', color='red', lw=1.5))
    
    ax1.set_xlabel('x', fontsize=12); ax1.set_ylabel('f(x)', fontsize=12)
    ax1.set_title('Gradient Descent: x0=3, eta=0.3', fontsize=13)
    ax1.legend(); ax1.set_xlim(-4,4); ax1.set_ylim(-1,17); ax1.grid(True, alpha=0.3)
    
    ax2 = axes[1]
    iters = list(range(len(px)))
    ax2.plot(iters, px, 'ro-', ms=8, lw=2)
    ax2.axhline(y=0, color='green', ls='--', alpha=0.7)
    ax2.text(5.5, 0.3, 'optimum x*=0', fontsize=10, color='green')
    for i, p in enumerate(px):
        lbl = f'{p:.4f}' if abs(p-round(p)) > 0.001 else f'{int(round(p))}'
        ax2.annotate(lbl, (i, p), textcoords="offset points", xytext=(0,12), ha='center', fontsize=9)
    ax2.set_xlabel('iteration', fontsize=12); ax2.set_ylabel('x value', fontsize=12)
    ax2.set_title('x converges quickly', fontsize=13)
    ax2.set_xticks(iters); ax2.grid(True, alpha=0.3)
    
    return save(fig, 'fig_ch1_gradient_path.png')

def fig_ch1_learning_rate():
    """图2: 三种学习率对比

    与正文 §1.4 严格对应（同一把尺子：损失降到初始值的千分之一）：
      eta=1.0  震荡，永远降不下去
      eta=0.3  4 步达标
      eta=0.01 171 步才达标（x 每步只收缩 2%）
    """
    fig, axes = plt.subplots(1, 4, figsize=(17.5, 4.1))

    def gd_path(x0, eta, n):
        pts = [x0]
        for _ in range(n):
            pts.append(pts[-1] - eta * 2 * pts[-1])
        return pts

    x = np.linspace(-4, 4, 200)

    # ---------- eta=1.0 震荡 ----------
    ax = axes[0]
    pts = gd_path(3.0, 1.0, 6)
    ax.plot(x, x**2, color=BLUE["m"], lw=1.5, alpha=0.4)
    ax.plot(pts, [p**2 for p in pts], 'o-', color=ROLE_DANGER, ms=5)
    for i in range(len(pts) - 1):
        ax.annotate('', xy=(pts[i + 1], pts[i + 1]**2), xytext=(pts[i], pts[i]**2),
                    arrowprops=dict(arrowstyle='->', color=ROLE_DANGER, lw=1))
    ax.set_title(r'$\eta=1.0$  震荡', fontsize=12, fontproperties=CJK_FONT_NAME)
    ax.set_xlabel('x'); ax.set_ylabel('f(x)')
    ax.set_xlim(-4, 4); ax.set_ylim(-1, 17); ax.grid(True, alpha=0.3)

    # ---------- eta=0.3 收敛 ----------
    ax = axes[1]
    pts = gd_path(3.0, 0.3, 6)
    ax.plot(x, x**2, color=BLUE["m"], lw=1.5, alpha=0.4)
    ax.plot(pts, [p**2 for p in pts], 'o-', color=GREEN["m"], ms=5)
    for i in range(len(pts) - 1):
        ax.annotate('', xy=(pts[i + 1], pts[i + 1]**2), xytext=(pts[i], pts[i]**2),
                    arrowprops=dict(arrowstyle='->', color=GREEN["m"], lw=1))
    ax.set_title(r'$\eta=0.3$  4 步降至千分之一', fontsize=12,
                 fontproperties=CJK_FONT_NAME)
    ax.set_xlabel('x'); ax.set_ylabel('f(x)')
    ax.set_xlim(-4, 4); ax.set_ylim(-1, 17); ax.grid(True, alpha=0.3)

    # ---------- eta=0.01 极慢 ----------
    ax = axes[2]
    N_SLOW = 171                      # 正文：降到同样千分之一所需步数
    pts = gd_path(3.0, 0.01, N_SLOW)
    ax.plot(x, x**2, color=BLUE["m"], lw=1.5, alpha=0.4, label=r'$f(x)=x^2$')
    sample = pts[::15]
    ax.plot(sample, [p**2 for p in sample], 'o-', color=ORANGE["m"], ms=4, lw=1)
    for i in range(len(sample) - 1):
        ax.annotate('', xy=(sample[i + 1], sample[i + 1]**2),
                    xytext=(sample[i], sample[i]**2),
                    arrowprops=dict(arrowstyle='->', color=ORANGE["m"],
                                    lw=0.8, alpha=0.8))
    ax.plot(pts[0], pts[0]**2, '>', color=GREEN["d"], ms=8, label='起点 $x_0=3$')
    ax.plot(pts[-1], pts[-1]**2, '*', color=ROLE_DANGER, ms=12,
            label=f'第 {N_SLOW} 步')
    ax.set_title(rf'$\eta=0.01$  需 {N_SLOW} 步才到同样位置', fontsize=12,
                 fontproperties=CJK_FONT_NAME)
    ax.set_xlabel('x'); ax.set_ylabel('f(x)')
    ax.set_xlim(-4, 4); ax.set_ylim(-1, 17); ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, prop=CJK_FONT_NAME)

    # ---------- 同一把尺子：f/f0 的对数衰减 ----------
    ax = axes[3]
    steps = np.arange(0, 201)
    f0 = 9.0
    def ratio(eta):
        xx = 3.0
        out = []
        for _ in steps:
            out.append(xx * xx / f0)
            xx = xx - eta * 2 * xx
        return np.array(out)

    r_big, r_ok, r_small = ratio(1.0), ratio(0.3), ratio(0.01)
    ax.semilogy(steps, r_big,   color=ROLE_DANGER, lw=2,   label=r'$\eta=1.0$  震荡')
    ax.semilogy(steps, r_ok,    color=GREEN["m"],  lw=2,   label=r'$\eta=0.3$')
    ax.semilogy(steps, r_small, color=ORANGE["m"], lw=2,   label=r'$\eta=0.01$')
    ax.axhline(1e-3, color=GRAY["d"], ls='--', lw=1.4)
    ax.text(8, 1.5e-3, '千分之一（同一把尺子）', fontsize=9, ha='left',
            color=GRAY["d"], fontproperties=CJK_FONT_NAME)

    def mark_at(arr, thr=1e-3):
        idx = np.argmax(arr < thr)
        return idx if arr[idx] < thr else None

    k_ok = mark_at(r_ok)
    k_sm = mark_at(r_small)
    if k_ok:
        ax.plot([k_ok], [r_ok[k_ok]], 'o', color=GREEN["d"], ms=8, zorder=5)
        ax.annotate(f'{k_ok} 步', xy=(k_ok, r_ok[k_ok]), xytext=(k_ok + 12, 3e-2),
                    fontsize=10, color=GREEN["d"], fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color=GREEN["d"], lw=1.3))
    if k_sm:
        ax.plot([k_sm], [r_small[k_sm]], 'o', color=ORANGE["d"], ms=8, zorder=5)
        ax.annotate(f'{k_sm} 步', xy=(k_sm, r_small[k_sm]), xytext=(k_sm - 62, 4e-3),
                    fontsize=10, color=ORANGE["d"], fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color=ORANGE["d"], lw=1.3))

    ax.set_xlabel('步数', fontsize=12, fontproperties=CJK_FONT_NAME)
    ax.set_ylabel(r'$f/f_0$（对数刻度）', fontsize=12)
    ax.set_title('同一把尺子：4 步 vs 171 步', fontsize=12,
                 fontproperties=CJK_FONT_NAME)
    ax.set_ylim(1e-10, 3)
    ax.set_xlim(0, 200)
    ax.grid(True, which='both', alpha=0.25)
    ax.legend(fontsize=8.5, loc='lower left', prop=CJK_FONT_NAME)

    plt.suptitle('学习率：太大震荡 / 刚好 4 步 / 太小 171 步', fontsize=14, y=1.03,
                 fontproperties=CJK_FONT_NAME)
    plt.tight_layout()
    return save(fig, 'fig_ch1_learning_rate.png')


def fig_ch1_local_minimum():
    """图4: 局部最小值（非对称双井）vs 鞍点

    与正文 §1.6 严格对应：
      左：f(x)=x^4-4x^2+4x —— 浅坑 x=1 (f=1) 与深谷 x=-phi (f=-10.09) 深浅悬殊，
          从 x0=2 出发的梯度下降必定困在浅坑。
      右：鞍点 f(x,y)=x^2-y^2 —— 存在下坡方向，但停在原点时梯度为零、更新量为零，
          确定性轨迹精确停在原地；起点偏一丝或被噪声踢一下，才会沿下坡方向离开。
          （更新为 -η∇f = (-0.1x, +0.1y)，y 分量按 1.1^n 放大，故子图固定 ±2 视窗。）
    """
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.0))

    # ============ 左：局部最小值（非对称双井） ============
    ax = axes[0]
    f  = lambda x: x**4 - 4 * x**2 + 4 * x
    df = lambda x: 4 * x**3 - 8 * x + 4

    xs = np.linspace(-2.4, 2.4, 600)
    ax.plot(xs, f(xs), color=INK, lw=2, label=r'$f(x)=x^4-4x^2+4x$')

    phi = (1 + np.sqrt(5)) / 2
    x_deep, x_hill, x_shallow = -phi, 1 / phi, 1.0

    # 深谷
    ax.plot(x_deep, f(x_deep), 'o', color=ROLE_DANGER, ms=11, zorder=5)
    ax.annotate('深谷  ' + r'$x\approx-1.618$' + '\n' + r'$f\approx-10.09$',
                xy=(x_deep, f(x_deep)), xytext=(-2.32, -6.6),
                fontsize=10.5, color=ROLE_DANGER, va='top',
                arrowprops=dict(arrowstyle='->', color=ROLE_DANGER, lw=1.6))
    # 山丘
    ax.plot(x_hill, f(x_hill), 'o', color=GRAY["m"], ms=9, zorder=5)
    ax.annotate('山丘  ' + r'$x\approx0.618$' + '\n' + r'$f\approx1.09$',
                xy=(x_hill, f(x_hill)), xytext=(0.25, 7.4),
                fontsize=10.5, color=GRAY["d"],
                arrowprops=dict(arrowstyle='->', color=GRAY["m"], lw=1.6))
    # 浅坑
    ax.plot(x_shallow, f(x_shallow), 'o', color=ORANGE["m"], ms=11, zorder=5)
    ax.annotate('浅坑  ' + r'$x=1$' + '\n' + r'$f=1.00$',
                xy=(x_shallow, f(x_shallow)), xytext=(1.55, 3.1),
                fontsize=10.5, color=ORANGE["d"],
                arrowprops=dict(arrowstyle='->', color=ORANGE["m"], lw=1.6))

    # 梯度下降轨迹：从 x0=2 出发，困在浅坑
    eta, xt = 0.03, 2.0
    traj = [xt]
    for _ in range(60):
        xt = xt - eta * df(xt)
        traj.append(xt)
    traj = np.array(traj)
    ax.plot(traj, f(traj), '--', color=ROLE_DANGER, lw=2,
            label=r'梯度下降路径  $\eta=0.03$')
    ax.plot(traj[0], f(traj[0]), 's', color=ROLE_DANGER, ms=10, label=r'起点  $x_0=2$')
    for i in [0, 3, 8, 20, 59]:
        if i + 1 < len(traj):
            ax.annotate('', xy=(traj[i + 1], f(traj[i + 1])),
                        xytext=(traj[i], f(traj[i])),
                        arrowprops=dict(arrowstyle='->', color=GREEN["m"],
                                        lw=1.3, alpha=0.85))

    ax.axhline(0, color=GRAY["m"], lw=0.6, alpha=0.5)
    ax.set_xlabel('x', fontsize=12)
    ax.set_ylabel('f(x)', fontsize=12)
    ax.set_title('局部最小值困境：滑进浅坑，到不了深谷', fontsize=13,
                 fontproperties=CJK_FONT_NAME)
    ax.legend(fontsize=9.5, loc='lower right', prop=CJK_FONT_NAME)  # 右上被曲线右支占据，右下为空区
    ax.grid(alpha=0.25)
    ax.set_ylim(-12, 9)

    # ============ 右：鞍点 ============
    ax = axes[1]
    g = np.linspace(-2, 2, 400)
    X, Y = np.meshgrid(g, g)
    Z = X**2 - Y**2
    ax.contourf(X, Y, Z, levels=22, cmap='RdBu_r', alpha=0.55)
    ax.contour(X, Y, Z, levels=12, colors=GRAY["d"], linewidths=0.6, alpha=0.5)

    # 确定性梯度下降：-η∇f = (-0.1x, +0.1y)。
    # 起点严格落在 y=0 的水平轴上 → y 恒为 0、x 按 0.9^n 收缩到 0，
    # 最终精确停在原点：梯度为零，更新量为零，一步也迈不出去。
    for i, x0 in enumerate((1.8, 1.1, -1.1, -1.8)):
        p = np.array([x0, 0.0], dtype=float)
        tr = [p.copy()]
        for _ in range(80):
            p = p - 0.05 * np.array([2 * p[0], -2 * p[1]])
            tr.append(p.copy())
        tr = np.array(tr)
        ax.plot(tr[:, 0], tr[:, 1], '-', color=ROLE_DANGER, lw=1.9, alpha=0.9,
                label='确定性轨迹（$y_0=0$）：停在鞍点' if i == 0 else None)
        ax.plot(tr[0, 0], tr[0, 1], 'o', color=ROLE_DANGER, ms=7)

    # 起点只要偏离一丝（y₀=0.02），确定性轨迹最终仍会沿下坡的 y 方向溜走——
    # 说明"存在下坡方向"和"算法自己会走过去"是两件事：停在鞍点上的轨迹不会
    # 自己启动，能被启动的只有"被扰动过"的轨迹（噪声、动量、显式扰动）。
    p = np.array([1.8, 0.02], dtype=float)
    tr = [p.copy()]
    for _ in range(80):
        p = p - 0.05 * np.array([2 * p[0], -2 * p[1]])
        tr.append(p.copy())
    tr = np.array(tr)
    ax.plot(tr[:, 0], tr[:, 1], '--', color=ORANGE["m"], lw=2.0,
            label=r'起点偏一丝 $y_0=0.02$：终究沿下坡溜走')
    ax.plot(tr[0, 0], tr[0, 1], 'o', color=ORANGE["m"], ms=7)

    # 加噪声：从同一个 y=0 的起点出发，噪声不断把轨迹踢出水平轴，离开得快得多
    np.random.seed(0)
    p = np.array([1.8, 0.0], dtype=float)
    tr = [p.copy()]
    for _ in range(160):
        grad = np.array([2 * p[0], -2 * p[1]])
        p = p - 0.05 * grad + 0.06 * np.random.randn(2)
        tr.append(p.copy())
    tr = np.array(tr)
    ax.plot(tr[:, 0], tr[:, 1], '-', color=GREEN["d"], lw=2.2,
            label='加噪声：从同一处出发，很快离开')
    ax.plot(tr[0, 0], tr[0, 1], 'o', color=GREEN["d"], ms=7)

    ax.plot(0, 0, '*', color='gold', ms=22, mec=INK, mew=1.2, zorder=6)
    ax.annotate('鞍点：梯度 = 0\n更新量 = 0，原地不动', xy=(0, 0),
                xytext=(-1.98, 1.28), fontsize=10.5,
                fontproperties=CJK_FONT_NAME,
                arrowprops=dict(arrowstyle='->', color=INK, lw=1.5))
    ax.annotate('下坡方向（y 轴）', xy=(0, -1.95), xytext=(-2.15, -0.55),
                fontsize=10.5, color=GREEN["d"], fontproperties=CJK_FONT_NAME,
                arrowprops=dict(arrowstyle='->', color=GREEN["d"], lw=1.6))
    ax.annotate('上坡方向（x 轴）', xy=(1.95, 0), xytext=(0.60, 1.72),
                fontsize=10.5, color=ROLE_DANGER, fontproperties=CJK_FONT_NAME,
                arrowprops=dict(arrowstyle='->', color=ROLE_DANGER, lw=1.6))

    ax.set_xlabel('x', fontsize=12)
    ax.set_ylabel('y', fontsize=12)
    ax.set_title(r'鞍点 $f(x,y)=x^2-y^2$：有下坡路，但梯度为零走不动',
                 fontsize=13, fontproperties=CJK_FONT_NAME)
    ax.set_xlim(-2, 2)          # y 分量按 1.1^n 增长，必须锁死视窗，否则画面被撑爆
    ax.set_ylim(-2, 2)
    ax.legend(fontsize=8.5, loc='upper center', bbox_to_anchor=(0.5, -0.10),
              prop=CJK_FONT_NAME, framealpha=0.9)
    ax.set_aspect('equal')

    plt.tight_layout()
    return save(fig, 'fig_ch1_local_minimum.png')


def fig_ch1_adam_vs_gd():
    """图3: Adam vs 朴素梯度下降 (f=w1²+10w2², init(3,2))"""
    coef = 10
    init = np.array([3.0, 2.0])
    steps = 30

    # GD eta=0.1
    gd_w = [init.copy()]
    gd_loss = [init[0]**2 + coef*init[1]**2]
    w = init.copy()
    for _ in range(steps):
        w = w - 0.1 * np.array([2*w[0], 2*coef*w[1]])
        gd_w.append(w.copy())
        gd_loss.append(w[0]**2 + coef*w[1]**2)
    gd_w = np.array(gd_w)

    # Adam lr=0.6, b1=0.9, b2=0.999
    adam_w = [init.copy()]
    adam_loss = [init[0]**2 + coef*init[1]**2]
    m = v = np.zeros(2)
    w = init.copy()
    eps = 1e-8
    for t in range(1, steps+1):
        g = np.array([2*w[0], 2*coef*w[1]])
        m = 0.9*m + 0.1*g
        v = 0.999*v + 0.001*g**2
        mh = m / (1 - 0.9**t)
        vh = v / (1 - 0.999**t)
        w = w - 0.6 * mh / (np.sqrt(vh) + eps)
        adam_w.append(w.copy())
        adam_loss.append(w[0]**2 + coef*w[1]**2)
    adam_w = np.array(adam_w)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # Left: contour + trajectories
    ax = axes[0]
    w1 = np.linspace(-3.5, 3.5, 200)
    w2 = np.linspace(-2.5, 2.5, 200)
    W1, W2 = np.meshgrid(w1, w2)
    Z = W1**2 + coef*W2**2
    ax.contour(W1, W2, Z, levels=20, colors='gray', alpha=0.4, linewidths=0.8)
    ax.plot(gd_w[:10, 0], gd_w[:10, 1], 'r-o', lw=2, ms=5, label='GD ($\\eta=0.1$)', zorder=5)
    ax.plot(adam_w[:15, 0], adam_w[:15, 1], 'b-o', lw=2, ms=4, label='Adam ($lr=0.6$)', zorder=5)
    ax.plot(0, 0, 'k*', ms=15, zorder=10)
    ax.annotate('minimum', (0, 0), textcoords='offset points', xytext=(10, 10), fontsize=10)
    ax.set_xlabel('$w_1$', fontsize=12)
    ax.set_ylabel('$w_2$', fontsize=12)
    ax.set_title('Trajectories on $f=w_1^2+10w_2^2$', fontsize=13, fontweight='bold')
    ax.legend(loc='upper right'); ax.set_xlim(-3.5, 3.5); ax.set_ylim(-2.5, 2.5)
    ax.set_aspect('equal'); ax.grid(True, alpha=0.2)

    # Right: loss curves
    ax = axes[1]
    ax.plot(range(steps+1), gd_loss, 'r-', lw=2, label='GD')
    ax.plot(range(steps+1), adam_loss, 'b-', lw=2, label='Adam')
    ax.annotate(f'step 4: loss={adam_loss[4]:.2f}', (4, adam_loss[4]),
                textcoords='offset points', xytext=(15, 20), fontsize=9,
                arrowprops=dict(arrowstyle='->', color='blue'))
    ax.annotate(f'step 8: loss={adam_loss[8]:.2f}', (8, adam_loss[8]),
                textcoords='offset points', xytext=(15, -20), fontsize=9,
                arrowprops=dict(arrowstyle='->', color='blue'))
    ax.annotate('GD: $w_2$ 方向震荡不收敛\n(步长0.1 × 曲率20 = 2 → 恰好震荡)\nloss 卡在 $\\approx 10w_2^2 = 40$',
                xy=(20, gd_loss[20]), textcoords='offset points', xytext=(-100, 10),
                fontsize=9, color='red', fontproperties=CJK_FONT_NAME,
                arrowprops=dict(arrowstyle='->', color='red', lw=1.2))
    ax.set_xlabel('step', fontsize=12)
    ax.set_ylabel('loss', fontsize=12)
    ax.set_title('Loss convergence: GD slow vs Adam fast', fontsize=13, fontweight='bold')
    ax.legend(loc='upper right'); ax.set_xlim(0, steps); ax.set_ylim(-1, 55)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return save(fig, 'fig_ch1_adam_vs_gd.png')

def fig_ch2_lagrange():
    """图5: 拉格朗日乘子法——等高线相切 (f=x²+y, 单位圆)"""
    fig = plt.figure(figsize=(8, 6.5))
    ax = fig.add_subplot(111)
    
    x = np.linspace(-1.5, 1.5, 200)
    contour_specs = [(0.5, 'lightskyblue', '-', 1.5, 'normal'),
                     (1.0, 'cornflowerblue', '-', 1.5, 'normal'),
                     (1.25, 'navy', '-', 2.5, 'bold'),
                     (1.5, 'steelblue', '--', 1.5, 'normal')]
    for c, color, ls, lw, fw in contour_specs:
        yc = c - x**2
        mask = (yc >= -0.5) & (yc <= 1.5)
        ax.plot(x[mask], yc[mask], color=color, lw=lw, ls=ls)
        y_label = min(c, 1.42)
        ax.text(0, y_label, f'f={c}', fontsize=8, color=color,
                fontweight=fw, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                          alpha=0.85, edgecolor='none'))
    
    theta = np.linspace(0, 2*np.pi, 300)
    ax.plot(np.cos(theta), np.sin(theta), 'r-', lw=2, label='constraint: x²+y²=1')
    
    x_opt = np.sqrt(3)/2
    y_opt = 0.5
    ax.plot(x_opt, y_opt, 'ro', ms=12, zorder=5)
    ax.plot(-x_opt, y_opt, 'ro', ms=8, zorder=5)
    ax.text(x_opt+0.05, y_opt+0.08, f'P(√3/2, 1/2)\n≈(0.866, 0.5)', fontsize=9, color='darkred')
    ax.text(-x_opt-0.75, y_opt+0.08, '对称最优点\n≈(-0.866, 0.5)', fontsize=9, color='darkred')
    
    scale = 0.15
    ax.annotate('', xy=(x_opt + scale*np.sqrt(3), y_opt + scale*1),
                xytext=(x_opt, y_opt), arrowprops=dict(arrowstyle='->', color='blue', lw=2.5))
    ax.text(x_opt + 0.35, y_opt + 0.25, '∇f = [√3, 1]', fontsize=9, color='blue')
    
    t_dir = np.array([1, -np.sqrt(3)])
    t_dir = t_dir / np.linalg.norm(t_dir) * 0.4
    ax.plot([x_opt - t_dir[0], x_opt + t_dir[0]], 
            [y_opt - t_dir[1], y_opt + t_dir[1]], 'k--', lw=1, alpha=0.6)
    
    ax.set_xlim(-1.3, 1.5); ax.set_ylim(-0.5, 1.5)
    ax.set_aspect('equal')
    ax.set_title('最优 = 相切：f=1.25 等高线恰好触碰约束圆', fontsize=12, fontweight='bold',
                 fontproperties=CJK_FONT_NAME)
    ax.set_xlabel('x'); ax.set_ylabel('y'); ax.grid(True, alpha=0.2)
    
    return save(fig, 'fig_ch2_lagrange.png')

def fig_ch2_gradient_field():
    """图6: ∇f 在约束圆上的切线分量，P 点恰好为零"""
    fig = plt.figure(figsize=(7.5, 7.5))
    ax = fig.add_subplot(111)
    
    theta_fine = np.linspace(0, 2*np.pi, 300)
    ax.plot(np.cos(theta_fine), np.sin(theta_fine), 'r-', lw=1.5, alpha=0.4,
            label='constraint: $x^2+y^2=1$')
    
    # 8 等距点 + P 点（θ=π/6，不在等分点上）
    theta_pts = list(np.linspace(0, 2*np.pi, 8, endpoint=False)) + [np.pi/6]
    s = 0.45
    
    for th in theta_pts:
        px, py = np.cos(th), np.sin(th)
        dfx, dfy = 2*px, 1.0
        norm = np.sqrt(dfx**2 + dfy**2)
        
        tx, ty = -np.sin(th), np.cos(th)
        proj = dfx*tx + dfy*ty
        is_P = abs(th - np.pi/6) < 0.01
        
        # 蓝色实箭: 完整的 ∇f
        ax.annotate('', xy=(px + s*dfx/norm, py + s*dfy/norm),
                    xytext=(px, py),
                    arrowprops=dict(arrowstyle='->', color='steelblue', lw=2.2))
        
        # 红色虚箭: 切线分量（长度与蓝箭严格成比例）
        if abs(proj) > 0.02:
            comp_s = s * abs(proj) / norm
            sx = np.sign(proj) * tx
            sy = np.sign(proj) * ty
            ax.annotate('', xy=(px + comp_s*sx, py + comp_s*sy),
                        xytext=(px, py),
                        arrowprops=dict(arrowstyle='->', color='red', lw=1.5,
                                       ls='--', alpha=0.7))
        
        # f 值标注（内侧白底框，避开箭头）
        fval = px**2 + py
        if is_P:
            label_text = f'P  f={fval:.2f}'
        elif abs(fval - round(fval)) < 0.001:
            label_text = f'f={int(round(fval))}'
        else:
            label_text = f'f={fval:.2f}'
        ix, iy = -0.35 * np.cos(th), -0.35 * np.sin(th)
        color = 'darkred' if is_P else 'gray'
        fw = 'bold' if is_P else 'normal'
        ax.text(px + ix, py + iy, label_text, fontsize=7.5,
                color=color, ha='center', va='center', fontweight=fw,
                bbox=dict(boxstyle='round,pad=0.1', facecolor='white',
                          alpha=0.9, edgecolor='none'))
    
    # P 点标记
    x_opt, y_opt = np.sqrt(3)/2, 0.5
    ax.plot(x_opt, y_opt, 'ro', ms=8, zorder=5)
    
    # 图例（左下角空白区）
    ax.annotate('', xy=(-1.5, -0.7), xytext=(-1.9, -0.7),
                arrowprops=dict(arrowstyle='->', color='steelblue', lw=2.2))
    ax.text(-1.45, -0.7, r'$\nabla f = [2x, 1]$ (full)', fontsize=9,
            color='steelblue', va='center')
    
    ax.annotate('', xy=(-1.5, -1.0), xytext=(-1.9, -1.0),
                arrowprops=dict(arrowstyle='->', color='red', lw=1.5, ls='--', alpha=0.7))
    ax.text(-1.45, -1.0, r'tangent component ($\nabla f \cdot t$)', fontsize=9,
            color='red', va='center', alpha=0.8)
    
    ax.set_xlim(-2.1, 1.7); ax.set_ylim(-1.5, 1.3)
    ax.set_aspect('equal')
    ax.set_title(r'Tangent component of $\nabla f$ vanishes at P and $(0,\pm 1)$',
                 fontsize=12, fontweight='bold')
    ax.set_xlabel('x'); ax.set_ylabel('y')
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.2)
    
    return save(fig, 'fig_ch2_gradient_field.png')

def fig_ch2_complementary_slackness():
    """图7: 互补松弛性——为什么最优解必须在边界上"""
    fig = plt.figure(figsize=(6.5, 6.5))
    ax = fig.add_subplot(111)
    
    theta_fine = np.linspace(0, 2*np.pi, 300)
    
    # 禁区：整个 axes 背景填红，再挖掉可行圆
    ax.set_xlim(-1.8, 1.6); ax.set_ylim(-1.5, 1.4)
    ax.set_aspect('equal')
    
    # 用 axes 坐标画一个铺满背景的红色矩形
    ax.axhspan(-1.5, 1.4, xmin=0, xmax=1, color='red', alpha=0.08, zorder=0)
    ax.text(1.2, 1.1, '禁区\ng(x,y)>0', fontsize=9, color='red', alpha=0.7, ha='center')
    ax.text(-1.35, 1.1, '禁区', fontsize=9, color='red', alpha=0.7, ha='center')
    ax.text(0, -1.35, '禁区', fontsize=9, color='red', alpha=0.7, ha='center')
    
    # 可行域：圆内填蓝（盖住红底）
    ax.fill(np.cos(theta_fine), np.sin(theta_fine), alpha=0.15, color='lightblue',
            label='可行域 g≤0', zorder=1)
    
    # 边界
    ax.plot(np.cos(theta_fine), np.sin(theta_fine), 'r-', lw=2,
            label='边界 g=0', zorder=2)
    
    # 圆心：λ=0 假设导致矛盾
    ax.plot(0, 0, 'bs', ms=10, zorder=5)
    ax.text(0.1, -0.2, "(0,0)\n假设 λ=0\n→ ∂L/∂y=1=0\n→ 矛盾", 
            fontsize=8.5, color='blue', va='top',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.9))
    
    # P 点：边界上最优解
    x_opt = np.sqrt(3)/2
    y_opt = 0.5
    ax.plot(x_opt, y_opt, 'ro', ms=10, zorder=5)
    ax.text(x_opt-0.85, y_opt+0.1, "P 在边界上\nλ=-1 ≠ 0\n→ 约束有效",
            fontsize=8.5, color='darkred',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
    
    ax.set_title('互补松弛性：内部不可能，最优解必须在边界', fontsize=12, fontweight='bold')
    ax.set_xlabel('x'); ax.set_ylabel('y')
    ax.legend(loc='lower right', fontsize=9); ax.grid(True, alpha=0.2)
    
    return save(fig, 'fig_ch2_complementary_slackness.png')

# ============================================================
# Ch3 - 3张图
# ============================================================

def fig_ch3_entropy_softmax():
    """图8: 熵函数与Softmax温度"""
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    
    # 左：熵函数
    ax = axes[0]
    p = np.linspace(0.001, 0.999, 200)
    H = -(p * np.log(p) + (1-p) * np.log(1-p))
    ax.plot(p, H, 'b-', lw=2)
    ax.axvline(x=0.5, color='red', ls='--', alpha=0.7)
    ax.plot(0.5, np.log(2), 'ro', ms=10, zorder=5)
    ax.text(0.55, 0.65, f'H(0.5) = ln(2)\n≈ 0.693\n(maximum)', fontsize=9, color='red')
    ax.set_xlabel('p'); ax.set_ylabel('H(p)')
    ax.set_title('Entropy H(p) = -pln(p)-(1-p)ln(1-p)', fontsize=11, fontweight='bold')
    ax.set_xlim(0, 1); ax.set_ylim(-0.1, 0.8); ax.grid(True, alpha=0.3)
    
    # 中：不同温度下的Softmax输出（分组柱状图，不重叠）
    ax = axes[1]
    z = np.array([2.0, 1.0, 0.1])
    temps = [(2.0, 'steelblue', 'T=2 (平坦)'), (1.0, 'cornflowerblue', 'T=1 (标准)'), (0.5, 'navy', 'T=0.5 (尖锐)')]
    n = len(temps)
    bar_w = 0.25
    x_base = np.arange(3)
    for i, (T, color, label) in enumerate(temps):
        exp_z = np.exp(z / T)
        p_t = exp_z / exp_z.sum()
        offset = (i - (n-1)/2) * bar_w
        bars = ax.bar(x_base + offset, p_t, color=color, alpha=0.85, label=label, width=bar_w)
        for j, bar in enumerate(bars):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.015,
                    f'{p_t[j]:.2f}', ha='center', va='bottom', fontsize=7, color=color)
    ax.set_xlabel('类别'); ax.set_ylabel('概率')
    ax.set_title('Softmax: 同一分数在不同温度下的输出', fontsize=11, fontweight='bold')
    ax.set_xticks(x_base); ax.set_xticklabels(['类别1\n(z=2.0)', '类别2\n(z=1.0)', '类别3\n(z=0.1)'])
    ax.set_ylim(0, 1.0)
    ax.legend(fontsize=8); ax.grid(True, alpha=0.2, axis='y')
    
    # 右：温度T=0.5（自信）
    ax = axes[2]
    T_vals = [0.5, 0.7, 1.0, 1.5, 2.0]
    p1_vals = []
    for T in T_vals:
        exp_z = np.exp(z / T)
        p_t = exp_z / exp_z.sum()
        p1_vals.append(p_t[0])
    ax.plot(T_vals, p1_vals, 'bo-', lw=2, ms=8)
    ax.axhline(y=1/3, color='gray', ls='--', alpha=0.5, label='uniform = 1/3')
    ax.set_xlabel('temperature T'); ax.set_ylabel('$p_1$ (prob of class 1)')
    ax.set_title('Class 1 probability vs temperature', fontsize=11, fontweight='bold')
    ax.legend(); ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return save(fig, 'fig_ch3_entropy_softmax.png')

def fig_ch3_crossentropy():
    """图9: 交叉熵损失"""
    fig, ax = plt.subplots(figsize=(8, 5))
    
    q = np.linspace(0.001, 1.0, 200)
    ce = -np.log(q)
    ax.plot(q, ce, 'b-', lw=2)
    ax.axhline(y=0, color='gray', ls='-', alpha=0.3)
    
    # 标记关键点
    points = [(0.99, -np.log(0.99), 'good\np=0.99', 'green'),
              (0.659, -np.log(0.659), 'ok\np=0.659', 'orange'),
              (0.10, -np.log(0.10), 'bad\np=0.10', 'red'),
              (0.01, -np.log(0.01), 'terrible\np=0.01', 'darkred')]
    
    for qv, cv, txt, color in points:
        ax.plot(qv, cv, 'o', color=color, ms=10, zorder=5)
        ax.text(qv, cv + 0.3, txt, fontsize=9, ha='center', color=color, fontweight='bold')
    
    ax.fill_between(q, 0, ce, alpha=0.1, color='blue')
    ax.set_xlabel('predicted probability $p_1$', fontsize=12)
    ax.set_ylabel('cross entropy $H = -\\ln(p_1)$', fontsize=12)
    ax.set_title('Cross-Entropy: confident mistakes are punished heavily', fontsize=13, fontweight='bold')
    ax.set_xlim(0, 1); ax.set_ylim(-0.5, 5.5); ax.grid(True, alpha=0.3)
    
    return save(fig, 'fig_ch3_crossentropy.png')

def fig_ch3_diffusion_demo():
    """图10: 扩散模型前向加噪与反向去噪数值演示 (N(2,1))"""
    np.random.seed(42)
    x0 = 2.0
    eta = 0.2
    n_fwd = 20
    n_rev = 40

    # Forward: x_t = sqrt(alpha_bar_t)*x0 + sqrt(1-alpha_bar_t)*eps
    # alpha_bar decreases from 1.0 to 0.01 over n_fwd steps
    fwd_x = [x0]
    fwd_t = [0]
    for t in range(1, n_fwd+1):
        alpha_bar = max(0.01, 1.0 - (t/n_fwd)**2 * 0.99)
        eps = np.random.randn()
        xt = np.sqrt(alpha_bar) * x0 + np.sqrt(1-alpha_bar) * eps
        fwd_x.append(xt)
        fwd_t.append(t)

    # Reverse Langevin: x_{t-1} = x_t + eta/2 * score(x_t) + sqrt(eta)*noise
    # score = 2 - x for N(2,1)
    rev_x = [fwd_x[-1]]
    rev_t = [0]
    x = fwd_x[-1]
    for t in range(1, n_rev+1):
        score = 2.0 - x
        noise = np.random.randn() * np.sqrt(eta)
        x = x + eta/2 * score + noise
        rev_x.append(x)
        rev_t.append(t)

    fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))

    # Left: forward process
    ax = axes[0]
    ax.plot(fwd_t, fwd_x, 'b-o', lw=2, ms=4, label='$x_t$')
    ax.axhline(y=x0, color='green', ls='--', lw=1.5, alpha=0.7, label=f'data peak $x_0={x0}$')
    ax.axhline(y=0, color='gray', ls=':', alpha=0.4)
    ax.annotate('signal\ngradually\noverwhelmed\nby noise',
                (n_fwd*0.7, fwd_x[int(n_fwd*0.7)]),
                textcoords='offset points', xytext=(15, 20), fontsize=9,
                arrowprops=dict(arrowstyle='->', color='blue'))
    ax.set_xlabel('forward step $t$', fontsize=12)
    ax.set_ylabel('$x_t$', fontsize=12)
    ax.set_title('Forward: add noise (data $\\to$ noise)', fontsize=13, fontweight='bold')
    ax.legend(loc='upper right'); ax.set_xlim(0, n_fwd); ax.grid(True, alpha=0.3)

    # Right: reverse process
    ax = axes[1]
    ax.plot(rev_t, rev_x, 'g-o', lw=2, ms=3, label='$x_t$')
    ax.axhline(y=x0, color='green', ls='--', lw=1.5, alpha=0.7, label=f'data peak $x_0={x0}$')
    ax.axhline(y=0, color='gray', ls=':', alpha=0.4)
    ax.annotate('Langevin samples\nfluctuate around\n$\\mu=2$',
                (n_rev*0.75, rev_x[int(n_rev*0.75)]),
                textcoords='offset points', xytext=(10, 20), fontsize=9,
                arrowprops=dict(arrowstyle='->', color='green'))
    ax.set_xlabel('reverse step $t$', fontsize=12)
    ax.set_ylabel('$x_t$', fontsize=12)
    ax.set_title('Reverse: denoise via score $\\nabla\\log p(x) = 2-x$', fontsize=13, fontweight='bold')
    ax.legend(loc='upper right'); ax.set_xlim(0, n_rev); ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return save(fig, 'fig_ch3_diffusion_demo.png')

# ============================================================
# Ch4 - 4张图
# ============================================================

def fig_ch4_backprop():
    """图11: MLP计算图与反向传播"""
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_xlim(0, 10); ax.set_ylim(0, 4)
    ax.axis('off')
    
    # 节点位置
    nodes = {
        'x': (1, 2), 'W': (2.5, 3.5), 'b': (2.5, 0.5),
        'z': (4, 2), 'ReLU': (5.5, 2), 'h': (7, 2),
        'V': (5.5, 3.5), 'c': (5.5, 0.5),
        'y_hat': (8.5, 2), 'L': (9.5, 2)
    }
    
    # 画前向传播箭头（蓝色）
    forward_edges = [('x', 'z'), ('W', 'z'), ('b', 'z'), ('z', 'ReLU'), ('ReLU', 'h'), 
                     ('h', 'y_hat'), ('V', 'y_hat'), ('c', 'y_hat'), ('y_hat', 'L')]
    for src, dst in forward_edges:
        x1, y1 = nodes[src]; x2, y2 = nodes[dst]
        ax.annotate('', xy=(x2-0.3, y2), xytext=(x1+0.3, y1),
                    arrowprops=dict(arrowstyle='->', color='blue', lw=1.5))
    
    # 画反向传播箭头（红色虚线）
    backward_edges = [('L', 'y_hat'), ('y_hat', 'h'), ('y_hat', 'V'), ('y_hat', 'c'),
                      ('h', 'ReLU'), ('ReLU', 'z'), ('z', 'x'), ('z', 'W'), ('z', 'b')]
    for src, dst in backward_edges:
        x1, y1 = nodes[src]; x2, y2 = nodes[dst]
        offset = 0.15
        ax.annotate('', xy=(x2+offset, y2+offset), xytext=(x1-offset, y1-offset),
                    arrowprops=dict(arrowstyle='->', color='red', lw=1, ls='--', alpha=0.6))
    
    # 画节点
    for name, (x, y) in nodes.items():
        if name in ['x', 'h']:
            ax.plot(x, y, 'o', ms=20, color='lightblue', zorder=5)
        elif name == 'L':
            ax.plot(x, y, 'o', ms=20, color='lightcoral', zorder=5)
        else:
            ax.plot(x, y, 's', ms=15, color='lightgray', zorder=5)
        ax.text(x, y, name, ha='center', va='center', fontsize=11, fontweight='bold', zorder=6)
    
    # 公式标签
    ax.text(4, 2.8, r'$z=Wx+b$', fontsize=10, ha='center', color='blue')
    ax.text(5.5, 2.8, r'$h=\max(0,z)$', fontsize=10, ha='center', color='blue')
    ax.text(8.5, 2.8, r'$\hat{y}=Vh+c$', fontsize=10, ha='center', color='blue')
    ax.text(9.5, 1.2, r'$L=\frac{1}{2}(\hat{y}-y)^2$', fontsize=10, ha='center', color='red')
    
    ax.text(5, 3.8, 'Forward: blue solid arrows', fontsize=10, color='blue', fontweight='bold')
    ax.text(5, 0.1, 'Backward: red dashed arrows (gradients)', fontsize=10, color='red', fontweight='bold')
    
    ax.set_title('MLP Forward & Backward Propagation', fontsize=14, fontweight='bold')
    return save(fig, 'fig_ch4_backprop.png')

def fig_ch4_activations():
    """图14: 激活函数形状对比"""
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.5))
    x = np.linspace(-5, 5, 300)
    
    # ReLU
    ax = axes[0]
    ax.plot(x, np.maximum(0, x), 'b-', lw=2)
    ax.fill_between(x, 0, np.maximum(0, x), alpha=0.1, color='blue')
    ax.axhline(y=0, color='k', lw=0.5); ax.axvline(x=0, color='k', lw=0.5)
    ax.text(-3.5, 3, 'dead zone\n(grad=0)', fontsize=8, color='red', alpha=0.7)
    ax.text(1.5, 2, 'pass through\n(grad=1)', fontsize=8, color='blue', alpha=0.7)
    ax.set_title('ReLU', fontsize=13, fontweight='bold')
    ax.set_xlabel('z'); ax.set_ylabel('output')
    ax.set_xlim(-5,5); ax.set_ylim(-1,5); ax.grid(True, alpha=0.2)
    
    # Sigmoid
    ax = axes[1]
    ax.plot(x, 1/(1+np.exp(-x)), 'g-', lw=2)
    ax.fill_between(x, 0, 1/(1+np.exp(-x)), alpha=0.1, color='green')
    ax.axhline(y=0, color='k', lw=0.5); ax.axvline(x=0, color='k', lw=0.5)
    ax.text(2.5, 0.9, 'saturate\n(grad~0)', fontsize=8, color='red', alpha=0.7)
    ax.text(0.3, 0.27, 'max grad=0.25', fontsize=8, color='green')
    ax.set_title('Sigmoid', fontsize=13, fontweight='bold')
    ax.set_xlabel('z'); ax.set_ylabel('output')
    ax.set_xlim(-5,5); ax.set_ylim(-0.1,1.1); ax.grid(True, alpha=0.2)
    
    # Swish
    ax = axes[2]
    ax.plot(x, x * (1/(1+np.exp(-x))), 'm-', lw=2)
    ax.axhline(y=0, color='k', lw=0.5); ax.axvline(x=0, color='k', lw=0.5)
    ax.text(-4, 1.5, 'smooth for\nnegative input', fontsize=8, color='magenta', alpha=0.7)
    ax.text(1.5, 4, 'approx identity\nfor large z', fontsize=8, color='magenta', alpha=0.7)
    ax.set_title('Swish (SwiGLU core)', fontsize=13, fontweight='bold')
    ax.set_xlabel('z'); ax.set_ylabel('output')
    ax.set_xlim(-5,5); ax.set_ylim(-1,5); ax.grid(True, alpha=0.2)
    
    # GELU
    ax = axes[3]
    ax.plot(x, x * (1+np.tanh(np.sqrt(2/np.pi)*(x+0.044715*x**3)))/2, 'orange', lw=2)
    ax.axhline(y=0, color='k', lw=0.5); ax.axvline(x=0, color='k', lw=0.5)
    ax.text(-3, 2, 'smooth,\nnon-monotonic\n"bump"', fontsize=8, color='orange')
    ax.set_title('GELU (GPT/BERT)', fontsize=13, fontweight='bold')
    ax.set_xlabel('z'); ax.set_ylabel('output')
    ax.set_xlim(-5,5); ax.set_ylim(-1,5); ax.grid(True, alpha=0.2)
    
    plt.suptitle('Activation Functions: from hard-cut to smooth gating', fontsize=14, y=1.05)
    return save(fig, 'fig_ch4_activations.png')

def fig_ch4_swiglu():
    """图13: SwiGLU结构示意图"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Left: SwiGLU data flow diagram
    ax = axes[0]
    ax.set_xlim(0, 10); ax.set_ylim(0, 7.9); ax.axis('off')
    ax.set_title('SwiGLU = Swish($xW_1$) $\\odot$ ($xW_2$)', fontsize=13, fontweight='bold')

    # Boxes
    box_props = dict(boxstyle='round,pad=0.4', facecolor='lightblue', edgecolor='blue', lw=1.5)
    gate_props = dict(boxstyle='round,pad=0.4', facecolor='lightyellow', edgecolor='orange', lw=1.5)
    out_props = dict(boxstyle='round,pad=0.4', facecolor='lightgreen', edgecolor='green', lw=1.5)

    ax.text(1, 5.5, '$x$', fontsize=14, ha='center', va='center')
    ax.annotate('', xy=(2, 5.5), xytext=(1.5, 5.5), arrowprops=dict(arrowstyle='->', lw=1.5))

    # Split into two branches
    ax.text(3.5, 6.5, '$xW_1$', fontsize=12, ha='center', va='center', bbox=gate_props)
    ax.text(3.5, 4.5, '$xW_2$', fontsize=12, ha='center', va='center', bbox=box_props)

    ax.annotate('', xy=(3, 6.5), xytext=(2, 5.7), arrowprops=dict(arrowstyle='->', lw=1.5))
    ax.annotate('', xy=(3, 4.5), xytext=(2, 5.3), arrowprops=dict(arrowstyle='->', lw=1.5))

    # Swish on upper branch
    ax.text(5.5, 6.5, 'Swish', fontsize=11, ha='center', va='center', bbox=gate_props)
    ax.annotate('', xy=(5, 6.5), xytext=(4.2, 6.5), arrowprops=dict(arrowstyle='->', lw=1.5))

    # Swish output
    ax.text(7, 6.5, 'Swish($xW_1$)', fontsize=10, ha='center', va='center', bbox=gate_props)
    ax.annotate('', xy=(6.5, 6.5), xytext=(6.2, 6.5), arrowprops=dict(arrowstyle='->', lw=1.5))

    # Element-wise multiply
    ax.text(7, 4.5, '$xW_2$', fontsize=12, ha='center', va='center', bbox=box_props)
    ax.annotate('', xy=(6.5, 4.5), xytext=(4.2, 4.5), arrowprops=dict(arrowstyle='->', lw=1.5))

    # Multiply node
    ax.plot(8, 5.5, 'o', ms=15, color='red', zorder=5)
    ax.text(8, 5.5, '$\\odot$', fontsize=12, ha='center', va='center', color='white', fontweight='bold', zorder=6)
    ax.annotate('', xy=(8, 6.0), xytext=(7.8, 6.5), arrowprops=dict(arrowstyle='->', lw=1.5))
    ax.annotate('', xy=(8, 5.0), xytext=(7.8, 4.5), arrowprops=dict(arrowstyle='->', lw=1.5))

    # Output
    ax.text(9.2, 5.5, 'output', fontsize=11, ha='center', va='center', bbox=out_props)
    ax.annotate('', xy=(8.8, 5.5), xytext=(8.3, 5.5), arrowprops=dict(arrowstyle='->', lw=1.5))

    # Labels for branches
    ax.text(5.5, 7.15, 'gate (learned switch)', fontsize=8, ha='center', color='orange', style='italic')
    ax.text(5.5, 3.8, 'value (linear transform)', fontsize=8, ha='center', color='blue', style='italic')

    # Right: Swish vs ReLU comparison in gating context
    ax = axes[1]
    x = np.linspace(-4, 4, 300)
    swish = x * (1/(1+np.exp(-x)))
    relu = np.maximum(0, x)

    ax.plot(x, swish, 'm-', lw=2, label='Swish: $x \\cdot \\sigma(x)$')
    ax.plot(x, relu, 'b--', lw=2, label='ReLU: $\\max(0, x)$', alpha=0.6)
    ax.fill_between(x, 0, swish, alpha=0.08, color='magenta')
    ax.axhline(y=0, color='k', lw=0.5); ax.axvline(x=0, color='k', lw=0.5)

    # Annotate key difference
    ax.annotate('negative values\npreserved (not killed)',
                (-2, swish[np.argmin(np.abs(x+2))]),
                textcoords='offset points', xytext=(-60, 30), fontsize=9, color='magenta',
                arrowprops=dict(arrowstyle='->', color='magenta'))
    ax.annotate('hard cutoff\nat $x=0$',
                (0.5, 0.5),
                textcoords='offset points', xytext=(30, -30), fontsize=9, color='blue',
                arrowprops=dict(arrowstyle='->', color='blue'))

    ax.set_xlabel('$z$', fontsize=12)
    ax.set_ylabel('output', fontsize=12)
    ax.set_title('Swish vs ReLU: smooth gating vs hard cutoff', fontsize=13, fontweight='bold')
    ax.legend(loc='upper left', fontsize=10); ax.set_xlim(-4, 4); ax.set_ylim(-2, 5)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return save(fig, 'fig_ch4_swiglu.png')

def fig_ch4_gradient_decay():
    """图12: 梯度随深度衰减"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    
    # 左：衰减曲线
    ax = axes[0]
    depths = np.arange(1, 51)
    ax.semilogy(depths, 0.25**depths, 'g-', lw=2, label='Sigmoid (max grad=0.25)')
    ax.semilogy(depths, 0.42**depths, 'c--', lw=2, label='Tanh (avg grad≈0.42)')
    ax.semilogy(depths, np.ones_like(depths), 'b-', lw=2, label='ReLU (grad=1, no decay)', alpha=0.5)
    ax.axhline(y=1e-6, color='red', ls=':', lw=1.5, alpha=0.7)
    ax.text(25, 2e-6, '1e-6 (effectively zero)', fontsize=9, color='red')
    ax.annotate(f'Sigmoid at 10 layers:\n0.25^10 = {0.25**10:.2e}', 
                xy=(10, 0.25**10), xytext=(18, 1e-4),
                fontsize=9, arrowprops=dict(arrowstyle='->', color='green'),
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
    ax.set_title('Gradient decay vs network depth', fontsize=13, fontweight='bold')
    ax.set_xlabel('network depth (number of layers)')
    ax.set_ylabel('gradient magnitude (log scale)')
    ax.set_xlim(1,50); ax.set_ylim(1e-20, 2)
    ax.legend(loc='upper right'); ax.grid(True, alpha=0.3, which='both')
    
    # 右：导数形状
    ax = axes[1]
    z = np.linspace(-4, 4, 200)
    relu_d = np.where(z > 0, 1, 0)
    sigmoid_d = (1/(1+np.exp(-z))) * (1 - 1/(1+np.exp(-z)))
    ax.plot(z, relu_d, 'b-', lw=2.5, label="ReLU'(z)", alpha=0.8)
    ax.plot(z, sigmoid_d, 'g-', lw=2.5, label="Sigmoid'(z)", alpha=0.8)
    ax.axhline(y=0.25, color='green', ls=':', alpha=0.5)
    ax.text(0.3, 0.27, 'max=0.25', fontsize=9, color='green')
    ax.text(-3.5, 0.5, "grad=0\n(dead zone)", fontsize=9, color='blue')
    ax.text(0.5, 0.7, "grad=1\n(full pass)", fontsize=9, color='blue')
    ax.set_title("Derivative comparison: why ReLU wins", fontsize=13, fontweight='bold')
    ax.set_xlabel('z (pre-activation)'); ax.set_ylabel("gradient (derivative)")
    ax.set_xlim(-4,4); ax.set_ylim(-0.1,1.2)
    ax.legend(loc='upper right'); ax.grid(True, alpha=0.2)
    
    plt.tight_layout()
    return save(fig, 'fig_ch4_gradient_decay.png')

# ============================================================
# Ch5 — 4张图
# ============================================================

def fig_ch5_attention_heatmap():
    """图15: Attention权重热力图"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    A = np.array([[0.1344, 0.2805, 0.5851],
                  [0.0203, 0.1312, 0.8485],
                  [0.0024, 0.0474, 0.9502]])
    
    # 完整热力图
    ax = axes[0]
    im = ax.imshow(A, cmap='YlOrRd', aspect='auto')
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f'{A[i,j]:.3f}', ha='center', va='center', 
                   fontsize=12, fontweight='bold', color='white' if A[i,j] > 0.5 else 'black')
    ax.set_xticks(range(3)); ax.set_yticks(range(3))
    ax.set_xticklabels(['Key1', 'Key2', 'Key3']); ax.set_yticklabels(['Query1', 'Query2', 'Query3'])
    ax.set_title('Attention weights A (full)', fontsize=12, fontweight='bold')
    plt.colorbar(im, ax=ax)
    
    # 因果mask（重新归一化，每行和为1）
    ax = axes[1]
    A_causal = np.zeros_like(A)
    for i in range(3):
        row = A[i, :i+1]
        A_causal[i, :i+1] = row / row.sum()
    im = ax.imshow(A_causal, cmap='YlOrRd', aspect='auto')
    for i in range(3):
        for j in range(3):
            if j <= i:
                ax.text(j, i, f'{A_causal[i,j]:.3f}', ha='center', va='center',
                       fontsize=12, fontweight='bold', color='white' if A_causal[i,j] > 0.5 else 'black')
            else:
                ax.text(j, i, '—', ha='center', va='center', fontsize=12, color='gray')
    ax.set_xticks(range(3)); ax.set_yticks(range(3))
    ax.set_xticklabels(['Key1', 'Key2', 'Key3']); ax.set_yticklabels(['Query1', 'Query2', 'Query3'])
    ax.set_title('Attention weights A (causal mask)', fontsize=12, fontweight='bold')
    plt.colorbar(im, ax=ax)
    
    plt.tight_layout()
    return save(fig, 'fig_ch5_attention_heatmap.png')

def fig_ch5_attention_qkv():
    """图16: Q/K/V投影与加权输出（含注意力权重矩阵A）"""
    fig, axes = plt.subplots(1, 5, figsize=(22, 4.5))
    
    Q = np.array([[0.4, 0.6], [1.2, 1.4], [2.0, 2.2]])
    K = np.array([[0.4, 0.7], [1.2, 1.9], [2.0, 3.1]])
    V = np.array([[0.6, 0.4], [1.4, 1.2], [2.2, 2.0]])
    
    for ax, M, title in zip(axes[:3], [Q, K, V], ['Q (Query)', 'K (Key)', 'V (Value)']):
        im = ax.imshow(M, cmap='Blues', aspect='auto')
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                ax.text(j, i, f'{M[i,j]:.1f}', ha='center', va='center', fontsize=11)
        ax.set_xticks(range(2)); ax.set_yticks(range(3))
        ax.set_xticklabels(['dim1', 'dim2']); ax.set_yticklabels(['token1', 'token2', 'token3'])
        ax.set_title(f'{title}\n{M.shape}', fontsize=12, fontweight='bold')
        plt.colorbar(im, ax=ax)
    
    # 第4个子图：注意力权重 A = softmax(QK^T/√d_k)
    d_k = Q.shape[1]
    scores = Q @ K.T / np.sqrt(d_k)
    exp_s = np.exp(scores - scores.max(axis=1, keepdims=True))
    A_weights = exp_s / exp_s.sum(axis=1, keepdims=True)
    
    ax = axes[3]
    im = ax.imshow(A_weights, cmap='Oranges', aspect='auto')
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f'{A_weights[i,j]:.2f}', ha='center', va='center', fontsize=11,
                   fontweight='bold', color='white' if A_weights[i,j] > 0.5 else 'black')
    ax.set_xticks(range(3)); ax.set_yticks(range(3))
    ax.set_xticklabels(['Key1', 'Key2', 'Key3']); ax.set_yticklabels(['Qry1', 'Qry2', 'Qry3'])
    ax.set_title('A = softmax(QK$^T$/√d)\n(3,3) 权重', fontsize=12, fontweight='bold')
    plt.colorbar(im, ax=ax)
    
    # 第5个子图：输出 O = A @ V
    O = A_weights @ V
    ax = axes[4]
    im = ax.imshow(O, cmap='Purples', aspect='auto')
    for i in range(O.shape[0]):
        for j in range(O.shape[1]):
            ax.text(j, i, f'{O[i,j]:.2f}', ha='center', va='center', fontsize=11)
    ax.set_xticks(range(2)); ax.set_yticks(range(3))
    ax.set_xticklabels(['dim1', 'dim2']); ax.set_yticklabels(['token1', 'token2', 'token3'])
    ax.set_title('O = A·V\n(3,2) 输出', fontsize=12, fontweight='bold')
    plt.colorbar(im, ax=ax)
    
    plt.suptitle('Q/K → 注意力权重 A → 加权求和 V → 输出 O', fontsize=13, y=1.02, fontproperties=CJK_FONT_NAME)
    plt.tight_layout()
    return save(fig, 'fig_ch5_attention_qkv.png')

def fig_ch5_llm_pipeline():
    """图18: LLM Pipeline -- from text to text"""
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    import matplotlib.patheffects as pe

    fig, ax = plt.subplots(figsize=(15, 9))
    ax.set_xlim(-0.5, 15)
    ax.set_ylim(-1, 10.5)
    ax.axis('off')

    # ── palette: 3 colors only ──
    BLUE   = '#4A90D9'
    BLUE_F = '#D6E8F7'
    AMBER  = '#E89B3F'
    AMBER_F = '#FCE8D0'
    GREEN  = '#5BAA5B'

    # ── helpers ──
    def rbox(cx, cy, w, h, label, face, edge, fs=10):
        box = FancyBboxPatch((cx - w/2, cy - h/2), w, h,
                             boxstyle='round,pad=0.08', facecolor=face,
                             edgecolor=edge, lw=2, zorder=5)
        ax.add_patch(box)
        ax.text(cx, cy, label, ha='center', va='center', fontsize=fs,
                fontweight='bold', color='#222', zorder=6, linespacing=1.4)

    def arrow(x1, y1, x2, y2, color=BLUE, lw=2.0, ls='-', rad=0):
        cs = f'arc3,rad={rad}' if rad else 'arc3,rad=0'
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                                    ls=ls, connectionstyle=cs,
                                    shrinkA=0, shrinkB=0))

    # ════════════════ Top: full pipeline ════════════════
    # Title at very top; green arc goes between title and boxes
    ax.text(7.25, 10.0, 'LLM Pipeline: from text to text', fontsize=15,
            fontweight='bold', ha='center', va='center', color='#222')

    nodes = [
        (0.6,  'Input text\n"today I"',    BLUE_F,  'r'),
        (2.8,  'Embedding\nlookup',        BLUE_F,  'r'),
        (5.4,  'N x Transformer\nBlock',   AMBER_F, 'r'),
        (8.4,  'LM Head\nlinear map',      BLUE_F,  'r'),
        (10.6, 'Softmax\nprobability',     BLUE_F,  'r'),
        (12.8, 'Sample\nnext token',       BLUE_F,  'r'),
    ]
    BW, BH = 1.7, 1.15  # uniform box size
    for x, lbl, fc, _ in nodes:
        rbox(x, 8.3, BW, BH, lbl, fc, '#555', fs=9.5)

    # forward arrows (uniform gap)
    for i in range(len(nodes) - 1):
        x1 = nodes[i][0] + BW / 2
        x2 = nodes[i+1][0] - BW / 2
        arrow(x1, 8.3, x2, 8.3, color=BLUE, lw=2)

    # autoregressive loop — shallow arc in the gap between title (y=10) and boxes (y=8.3)
    arrow(12.8, 8.9, 0.6, 8.9, color=GREEN, lw=2, ls='--', rad=0.12)
    ax.text(6.7, 9.35, 'autoregressive loop', ha='center', va='center',
            fontsize=9, color=GREEN, fontweight='bold', style='italic')

    # ════════════════ Bottom: Block detail ════════════════
    # dashed guide from "N x Transformer Block" box down to subtitle
    ax.annotate('', xy=(5.4, 5.85), xytext=(5.4, 7.72),
                arrowprops=dict(arrowstyle='->', color='#AAA', lw=1.5,
                                ls=':', connectionstyle='arc3,rad=0'))
    ax.text(5.65, 6.8, 'expand', fontsize=8, color='#555', va='center',
            style='italic')

    ax.text(7.25, 5.8, 'One Transformer Block (repeated N times)', fontsize=12,
            fontweight='bold', ha='center', va='center', color='#333')

    block = [
        (0.6,  'h',                BLUE_F,  'c'),
        (2.6,  'RMSNorm\nscale',     '#EEEEEE', 'r'),
        (4.8,  'Attention\ndynamic', AMBER_F, 'r'),
        (7.0,  'RMSNorm\nscale',     '#EEEEEE', 'r'),
        (9.2,  'FFN\nstatic\nknowledge', AMBER_F, 'r'),
        (11.2, 'h_out',             BLUE_F,  'c'),
    ]
    SBW, SBH = 1.55, 1.0  # uniform sub-box
    SC_R = 0.42           # circle radius
    for x, lbl, fc, shape in block:
        if shape == 'c':
            circ = plt.Circle((x, 4.2), SC_R, facecolor=fc, edgecolor='#555',
                              lw=2, zorder=5)
            ax.add_patch(circ)
            ax.text(x, 4.2, lbl, ha='center', va='center', fontsize=9,
                    fontweight='bold', color='#222', zorder=6)
        else:
            rbox(x, 4.2, SBW, SBH, lbl, fc, '#555', fs=8.5)

    # forward arrows
    for i in range(len(block) - 1):
        x1 = block[i][0] + (SC_R if block[i][3] == 'c' else SBW / 2)
        x2 = block[i+1][0] - (SC_R if block[i+1][3] == 'c' else SBW / 2)
        arrow(x1, 4.2, x2, 4.2, color=BLUE, lw=1.5)

    # residual: h bypasses RMSNorm+Attention, merges after Attention output
    arrow(0.6, 4.65, 5.7, 4.65, color=AMBER, lw=1.5, ls='--', rad=-0.3)
    ax.text(2.8, 5.15, '+', fontsize=14, color=AMBER, ha='center',
            fontweight='bold')

    # residual: h' bypasses RMSNorm+FFN, merges after FFN output
    arrow(5.7, 4.65, 10.1, 4.65, color=AMBER, lw=1.5, ls='--', rad=-0.3)
    ax.text(7.9, 5.15, '+', fontsize=14, color=AMBER, ha='center',
            fontweight='bold')

    ax.text(3.0, 5.5, 'residual', fontsize=8, color=AMBER, ha='center',
            fontweight='bold', style='italic')
    ax.text(8.1, 5.5, 'residual', fontsize=8, color=AMBER, ha='center',
            fontweight='bold', style='italic')

    # ════════════════ Formula row ════════════════
    y_f = 2.0
    formulas = [
        (0.6,  r'$x = \mathrm{Embed}[i]$', 'lookup', BLUE),
        (4.8,  r'$\mathrm{Attn}(\mathrm{RMSNorm}(h))+h$',   'Pre-Norm + residual', AMBER),
        (8.5,  r'$\mathrm{FFN}(\mathrm{RMSNorm}(h\,'')) + h''$', 'Pre-Norm + residual', AMBER),
        (12.3, r'$p = \mathrm{Softmax}(h_f W_{hd})$', 'probability', BLUE),
    ]
    for x, formula, note, color in formulas:
        ax.text(x, y_f + 0.25, formula, fontsize=9, ha='center', va='center',
                color=color)
        ax.text(x, y_f - 0.25, note, fontsize=8, ha='center', va='center',
                color='#555', style='italic')

    # ── legend (bottom-right, compact) ──
    lx, ly = 12.8, 0.35
    ax.plot([lx - 0.4, lx], [ly + 0.5, ly + 0.5], color=BLUE, lw=2)
    ax.text(lx + 0.1, ly + 0.5, 'forward', fontsize=8, va='center', color='#444')
    ax.plot([lx - 0.4, lx], [ly + 0.2, ly + 0.2], color=GREEN, lw=2, ls='--')
    ax.text(lx + 0.1, ly + 0.2, 'autoregressive', fontsize=8, va='center', color='#444')
    ax.plot([lx - 0.4, lx], [ly - 0.1, ly - 0.1], color=AMBER, lw=1.5, ls='--')
    ax.text(lx + 0.1, ly - 0.1, 'residual', fontsize=8, va='center', color='#444')

    plt.tight_layout()
    return save(fig, 'fig_ch5_llm_pipeline.png')

def fig_ch5_rope():
    """图17: RoPE旋转位置编码"""
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))

    thetas = [1.0, 0.1, 0.01, 0.001]
    labels = ['pair 0 (θ=1.0)', 'pair 1 (θ=0.1)', 'pair 2 (θ=0.01)', 'pair 3 (θ=0.001)']
    colors_p = ['navy', 'cornflowerblue', 'steelblue', 'lightblue']

    # 左: 多频率灵敏区铺满距离轴
    ax = axes[0]
    for i, (theta, label, color) in enumerate(zip(thetas, labels, colors_p)):
        eff_range = np.pi / (2 * theta)
        y_start = i * 1.0
        d_eff = np.linspace(0, min(eff_range, 2000), 500)
        ax.fill_between(d_eff, y_start, y_start + 0.7, color=color, alpha=0.6)
        if eff_range < 2000:
            d_osc = np.linspace(eff_range, 2000, 500)
            ax.fill_between(d_osc, y_start, y_start + 0.7, color=color, alpha=0.12)
        ax.text(eff_range * 0.95, y_start + 0.85, f'≈{eff_range:.0f}', fontsize=8, color=color,
                ha='right', va='bottom', fontweight='bold')
        ax.text(1.5, y_start + 0.35, label, fontsize=8, color=color, va='center')
        ax.plot([eff_range, eff_range], [y_start - 0.05, y_start + 0.75], color=color, lw=1, ls='--', alpha=0.4)
    ax.set_xlabel('相对距离 d (对数刻度)', fontsize=10)
    ax.set_xscale('log')
    ax.set_xlim(1, 2000)
    ax.set_ylim(-0.5, 4.5)
    ax.set_yticks([])
    ax.set_title('各频率灵敏区铺满距离轴', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.2, axis='x')
    ax.text(1.5, -0.4, '实色=灵敏区(cos 1→0)\n浅色=震荡区(无区分力)', fontsize=7, color='gray', va='top')

    # 右: 单频率 vs 多频率
    ax = axes[1]
    dists = np.arange(0, 200)
    single = np.cos(0.1 * dists)
    ax.plot(dists, single, color='red', lw=1.5, alpha=0.6, label='单频率 θ=0.1', linestyle='--')
    multi = sum(np.cos(t * dists) for t in thetas) / 4
    ax.plot(dists, multi, color='navy', lw=2, label='多频率叠加(4个pair)', alpha=0.85)
    ax.axhline(y=0, color='k', lw=0.5, ls=':', alpha=0.5)
    ax.set_xlabel('相对距离 d', fontsize=10)
    ax.set_ylabel('注意力分数 (归一化)', fontsize=10)
    ax.set_xlim(0, 200); ax.set_ylim(-0.7, 1.1)
    ax.set_title('单频率有盲区 vs 多频率全覆盖', fontsize=12, fontweight='bold')
    ax.legend(fontsize=9, loc='upper right')
    ax.grid(True, alpha=0.2)
    ax.annotate('盲区: cos过零后\n震荡, 无法区分', xy=(25, -0.45), fontsize=7, color='red',
                ha='center', bbox=dict(boxstyle='round,pad=0.2', facecolor='lightyellow', edgecolor='red', alpha=0.7))

    plt.tight_layout()
    return save(fig, 'fig_ch5_rope.png')

# ============================================================
# Ch6 — 2张图
# ============================================================

def fig_ch6_lora():
    """图20: LoRA/DoRA/QLoRA参数对比"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # 左：参数空间示意
    ax = axes[0]
    d, r = 10, 4
    # 画全参数空间
    ax.fill_between([0, d], 0, d, alpha=0.1, color='blue', label=f'full W: {d}×{d}={d*d} params')
    # 画LoRA低秩子空间
    ax.fill_between([0, r], 0, d, alpha=0.3, color='green', label=f'LoRA B: {d}×{r}={d*r}')
    ax.fill_between([0, d], 0, r, alpha=0.3, color='orange', label=f'LoRA A: {r}×{d}={d*r}')
    ax.plot([0, r], [d, d], 'g-', lw=3)
    ax.plot([d, d], [0, r], 'orange', lw=3)
    ax.text(r/2, d+0.3, f'B ({d}×{r})', fontsize=10, color='green', ha='center')
    ax.text(d+0.3, r/2, f'A ({r}×{d})', fontsize=10, color='orange', ha='center', rotation=90)
    ax.set_xlim(0, d+2); ax.set_ylim(0, d+2)
    ax.set_aspect('equal')
    ax.set_title(f'LoRA: low-rank update (r={r})', fontsize=12, fontweight='bold')
    ax.set_xlabel('dimension'); ax.set_ylabel('dimension')
    ax.legend(loc='lower right', fontsize=9)
    ax.grid(True, alpha=0.2)
    
    # 右：参数量对比表
    ax = axes[1]
    ax.axis('off')
    table_data = [
        ['Method', 'Trainable', 'Frozen', 'Use case'],
        ['Full fine-tune', 'd² (100%)', '0', 'Big data+compute'],
        ['LoRA (r=4)', '2dr (~0.2%)', 'd² (frozen W0)', 'Consumer GPU'],
        ['QLoRA', '2dr (~0.2%)', 'd² (4-bit quant)', '24GB GPU, 7B model'],
        ['DoRA', '2dr+d (~0.2%)', 'd² (frozen W0)', 'Fine-grained tasks'],
    ]
    table = ax.table(cellText=table_data[1:], colLabels=table_data[0],
                     cellLoc='center', loc='center', bbox=[0, 0.3, 1, 0.7])
    table.auto_set_font_size(False); table.set_fontsize(9)
    table.scale(1, 2)
    for (row, col), cell in table.get_celld().items():
        cell.set_text_props(fontproperties=CJK_FONT_NAME)
        if row == 0:
            cell.set_facecolor('#4472C4'); cell.set_text_props(color='white', fontweight='bold', fontproperties=CJK_FONT_NAME)
        elif row % 2 == 0:
            cell.set_facecolor('#E7E6E6')
    ax.set_title('Parameter efficiency comparison', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    return save(fig, 'fig_ch6_lora.png')

def fig_ch6_svd():
    """图19: SVD低秩分解 + 低秩截断"""
    fig, axes = plt.subplots(2, 4, figsize=(15, 7))
    
    # ---- 上排：完整SVD分解 A = UΣV^T ----
    # 原始矩阵
    ax = axes[0, 0]
    A = np.array([[3, 0, 1], [0, 2, 1]])
    im = ax.imshow(A, cmap='Blues', aspect='auto')
    for i in range(2):
        for j in range(3):
            ax.text(j, i, str(A[i,j]), ha='center', va='center', fontsize=14, fontweight='bold')
    ax.set_xticks(range(3)); ax.set_yticks(range(2))
    ax.set_title('A (2×3)\noriginal', fontsize=13, fontweight='bold')
    plt.colorbar(im, ax=ax)
    
    # U矩阵
    ax = axes[0, 1]
    U = np.array([[-0.982, -0.189], [-0.189, 0.982]])
    im = ax.imshow(U, cmap='RdBu', aspect='auto', vmin=-1, vmax=1)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f'{U[i,j]:.2f}', ha='center', va='center', fontsize=11)
    ax.set_xticks(range(2)); ax.set_yticks(range(2))
    ax.set_title('U (2×2)\nrotation', fontsize=13, fontweight='bold')
    plt.colorbar(im, ax=ax)
    
    # Σ矩阵
    ax = axes[0, 2]
    Sigma = np.array([[3.193, 0, 0], [0, 2.193, 0]])
    im = ax.imshow(Sigma, cmap='Greens', aspect='auto')
    for i in range(2):
        for j in range(3):
            if Sigma[i,j] > 0.1:
                ax.text(j, i, f'{Sigma[i,j]:.2f}', ha='center', va='center', fontsize=11, fontweight='bold')
    ax.set_xticks(range(3)); ax.set_yticks(range(2))
    ax.set_title(r'$\Sigma$ (2×3)' + '\nstretching', fontsize=13, fontweight='bold')
    plt.colorbar(im, ax=ax)
    
    # V^T矩阵
    ax = axes[0, 3]
    Vt = np.array([[-0.923, -0.118, -0.367], [-0.259, 0.896, 0.362], [-0.286, -0.429, 0.857]])
    im = ax.imshow(Vt, cmap='RdBu', aspect='auto', vmin=-1, vmax=1)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f'{Vt[i,j]:.2f}', ha='center', va='center', fontsize=10)
    ax.set_xticks(range(3)); ax.set_yticks(range(3))
    ax.set_title(r'$V^T$ (3×3)' + '\nrotation', fontsize=13, fontweight='bold')
    plt.colorbar(im, ax=ax)
    
    # ---- 下排：低秩截断对比 ----
    # A_1: rank-1 approximation
    ax = axes[1, 0]
    sigma1 = 3.193
    u1 = U[:, 0:1]  # (2,1)
    v1t = Vt[0:1, :]  # (1,3)
    A1 = sigma1 * u1 @ v1t
    im = ax.imshow(A1, cmap='Blues', aspect='auto')
    for i in range(2):
        for j in range(3):
            ax.text(j, i, f'{A1[i,j]:.2f}', ha='center', va='center', fontsize=11)
    ax.set_xticks(range(3)); ax.set_yticks(range(2))
    ax.set_title(r'$A_1$ (rank-1)' + '\n' + r'$\sigma_1 u_1 v_1^T$ only', fontsize=13, fontweight='bold')
    plt.colorbar(im, ax=ax)
    
    # Error A - A_1
    ax = axes[1, 1]
    error = A - A1
    im = ax.imshow(error, cmap='RdBu', aspect='auto', vmin=-2, vmax=2)
    for i in range(2):
        for j in range(3):
            ax.text(j, i, f'{error[i,j]:.2f}', ha='center', va='center', fontsize=11)
    ax.set_xticks(range(3)); ax.set_yticks(range(2))
    ax.set_title(r'$A - A_1$' + '\n(error)', fontsize=13, fontweight='bold')
    plt.colorbar(im, ax=ax)
    
    # Energy retention bar chart
    ax = axes[1, 2]
    sigma2 = 2.193
    total_energy = sigma1**2 + sigma2**2
    k1_energy = sigma1**2
    labels = ['k=1\n(68%)', 'k=2\n(100%)']
    energies = [k1_energy / total_energy * 100, 100]
    colors_e = ['#4CAF50', '#2196F3']
    bars = ax.bar(labels, energies, color=colors_e, width=0.5)
    ax.set_ylabel('Energy retention (%)', fontsize=11)
    ax.set_title(r'Energy retention' + '\n' + r'$\|A_k\|^2 / \|A\|^2$', fontsize=13, fontweight='bold')
    ax.set_ylim(0, 120)
    for bar, val in zip(bars, energies):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f'{val:.0f}%', ha='center', fontsize=11)
    ax.grid(True, axis='y', alpha=0.2)
    
    # Frobenius norm comparison
    ax = axes[1, 3]
    frob_A = np.sqrt(np.sum(A**2))
    frob_error = np.sqrt(np.sum(error**2))
    labels2 = [r'$\|A\|_F$', r'$\|A-A_1\|_F$']
    vals = [frob_A, frob_error]
    colors_f = ['#2196F3', '#F44336']
    bars2 = ax.bar(labels2, vals, color=colors_f, width=0.5)
    ax.set_ylabel('Frobenius norm', fontsize=11)
    ax.set_title(f'Error ' + r'$\approx \sigma_2$' + f' = {sigma2:.3f}\n(Eckart-Young)', fontsize=13, fontweight='bold')
    ax.set_ylim(0, max(vals) * 1.3)
    for bar, val in zip(bars2, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, f'{val:.3f}', ha='center', fontsize=11)
    ax.grid(True, axis='y', alpha=0.2)
    
    plt.suptitle(r'SVD: $A = U\Sigma V^T$  (rotate -> stretch -> rotate)  +  low-rank truncation keeps main info', fontsize=14, y=1.02)
    plt.tight_layout()
    return save(fig, 'fig_ch6_svd.png')

# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """生成全部配图。返回失败张数（0 = 全部成功），供退出码使用。"""
    from fig_common import run_all

    setup()
    funcs = [
        # Ch0 AI 全景 (1张)
        fig_ch0_ai_panorama,
        # Ch1 梯度下降 (4张)
        fig_ch1_gradient_path, fig_ch1_learning_rate, fig_ch1_local_minimum,
        fig_ch1_adam_vs_gd,
        # Ch2 拉格朗日乘子法 (3张)
        fig_ch2_lagrange, fig_ch2_gradient_field, fig_ch2_complementary_slackness,
        # Ch3 最大熵/Softmax (3张)
        fig_ch3_entropy_softmax, fig_ch3_crossentropy,
        fig_ch3_diffusion_demo,
        # Ch4 反向传播 (4张)
        fig_ch4_backprop, fig_ch4_activations, fig_ch4_swiglu,
        fig_ch4_gradient_decay,
        # Ch5 Attention (4张)
        fig_ch5_attention_heatmap, fig_ch5_attention_qkv,
        fig_ch5_llm_pipeline, fig_ch5_rope,
        # Ch6 低秩 (2张)
        fig_ch6_lora, fig_ch6_svd,
    ]
    return run_all(funcs, "AI数学：从起步到前沿", expected=21)


if __name__ == '__main__':
    sys.exit(main())  # 失败张数作为退出码，CI 才能真的拦住
