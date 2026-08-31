#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扩散：从噪声生成 - 全部可视化图表
生成 41 张插图，覆盖从数学原理到工程实践的全部关键概念。
依赖: numpy, matplotlib
运行: python generate_figures.py
输出: figures/ 目录
"""

import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import (
    FancyArrowPatch, Circle, FancyBboxPatch, Rectangle, Polygon, Ellipse
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import fig_common  # noqa: E402  (sys.path 就绪后再导入共享模块)
from fig_common import CJK_FONT_NAME, setup_rc  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "figures"

# 扩散脚本 dpi 已与其余四本统一（200）；CJK_FONT_NAME 字体由共享模块探测。
setup_rc(dpi=200)

plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['axes.labelsize'] = 11


def save(fig, name):
    """统一保存函数（与其余四本一致，均经 fig_common.save_fig）"""
    fig_common.save_fig(fig, name, OUTPUT_DIR, dpi=200, facecolor='white')
    print(f"[OK] {OUTPUT_DIR / name}")

# =============================================================================
# Ch1 前向过程——信号衰减与噪声增长
# =============================================================================
def fig_ch1_forward_process():
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    t = np.arange(0, 1001)
    beta_schedule = np.linspace(0.0001, 0.02, 1000)
    alpha = 1 - beta_schedule
    alpha_bar = np.concatenate([[1.0], np.cumprod(alpha)])

    # 左图: 信号与噪声比例
    ax = axes[0]
    ax.plot(t, np.sqrt(alpha_bar), 'b-', linewidth=2, label=r'$\sqrt{\bar{\alpha}_t}$（信号）')
    ax.plot(t, np.sqrt(1-alpha_bar), 'r-', linewidth=2, label=r'$\sqrt{1-\bar{\alpha}_t}$（噪声）')
    ax.axhline(y=0.1, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(x=500, color='gray', linestyle='--', alpha=0.5)
    ax.set_xlabel('时间步 t')
    ax.set_ylabel('系数')
    ax.set_title('前向过程：信号 vs 噪声')
    ax.legend(loc='upper right')
    ax.set_xlim(0, 1000); ax.set_ylim(0, 1.1)
    ax.grid(True, alpha=0.3)

    # 中图: 一维信号墨化过程
    ax = axes[1]
    np.random.seed(42)
    x0 = 2.0
    t_demo = [0, 10, 50, 100, 200, 500, 1000]
    alpha_bar_demo = np.array([1.0, 0.8, 0.5, 0.25, 0.1, 0.01, 0.0001])
    colors = plt.cm.Blues(np.linspace(0.3, 0.9, len(t_demo)))
    for i, (ti, ab) in enumerate(zip(t_demo, alpha_bar_demo)):
        x_vals = np.sqrt(ab) * x0 + np.sqrt(1-ab) * np.random.randn(1000)
        ax.hist(x_vals, bins=30, alpha=0.6, color=colors[i], 
                label=f't={ti}, μ={np.sqrt(ab)*x0:.2f}')
    ax.set_xlabel('数值'); ax.set_ylabel('频数')
    ax.set_title('一维信号随时间"滴墨"扩散')
    ax.legend(loc='upper left', fontsize=8)
    ax.axvline(x=x0, color='green', linestyle='--', linewidth=2)

    # 右图: 闭式跳步公式
    ax = axes[2]
    ax.text(0.5, 0.85, '闭式跳步公式', ha='center', fontsize=13, fontweight='bold')
    ax.text(0.5, 0.65, r'$x_t = \sqrt{\bar{\alpha}_t}\,x_0 + \sqrt{1-\bar{\alpha}_t}\,\epsilon$', 
            ha='center', fontsize=12, family='monospace',
            bbox=dict(boxstyle='round', facecolor='lightyellow', edgecolor='orange'))
    ax.annotate('', xy=(0.2, 0.45), xytext=(0.5, 0.55),
                arrowprops=dict(arrowstyle='->', color='blue', lw=2))
    ax.text(0.15, 0.40, '直接跳步\nO(1)', ha='center', fontsize=10, color='blue')
    ax.annotate('', xy=(0.8, 0.45), xytext=(0.5, 0.55),
                arrowprops=dict(arrowstyle='->', color='red', lw=2))
    ax.text(0.85, 0.40, '逐步加噪\nO(t)', ha='center', fontsize=10, color='red')
    ax.text(0.5, 0.15, '闭式公式免去逐步加噪', 
            ha='center', fontsize=10, style='italic')
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')

    save(fig, 'fig_ch1_forward_process.png')


# =============================================================================
# Ch3 反向过程——去噪步骤与贝叶斯概念
# =============================================================================
def fig_ch3_reverse_process():
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    # 左图: 逐步去噪可视化
    ax = axes[0]
    np.random.seed(123)
    x0, T = 2.0, 1000
    beta = np.linspace(0.0001, 0.02, T)
    alpha_bar = np.cumprod(1 - beta)
    t_steps = [1000, 800, 600, 400, 200, 50, 0]
    for i, t in enumerate(t_steps):
        if t == 0:
            val, color = x0, 'green'
        else:
            ab = alpha_bar[t-1]
            val = np.sqrt(ab) * x0 + np.sqrt(1-ab) * np.random.randn()
            color = plt.cm.Reds(0.3 + 0.7 * (1 - t/T))
        ax.scatter([t], [val], s=100, c=[color], zorder=5)
        if i > 0:
            ax.plot([t_steps[i-1], t], [prev_val, val], 'k--', alpha=0.3)
        prev_val = val
    ax.axhline(y=x0, color='green', linestyle='-', alpha=0.3, linewidth=2)
    ax.set_xlabel('时间步 t'); ax.set_ylabel('数值')
    ax.set_title('反向过程：逐步去噪')
    ax.set_xlim(0, 1050); ax.invert_xaxis()
    ax.grid(True, alpha=0.3)

    # 中图: 贝叶斯后验概念
    ax = axes[1]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    for cx, name, color in [(2, 'Prior\n$p(x_{t-1})$', 'lightblue'),
                            (5, 'Likelihood\n$p(x_t|x_{t-1})$', 'lightcoral'),
                            (8, 'Posterior\n$p(x_{t-1}|x_t)$', 'lightgreen')]:
        ax.add_patch(Circle((cx, 5), 1.2, color=color, alpha=0.5))
        ax.text(cx, 5, name, ha='center', va='center', fontsize=9)
    ax.annotate('', xy=(3.8, 5), xytext=(3.2, 5), arrowprops=dict(arrowstyle='->', color='black'))
    ax.annotate('', xy=(6.8, 5), xytext=(6.2, 5), arrowprops=dict(arrowstyle='->', color='black'))
    ax.text(5, 8, r'$p(x_{t-1}|x_t) = \frac{p(x_t|x_{t-1})p(x_{t-1})}{p(x_t)}$', 
            ha='center', fontsize=11, 
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))
    ax.text(5, 2, '未知 $p(x_t)$（归一化常数）→ 用神经网络近似', 
            ha='center', fontsize=10, style='italic')
    ax.axis('off'); ax.set_title('贝叶斯反向过程')

    save(fig, 'fig_ch3_reverse_process.png')


# =============================================================================
# Ch2 分数函数——等高线地图与 Langevin 动力学
# =============================================================================
def fig_ch2_score_function():
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    x = np.linspace(-3, 3, 50)
    y = np.linspace(-3, 3, 50)
    X, Y = np.meshgrid(x, y)
    Z = np.exp(-((X-1)**2 + (Y-1)**2)/0.5) + 0.7*np.exp(-((X+1)**2 + (Y+1)**2)/0.5)
    log_Z = np.log(Z + 1e-8)
    dy, dx = np.gradient(log_Z)

    # 左图: 等高线与分数向量
    ax = axes[0]
    contour = ax.contour(X, Y, Z, levels=8, colors='black', alpha=0.3, linewidths=0.5)
    ax.clabel(contour, inline=True, fontsize=8)
    step = 5
    ax.quiver(X[::step, ::step], Y[::step, ::step], 
              dx[::step, ::step], dy[::step, ::step],
              color='red', alpha=0.7, scale=20, width=0.003)
    ax.set_xlabel('$x_1$'); ax.set_ylabel('$x_2$')
    ax.set_title('分数函数：$\\nabla_x \\log p(x)$\n（箭头指向密度上坡方向）')
    ax.set_aspect('equal')

    # 中图: Langevin动力学轨迹
    ax = axes[1]
    np.random.seed(42)
    n_steps, eta = 200, 0.1
    x_curr = np.array([-2.5, -2.5])
    trajectory = [x_curr.copy()]
    for _ in range(n_steps):
        c1, c2 = np.array([1, 1]), np.array([-1, -1])
        d1, d2 = x_curr - c1, x_curr - c2
        score = -(d1 * np.exp(-np.sum(d1**2)/0.5) * 2/0.5 + 
                  d2 * np.exp(-np.sum(d2**2)/0.5) * 2/0.5 * 0.7)
        score /= (np.exp(-np.sum(d1**2)/0.5) + 0.7*np.exp(-np.sum(d2**2)/0.5) + 1e-8)
        x_curr = x_curr + eta/2 * score + np.sqrt(eta) * np.random.randn(2)
        trajectory.append(x_curr.copy())
    trajectory = np.array(trajectory)
    ax.plot(trajectory[:, 0], trajectory[:, 1], 'b-', alpha=0.5, linewidth=1)
    ax.scatter(trajectory[0, 0], trajectory[0, 1], c='red', s=100, zorder=5, label='起点（噪声）')
    ax.scatter(trajectory[-1, 0], trajectory[-1, 1], c='green', s=100, zorder=5, label='终点（数据）')
    ax.contour(X, Y, Z, levels=8, colors='black', alpha=0.2, linewidths=0.5)
    ax.set_xlabel('$x_1$'); ax.set_ylabel('$x_2$')
    ax.set_title('Langevin 动力学轨迹\n（沿密度上坡走向数据）')
    ax.legend(loc='upper left'); ax.set_aspect('equal')

    # 右图: Ch1 vs Ch3 对比
    ax = axes[2]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    box1 = FancyBboxPatch((0.5, 6), 3.5, 2.5, boxstyle="round,pad=0.1", 
                           facecolor='lightblue', edgecolor='blue', linewidth=2)
    ax.add_patch(box1)
    ax.text(2.25, 7.8, '第1章 梯度下降', ha='center', fontsize=11, fontweight='bold')
    ax.text(2.25, 7.2, r'$-\nabla_\theta L$', ha='center', fontsize=14, family='monospace')
    ax.text(2.25, 6.6, '优化对象：模型参数', ha='center', fontsize=9)

    box2 = FancyBboxPatch((5.5, 6), 3.5, 2.5, boxstyle="round,pad=0.1", 
                           facecolor='lightcoral', edgecolor='red', linewidth=2)
    ax.add_patch(box2)
    ax.text(7.25, 7.8, '第3章 分数函数', ha='center', fontsize=11, fontweight='bold')
    ax.text(7.25, 7.2, r'$+\nabla_x \log p(x)$', ha='center', fontsize=14, family='monospace')
    ax.text(7.25, 6.6, '优化对象：数据样本', ha='center', fontsize=9)

    ax.annotate('', xy=(5.3, 7.25), xytext=(4.2, 7.25),
                arrowprops=dict(arrowstyle='<->', color='purple', lw=2))
    ax.text(4.75, 7.6, '同一套数学\n作用于不同对象', ha='center', fontsize=9, color='purple')
    ax.text(5, 4, '两者都沿某个函数的斜率走', ha='center', fontsize=11, style='italic')
    ax.text(5, 3, '第1章：参数空间 → 最小化损失', ha='center', fontsize=10)
    ax.text(5, 2.2, '第3章：数据空间 → 最大化密度', ha='center', fontsize=10)
    ax.axis('off')
    ax.set_title('梯度下降 vs 分数函数')

    save(fig, 'fig_ch2_score_function.png')


# =============================================================================
# Ch4 训练目标——噪声预测 MSE
# =============================================================================
def fig_ch4_training_objective():
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    # 左图: 噪声预测流程
    ax = axes[0]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    box_x0 = FancyBboxPatch((0.5, 6), 2, 2, boxstyle="round,pad=0.1",
                             facecolor='lightgreen', edgecolor='green', linewidth=2)
    ax.add_patch(box_x0)
    ax.text(1.5, 7.5, r'$x_0$', ha='center', fontsize=14, fontweight='bold')
    ax.text(1.5, 6.8, '干净图片', ha='center', fontsize=9)
    ax.annotate('', xy=(3.5, 7), xytext=(2.7, 7),
                arrowprops=dict(arrowstyle='->', color='red', lw=2))
    ax.text(3.1, 7.3, r'$+\epsilon$', ha='center', fontsize=12, color='red')
    box_xt = FancyBboxPatch((3.7, 6), 2, 2, boxstyle="round,pad=0.1",
                             facecolor='lightgray', edgecolor='gray', linewidth=2)
    ax.add_patch(box_xt)
    ax.text(4.7, 7.5, r'$x_t$', ha='center', fontsize=14, fontweight='bold')
    ax.text(4.7, 6.8, '噪声图片', ha='center', fontsize=9)
    box_nn = FancyBboxPatch((6.5, 6), 2.5, 2, boxstyle="round,pad=0.1",
                             facecolor='lightyellow', edgecolor='orange', linewidth=2)
    ax.add_patch(box_nn)
    ax.text(7.75, 7.5, r'$\epsilon_\theta$', ha='center', fontsize=14, fontweight='bold')
    ax.text(7.75, 6.8, '神经网络', ha='center', fontsize=9)
    ax.annotate('', xy=(6.3, 7), xytext=(5.9, 7),
                arrowprops=dict(arrowstyle='->', color='blue', lw=2))
    ax.text(7.75, 5.2, r'$\hat{\epsilon}$', ha='center', fontsize=12, color='blue')
    ax.annotate('', xy=(7.75, 5.5), xytext=(7.75, 6),
                arrowprops=dict(arrowstyle='->', color='blue', lw=1.5))
    ax.text(5, 3.5, r'$\mathcal{L} = \|\epsilon - \epsilon_\theta(x_t, t)\|^2$', 
            ha='center', fontsize=12,
            bbox=dict(boxstyle='round', facecolor='lightyellow', edgecolor='orange'))
    ax.text(5, 2.5, '不预测图片，而是预测噪声！', 
            ha='center', fontsize=10, style='italic', color='red')
    ax.axis('off')
    ax.set_title('训练：噪声预测任务')

    # 中图: MSE损失曲面
    ax = axes[1]
    eps_true = 0.5
    eps_pred_range = np.linspace(-1, 2, 100)
    loss = (eps_true - eps_pred_range)**2
    ax.plot(eps_pred_range, loss, 'b-', linewidth=2)
    ax.axvline(x=eps_true, color='green', linestyle='--', linewidth=2, label=f'真实 ε={eps_true}')
    ax.scatter([0.4], [(0.5-0.4)**2], c='red', s=100, zorder=5, label='预测')
    ax.annotate('梯度推动\n预测趋向真实值', xy=(0.4, 0.01), xytext=(0, 0.5),
                arrowprops=dict(arrowstyle='->', color='red'), fontsize=9, color='red')
    ax.set_xlabel(r'预测噪声 $\epsilon_\theta$')
    ax.set_ylabel('MSE 损失')
    ax.set_title('MSE 损失曲面')
    ax.legend(loc='upper left'); ax.grid(True, alpha=0.3)

    # 右图: U-Net反向传播
    ax = axes[2]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    layers = ['Output\n(noise map)', 'UNet Decoder', 'Skip Connection', 'UNet Encoder', 'Input\n(noisy image)']
    y_pos = [1.5, 3, 5, 7, 8.5]
    colors = ['lightgreen', 'lightblue', 'lightyellow', 'lightblue', 'lightgray']
    for i, (layer, y, c) in enumerate(zip(layers, y_pos, colors)):
        box = FancyBboxPatch((2, y-0.4), 6, 0.8, boxstyle="round,pad=0.05",
                              facecolor=c, edgecolor='black', linewidth=1)
        ax.add_patch(box)
        ax.text(5, y, layer, ha='center', va='center', fontsize=10)
        if i < len(layers)-1:
            ax.annotate('', xy=(5, y_pos[i+1]-0.4), xytext=(5, y+0.4),
                       arrowprops=dict(arrowstyle='->', color='red', lw=1.5))
            ax.text(6.5, (y+y_pos[i+1])/2, r'$\partial L / \partial W$', 
                    ha='center', va='center', fontsize=10, color='red')
    ax.annotate('', xy=(2.5, 7-0.4), xytext=(2.5, 3+0.4),
                arrowprops=dict(arrowstyle='->', color='green', lw=1.5, linestyle='--'))
    ax.text(1.5, 5, '跳跃\n连接', ha='center', va='center', fontsize=8, color='green')
    ax.text(5, 0.5, '反向传播：链式法则穿过 U-Net（第4章）', 
            ha='center', fontsize=10, style='italic')
    ax.axis('off')
    ax.set_title('扩散 U-Net 中的反向传播')

    save(fig, 'fig_ch4_training_objective.png')


# =============================================================================
# Ch5 采样策略——DDPM vs DDIM
# =============================================================================
def fig_ch5_sampling_strategies():
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    # 左图: DDPM vs DDIM路径
    ax = axes[0]
    np.random.seed(42)
    T = 50
    true_path = np.array([np.linspace(3, 0.5, T), np.linspace(2, 0.5, T)]).T
    for i in range(T):
        true_path[i, 0] += 0.5 * np.sin(i * 0.2)
        true_path[i, 1] += 0.3 * np.cos(i * 0.15)
    ddpm_path = true_path.copy()
    for i in range(1, T):
        ddpm_path[i] += 0.15 * np.random.randn(2)
    ddim_indices = np.linspace(0, T-1, 10, dtype=int)
    ddim_path = true_path[ddim_indices]
    ax.plot(ddpm_path[:, 0], ddpm_path[:, 1], 'b.-', alpha=0.5, linewidth=1, markersize=3, 
            label='DDPM（50 步，有噪声）')
    ax.plot(ddim_path[:, 0], ddim_path[:, 1], 'r.-', alpha=0.8, linewidth=2, markersize=8, 
            label='DDIM（10 步，确定性）')
    ax.scatter([true_path[0, 0]], [true_path[0, 1]], c='purple', s=150, marker='*', zorder=5, label='起点（噪声）')
    ax.scatter([true_path[-1, 0]], [true_path[-1, 1]], c='green', s=150, marker='*', zorder=5, label='终点（数据）')
    ax.set_xlabel('维度 1'); ax.set_ylabel('维度 2')
    ax.set_title('DDPM vs DDIM 采样路径')
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.3); ax.set_aspect('equal')

    # 中图: 步数-质量权衡
    ax = axes[1]
    steps = [10, 20, 50, 100, 200, 500, 1000]
    ddim_q = [0.75, 0.88, 0.95, 0.97, 0.98, 0.99, 0.99]
    ddpm_q = [0.60, 0.72, 0.85, 0.92, 0.96, 0.98, 0.99]
    ax.plot(steps, ddim_q, 'r-o', linewidth=2, markersize=6, label='DDIM 质量')
    ax.plot(steps, ddpm_q, 'b-s', linewidth=2, markersize=6, label='DDPM 质量')
    ax.axhline(y=0.95, color='gray', linestyle='--', alpha=0.5)
    ax.text(600, 0.96, '质量阈值', fontsize=9, color='gray')
    ax.set_xlabel('采样步数'); ax.set_ylabel('生成质量')
    ax.set_title('质量 vs 步数：低步数下 DDIM 胜出')
    ax.set_xscale('log')
    ax.legend(loc='lower right'); ax.grid(True, alpha=0.3)
    ax.annotate('DDIM 50 步 ≈ DDPM 500 步', xy=(50, 0.95), xytext=(100, 0.85),
                arrowprops=dict(arrowstyle='->', color='red'), fontsize=9, color='red')

    # 右图: 确定性 ODE 轨迹 —— 每个噪声起点 → 唯一数据终点，轨迹互不相交
    ax = axes[2]
    t_ode = np.linspace(1, 0, 100)
    abar = np.cos(t_ode * np.pi / 2) ** 2   # t=1→abar=0(噪声端), t=0→abar=1(数据端)
    # (噪声起点, 数据终点)：两者都保序 ⇒ 任意 t 的正系数组合保序 ⇒ 轨迹互不相交
    pairs = [(-2.2, -1.5), (-0.8, -1.2), (0.8, 1.2), (2.2, 1.5)]
    blues = ['#1f4e79', '#2e75b6', '#5b9bd5', '#2e75b6']
    for k, (y_noise, y_data) in enumerate(pairs):
        y = y_data * np.sqrt(abar) + y_noise * np.sqrt(1 - abar)
        ax.plot(t_ode, y, '-', color=blues[k], linewidth=2.2, zorder=3,
                label='确定性 ODE 轨迹' if k == 0 else None)
        ax.scatter([1], [y_noise], c='purple', s=70, zorder=5,
                   label='噪声起点 ~N(0,1)' if k == 0 else None)
        ax.scatter([0], [y_data], c='green', s=70, zorder=5,
                   label='数据终点（流形）' if k == 0 else None)
    ax.text(0.5, 0.0, '轨迹互不相交\n（确定性双射）', fontsize=9,
            ha='center', va='center', color='#444', style='italic')
    ax.set_xlabel('时间 t（噪声 → 数据）'); ax.set_ylabel('数据值')
    ax.set_title('概率流 ODE：确定性轨迹\n（DDIM = ODE 离散化）')
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(-2.8, 2.8)
    ax.invert_xaxis()

    save(fig, 'fig_ch5_sampling_strategies.png')


# =============================================================================
# Ch6 条件控制与 LoRA
# =============================================================================
def fig_ch6_conditional_control():
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    # 左图: CFG引导强度
    ax = axes[0]
    w_values = [0, 1, 3, 7.5, 15, 25]
    conformity = [0.3, 0.5, 0.75, 0.92, 0.97, 0.99]
    diversity = [0.95, 0.85, 0.70, 0.55, 0.35, 0.15]
    ax.plot(w_values, conformity, 'r-o', linewidth=2, markersize=8, label='条件贴合度 ↑')
    ax.plot(w_values, diversity, 'b-s', linewidth=2, markersize=8, label='输出多样性 ↓')
    ax.axvline(x=7.5, color='green', linestyle='--', linewidth=2, alpha=0.7)
    ax.text(7.5, 1.02, '甜点区', ha='center', fontsize=9, color='green')
    ax.fill_between([5, 12], [0, 0], [1, 1], alpha=0.1, color='green')
    ax.set_xlabel('引导强度 w'); ax.set_ylabel('分数')
    ax.set_title('CFG：w 控制"贴合度-多样性"权衡')
    ax.legend(loc='center right'); ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1.1)

    # 中图: CFG向量加法
    ax = axes[1]
    ax.set_xlim(-1, 6); ax.set_ylim(-1, 6)
    ax.annotate('', xy=(1, 1), xytext=(0, 0), arrowprops=dict(arrowstyle='->', color='blue', lw=2))
    ax.text(0.3, 0.3, r'$\epsilon_{unc}$', fontsize=12, color='blue')
    ax.annotate('', xy=(4, 3), xytext=(0, 0), arrowprops=dict(arrowstyle='->', color='green', lw=2))
    ax.text(2, 1.8, r'$\epsilon_{cond}$', fontsize=12, color='green')
    ax.annotate('', xy=(3, 2), xytext=(1, 1),
                arrowprops=dict(arrowstyle='->', color='orange', lw=2, linestyle='--'))
    ax.text(2.2, 1.3, r'$\epsilon_{cond}-\epsilon_{unc}$', fontsize=10, color='orange')
    ax.annotate('', xy=(5, 4), xytext=(0, 0), arrowprops=dict(arrowstyle='->', color='red', lw=3))
    ax.text(3.0, 3.7, r'$\hat{\epsilon}$', fontsize=13, color='red', fontweight='bold')
    ax.text(2.5, 5.5, 'CFG = 无条件 + w ×（条件偏置）', 
            ha='center', fontsize=10.5, fontweight='bold')
    ax.text(2.5, -0.7, r'$\hat{\epsilon}=\epsilon_{unc}+w(\epsilon_{cond}-\epsilon_{unc})$', 
            ha='center', fontsize=11, color='red',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.set_aspect('equal'); ax.axis('off')
    ax.set_title('CFG：噪声空间里的向量加法')

    # 右图: LoRA低秩修正
    ax = axes[2]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    box_w0 = FancyBboxPatch((0.5, 5), 3, 3, boxstyle="round,pad=0.1",
                             facecolor='lightblue', edgecolor='blue', linewidth=2)
    ax.add_patch(box_w0)
    ax.text(2, 7.5, r'$W_0$', ha='center', fontsize=14, fontweight='bold')
    ax.text(2, 6.5, '预训练\n（冻结）', ha='center', fontsize=9)
    box_b = FancyBboxPatch((4.5, 7), 1.5, 2, boxstyle="round,pad=0.05",
                            facecolor='lightyellow', edgecolor='orange', linewidth=2)
    ax.add_patch(box_b)
    ax.text(5.25, 8.5, r'$B$', ha='center', fontsize=12, fontweight='bold')
    ax.text(5.25, 7.5, r'$d * r$', ha='center', fontsize=8)
    box_a = FancyBboxPatch((4.5, 5), 2.5, 1.5, boxstyle="round,pad=0.05",
                            facecolor='lightyellow', edgecolor='orange', linewidth=2)
    ax.add_patch(box_a)
    ax.text(5.75, 6.2, r'$A$', ha='center', fontsize=12, fontweight='bold')
    ax.text(5.75, 5.5, r'$r * d$', ha='center', fontsize=8)
    ax.text(4.5, 6.5, r'$*$', ha='center', fontsize=14, fontweight='bold')
    ax.text(7.5, 6.5, r'$=$', ha='center', fontsize=14, fontweight='bold')
    box_result = FancyBboxPatch((8, 5), 1.5, 3, boxstyle="round,pad=0.1",
                                 facecolor='lightgreen', edgecolor='green', linewidth=2)
    ax.add_patch(box_result)
    ax.text(8.75, 7.5, r'$W$', ha='center', fontsize=14, fontweight='bold')
    ax.text(8.75, 6.5, '最终\n权重', ha='center', fontsize=9)
    ax.text(2, 4.5, r'$+$', ha='center', fontsize=14, fontweight='bold')
    ax.annotate('', xy=(5.25, 5), xytext=(2, 4.5),
                arrowprops=dict(arrowstyle='->', color='black', lw=1.5))
    ax.text(5, 3.5, r'$W = W_0 + B * A$', ha='center', fontsize=12,
            bbox=dict(boxstyle='round', facecolor='white', edgecolor='black'))
    ax.text(5, 2.5, '低秩更新', ha='center', fontsize=10, color='orange')
    ax.text(5, 1.5, '只训练 B 和 A（小），冻结 W0（大）', 
            ha='center', fontsize=10, style='italic', color='red')
    ax.axis('off')
    ax.set_title('LoRA：低秩适配')

    save(fig, 'fig_ch6_conditional_control.png')


# =============================================================================
# Ch9 前沿展望——DiT 与视频生成
# =============================================================================
def fig_ch9_frontier():
    """Ch9 §9.7: 前沿全景——技法×工具矩阵 + 2022→2026 时间线"""
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, 12); ax.set_ylim(0, 10); ax.axis('off')
    ax.set_title('前沿全景：生成模型 = 技法 × 工具', fontsize=14, fontweight='bold',
                 fontproperties=CJK_FONT_NAME, pad=15)

    # 矩阵网格
    techniques = ['晕染（扩散/流匹配）', '线描（自回归）', '拼贴（掩码扩散）', '平涂（一致性模型）']
    tools = ['勾线笔\n(U-Net)', '大板刷\n(Transformer)', '海绵滚轮\n(Mamba/SSM)']

    # 网格参数
    x0, y0 = 2.5, 3.0  # 左下角
    cw, ch = 2.8, 1.3  # 格子宽高

    # 画列标题（工具）
    for j, tool in enumerate(tools):
        ax.text(x0 + j*cw + cw/2, y0 + 4*ch + 0.4, tool, ha='center', va='bottom',
                fontsize=10, fontweight='bold', fontproperties=CJK_FONT_NAME, color='#333')

    # 画行标题（技法）
    for i, tech in enumerate(techniques):
        ax.text(x0 - 0.2, y0 + (3-i)*ch + ch/2, tech, ha='right', va='center',
                fontsize=9.5, fontweight='bold', fontproperties=CJK_FONT_NAME, color='#333')

    # 画格子 + 填充模型名
    models = {
        (0, 0): 'SD 1.x/2.x\n(2022)',
        (0, 1): 'DiT / SD3\nFLUX / MovieGen\n(2024-2026)',
        (0, 2): 'DiS\n(2025)',
        (1, 0): '',
        (1, 1): 'LlamaGen\nVAR / Infinity\n(2024-2025)',
        (1, 2): '',
        (2, 0): '',
        (2, 1): 'MDLM\nShow-o\n(2024-2025)',
        (2, 2): '',
        (3, 0): 'LCM\n(2023)',
        (3, 1): 'SANA-Sprint\n(2025)',
        (3, 2): '',
    }

    for i in range(4):
        for j in range(3):
            x = x0 + j*cw
            y = y0 + (3-i)*ch
            # 有内容的格子用浅色背景
            content = models.get((i, j), '')
            fc = '#555555' if not content else '#555555' if i == 0 else '#555555' if i == 1 else '#555555' if i == 2 else '#555555'
            ec = '#999' if not content else '#1F5FB0' if i == 0 else '#FF6600' if i == 1 else '#2D6A3A' if i == 2 else '#9370DB'
            lw = 1 if not content else 1.5
            box = FancyBboxPatch((x+0.05, y+0.05), cw-0.1, ch-0.1,
                                  boxstyle="round,pad=0.05", facecolor=fc, edgecolor=ec, linewidth=lw)
            ax.add_patch(box)
            if content:
                ax.text(x + cw/2, y + ch/2, content, ha='center', va='center',
                        fontsize=8.5, fontproperties=CJK_FONT_NAME, color='#333')

    # 混合技法标注（跨格子）
    ax.annotate('Transfusion\n(左线描+右晕染)', xy=(x0 + 1*cw + cw/2, y0 + 3*ch + ch + 0.1),
                xytext=(x0 + 1*cw + cw/2, y0 + 4*ch + 1.2),
                fontsize=8.5, ha='center', fontproperties=CJK_FONT_NAME, color='#C62828',
                arrowprops=dict(arrowstyle='->', color='#C62828', lw=1.5),
                bbox=dict(boxstyle='round,pad=0.2', facecolor='#555555', edgecolor='#C62828'))

    ax.annotate('MAR\n(线描定序+晕染填内容)', xy=(x0 + 0.5*cw, y0 + 3*ch + ch/2),
                xytext=(x0 - 0.3, y0 + 4*ch + 1.2),
                fontsize=8.5, ha='center', fontproperties=CJK_FONT_NAME, color='#C62828',
                arrowprops=dict(arrowstyle='->', color='#C62828', lw=1.5),
                bbox=dict(boxstyle='round,pad=0.2', facecolor='#555555', edgecolor='#C62828'))

    # 时间线
    ty = 1.8
    ax.annotate('', xy=(11, ty), xytext=(1, ty),
                arrowprops=dict(arrowstyle='->', color='#666', lw=2))
    timeline = [
        (2.0, '2022-23\n"晕染唯一正解"\nU-Net + 扩散'),
        (4.5, '2024\n"线描也能画"\nDiT + VAR'),
        (7.0, '2025\n"一支笔多技法"\nTransfusion'),
        (9.5, '2026\n"自由组合"\n混合技法+混合工具'),
    ]
    for x, label in timeline:
        ax.plot(x, ty, 'o', color='#666', markersize=8, zorder=5)
        ax.text(x, ty - 0.3, label, ha='center', va='top', fontsize=8, fontproperties=CJK_FONT_NAME, color='#444')

    # 核心判断
    ax.text(6, 0.5, '没有一行是"一边绝对赢"——按任务选技法，按工程选工具',
            ha='center', fontsize=10, fontproperties=CJK_FONT_NAME, fontweight='bold', color='#333',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFFACD', edgecolor='#DAA520'))

    save(fig, 'fig_ch9_frontier.png')


# =============================================================================
# Ch4 时间步嵌入
# =============================================================================
def fig_ch4_time_embedding():
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    # 左图: 正弦位置编码
    ax = axes[0]
    T, dim = 1000, 64
    pe = np.zeros((T, dim))
    position = np.arange(T)[:, np.newaxis]
    div_term = np.exp(np.arange(0, dim, 2) * -(np.log(10000.0) / dim))
    pe[:, 0::2] = np.sin(position * div_term)
    pe[:, 1::2] = np.cos(position * div_term)
    im = ax.imshow(pe[:200, :32], aspect='auto', cmap='RdBu_r', vmin=-1, vmax=1)
    ax.set_xlabel('嵌入维度'); ax.set_ylabel('时间步 t')
    ax.set_title('正弦时间嵌入\n（网络如何"知道"当前步）')
    plt.colorbar(im, ax=ax, fraction=0.046)

    # 中图: 时间嵌入注入架构
    ax = axes[1]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    box_in = FancyBboxPatch((0.5, 6), 2, 1.5, boxstyle="round,pad=0.1",
                             facecolor='lightblue', edgecolor='blue', linewidth=2)
    ax.add_patch(box_in)
    ax.text(1.5, 7.2, '噪声图片\n$x_t$', ha='center', fontsize=10, fontweight='bold')
    box_t = FancyBboxPatch((0.5, 3.5), 2, 1.5, boxstyle="round,pad=0.1",
                            facecolor='lightyellow', edgecolor='orange', linewidth=2)
    ax.add_patch(box_t)
    ax.text(1.5, 4.7, '时间嵌入\n$\\gamma(t)$', ha='center', fontsize=10, fontweight='bold')
    ax.annotate('', xy=(4, 6.5), xytext=(2.7, 6.5), arrowprops=dict(arrowstyle='->', color='blue', lw=2))
    ax.annotate('', xy=(4, 6.5), xytext=(2.7, 4.5), arrowprops=dict(arrowstyle='->', color='orange', lw=2))
    ax.text(3.3, 5.5, '+', ha='center', fontsize=14, fontweight='bold')
    box_res = FancyBboxPatch((4, 5.5), 2.5, 2, boxstyle="round,pad=0.1",
                              facecolor='lightgreen', edgecolor='green', linewidth=2)
    ax.add_patch(box_res)
    ax.text(5.25, 7, 'ResBlock', ha='center', fontsize=11, fontweight='bold')
    ax.text(5.25, 6.2, 'Conv + GroupNorm\n+ SiLU', ha='center', fontsize=9)
    ax.annotate('', xy=(7.5, 6.5), xytext=(6.7, 6.5), arrowprops=dict(arrowstyle='->', color='black', lw=2))
    box_out = FancyBboxPatch((7.5, 5.5), 2, 2, boxstyle="round,pad=0.1",
                                facecolor='lightgray', edgecolor='gray', linewidth=2)
    ax.add_patch(box_out)
    ax.text(8.5, 7, '预测\n噪声', ha='center', fontsize=10, fontweight='bold')
    ax.text(5, 2, '关键洞见：同一网络，不同 t → 不同行为', 
            ha='center', fontsize=10, style='italic', color='red')
    ax.axis('off')
    ax.set_title('时间嵌入注入 UNet')

    # 右图: 网络行为随时间步变化
    ax = axes[2]
    t_steps = np.array([0, 250, 500, 750, 1000])
    step_magnitude = np.array([0.9, 0.7, 0.4, 0.15, 0.05])
    noise_sensitivity = np.array([0.1, 0.3, 0.6, 0.85, 0.98])
    ax.plot(t_steps, step_magnitude, 'b-o', linewidth=2, markersize=8, label='去噪幅度')
    ax.plot(t_steps, noise_sensitivity, 'r-s', linewidth=2, markersize=8, label='噪声敏感度')
    ax.fill_between(t_steps, 0, step_magnitude, alpha=0.2, color='blue')
    ax.fill_between(t_steps, 0, noise_sensitivity, alpha=0.2, color='red')
    ax.set_xlabel('时间步 t'); ax.set_ylabel('相对大小')
    ax.set_title('网络行为随 t 改变\n（通过时间嵌入隐式学到）')
    ax.legend(loc='center right'); ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 1000); ax.set_ylim(0, 1.1)

    save(fig, 'fig_ch4_time_embedding.png')


# =============================================================================
# Ch1 噪声调度对比 + 模型对比 + Inpainting
# =============================================================================
def fig_ch1_schedules_models_inpainting():
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    # 左图: 噪声调度对比
    ax = axes[0]
    T = 1000; t = np.arange(T)
    beta_linear = np.linspace(0.0001, 0.02, T)
    alpha_bar_linear = np.cumprod(1 - beta_linear)
    s = 0.008
    f_t = np.cos((t / T + s) / (1 + s) * np.pi / 2) ** 2
    alpha_bar_cosine = f_t / f_t[0]
    beta_sigmoid = 0.02 / (1 + np.exp(-(t - T/2) / 100))
    alpha_bar_sigmoid = np.cumprod(1 - beta_sigmoid)
    ax.plot(t, alpha_bar_linear, 'b-', linewidth=2, label='线性调度', alpha=0.8)
    ax.plot(t, alpha_bar_cosine, 'r-', linewidth=2, label='余弦调度', alpha=0.8)
    ax.plot(t, alpha_bar_sigmoid, 'g-', linewidth=2, label='sigmoid 调度', alpha=0.8)
    ax.axhline(y=0.01, color='gray', linestyle='--', alpha=0.5)
    ax.text(500, 0.02, '接近零区域\n（完全噪声）', fontsize=9, color='gray')
    ax.set_xlabel('时间步 t'); ax.set_ylabel(r'$\bar{\alpha}_t$（累积信号）')
    ax.set_title('噪声调度对比\n（架构超参数）')
    ax.legend(loc='upper right'); ax.grid(True, alpha=0.3)
    ax.set_xlim(0, T); ax.set_ylim(0, 1.1)

    # 中图: 生成模型对比
    ax = axes[1]
    ax.set_xlim(0, 10); ax.set_ylim(-0.6, 10)
    for x, y, title, desc, fc, ec in [
        (1.75, 7, 'VAE', '编码器 →\n隐变量 Z →\n解码器', 'lightblue', 'blue'),
        (1.75, 4, 'GAN', '噪声 Z →\n生成器 →\n判别器', 'lightcoral', 'red'),
        (1.75, 1, 'Diffusion', '前向加噪 →\n学习反向 →\n迭代去噪', 'lightgreen', 'green')
    ]:
        box = FancyBboxPatch((x-1.25, y-1.3), 2.5, 2.6, boxstyle="round,pad=0.1",
                              facecolor=fc, edgecolor=ec, linewidth=2)
        ax.add_patch(box)
        ax.text(x, y+1.02, title, ha='center', fontsize=11, fontweight='bold', color=ec)
        ax.text(x, y-0.55, desc, ha='center', fontsize=8.5, linespacing=1.4)
    ax.annotate('', xy=(4, 8), xytext=(3.2, 8), arrowprops=dict(arrowstyle='->', color='blue', lw=1.5))
    ax.text(4.5, 8, '确定性\n潜空间\n（快，偏模糊）', ha='left', fontsize=9, color='blue')
    ax.annotate('', xy=(4, 5), xytext=(3.2, 5), arrowprops=dict(arrowstyle='->', color='red', lw=1.5))
    ax.text(4.5, 5, '对抗训练\n（不稳定，\n模式坍塌）', ha='left', fontsize=9, color='red')
    ax.annotate('', xy=(4, 2), xytext=(3.2, 2), arrowprops=dict(arrowstyle='->', color='green', lw=1.5))
    ax.text(4.5, 2, '概率式\n反向过程\n（稳定，慢→快）', ha='left', fontsize=9, color='green')
    ax.text(8.3, 5, '扩散的取舍：\n质量 > 速度\n（但 DDIM\n补上了速度）', 
            ha='center', fontsize=9, style='italic',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))
    ax.axis('off')
    ax.set_title('生成模型：VAE vs GAN vs 扩散')

    # 右图: Inpainting原理
    ax = axes[2]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.add_patch(Rectangle((0.5, 6), 3, 3, facecolor='lightblue', edgecolor='blue', linewidth=2))
    ax.text(2, 8.5, '原始图片', ha='center', fontsize=10, fontweight='bold')
    ax.add_patch(Rectangle((1.5, 7), 1, 1, facecolor='gray', alpha=0.5, hatch='//'))
    ax.text(2, 7.5, '掩码', ha='center', fontsize=8, color='white')
    ax.text(2, 6.4, '$x_0$', ha='center', fontsize=12)
    ax.annotate('', xy=(5, 7.5), xytext=(3.7, 7.5), arrowprops=dict(arrowstyle='->', color='black', lw=2))
    ax.text(4.3, 7.8, '前向', ha='center', fontsize=9)
    ax.add_patch(Rectangle((5, 6), 3, 3, facecolor='lightgray', edgecolor='gray', linewidth=2))
    ax.text(6.5, 8.5, '噪声图片', ha='center', fontsize=10, fontweight='bold')
    ax.add_patch(Rectangle((5.5, 7), 1, 1, facecolor='blue', alpha=0.3))
    ax.text(6, 7.5, '噪声', ha='center', fontsize=8)
    ax.add_patch(Rectangle((6.5, 7), 1, 1, facecolor='gray', alpha=0.5, hatch='//'))
    ax.text(7, 7.5, '保留', ha='center', fontsize=8, color='white')
    ax.text(6.5, 6.4, '$x_t$', ha='center', fontsize=12)
    ax.text(6.5, 5.5, '修复 = 掩码区域加噪（待生成），\n非掩码区域保留（已知）', 
            ha='center', fontsize=10, style='italic',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))
    ax.axis('off')
    ax.set_title('图像修复：带掩码的前向过程')

    save(fig, 'fig_ch1_schedules_models_inpainting.png')


# =============================================================================
# Ch6 ControlNet 零初始化 + CFG 演进 + 一致性模型
# =============================================================================
def fig_ch6_controlnet_cfg_consistency():
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    # 左图: ControlNet零初始化
    ax = axes[0]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    for i, y in enumerate([7.5, 6.5, 5.5, 4.5, 3.5, 2.5, 1.5]):
        width = 1.5 + 0.5 * abs(i - 3)
        box = FancyBboxPatch((1.5-width/2, y-0.3), width, 0.6, 
                              boxstyle="round,pad=0.02",
                              facecolor='lightblue', edgecolor='blue', linewidth=1)
        ax.add_patch(box)
        ax.text(1.5, y, f'L{i+1}', ha='center', va='center', fontsize=8)
    ax.text(1.5, 8.5, '冻结的 UNet', ha='center', fontsize=11, fontweight='bold', color='blue')
    for i, y in enumerate([7.5, 6.5, 5.5, 4.5, 3.5, 2.5, 1.5]):
        box = FancyBboxPatch((4.5, y-0.3), 1.5, 0.6, 
                              boxstyle="round,pad=0.02",
                              facecolor='white', edgecolor='orange', linewidth=1, linestyle='--')
        ax.add_patch(box)
        ax.text(5.25, y, '0', ha='center', va='center', fontsize=10, color='orange', fontweight='bold')
    ax.text(5.25, 8.5, 'ControlNet\n（零初始化）', ha='center', fontsize=11, fontweight='bold', color='orange')
    ax.add_patch(FancyBboxPatch((7, 4), 2.5, 2, boxstyle="round,pad=0.1",
                                   facecolor='lightyellow', edgecolor='green', linewidth=2))
    ax.text(8.25, 5.5, '条件', ha='center', fontsize=10, fontweight='bold')
    ax.text(8.25, 4.7, '姿态/边缘/深度', ha='center', fontsize=9)
    for i, y in enumerate([7.5, 6.5, 5.5, 4.5, 3.5, 2.5, 1.5]):
        ax.annotate('', xy=(4.5, y), xytext=(3.2, y),
                   arrowprops=dict(arrowstyle='->', color='gray', lw=1, alpha=0.5))
        ax.annotate('', xy=(7, y), xytext=(6.2, y),
                   arrowprops=dict(arrowstyle='->', color='green', lw=1, alpha=0.5))
    ax.text(5.25, 0.5, '零初始化 → 输出=0 → 起初 UNet 不变\n训练逐步"解锁"控制能力', 
            ha='center', fontsize=10, style='italic', color='red',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.3))
    ax.axis('off')
    ax.set_title('ControlNet：零初始化保护基座模型')

    # 中图: CG vs CFG
    ax = axes[1]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    box_cg = FancyBboxPatch((0.5, 5.5), 4, 3.3, boxstyle="round,pad=0.1",
                             facecolor='lightcoral', edgecolor='red', linewidth=2, alpha=0.5)
    ax.add_patch(box_cg)
    ax.text(2.5, 8.5, '分类器引导（旧）', ha='center', fontsize=10.5, fontweight='bold', color='red')
    ax.text(2.5, 7.05, '训练独立分类器\n→ 计算 $\\nabla_x\\log p(y|x)$\n→ 加到分数上', ha='center', fontsize=8.5, linespacing=1.3)
    ax.text(2.5, 5.95, '问题：脆弱、昂贵、\n需要标注数据', ha='center', fontsize=8.5,
            style='italic', color='darkred', linespacing=1.3)
    ax.annotate('', xy=(5, 7.1), xytext=(4.7, 7.1), arrowprops=dict(arrowstyle='->', color='black', lw=2))
    box_cfg = FancyBboxPatch((5, 5.5), 4.5, 3.3, boxstyle="round,pad=0.1",
                              facecolor='lightgreen', edgecolor='green', linewidth=2)
    ax.add_patch(box_cfg)
    ax.text(7.25, 8.5, '无分类器引导（新）', ha='center', fontsize=10.5, fontweight='bold', color='green')
    ax.text(7.25, 7.05, '单个网络同时学\n有条件 & 无条件\n→ 线性插值', ha='center', fontsize=8.5, linespacing=1.3)
    ax.text(7.25, 5.95, '优势：无需额外分类器，\n更稳定，端到端', ha='center', fontsize=8.5,
            style='italic', color='darkgreen', linespacing=1.3)
    ax.text(5, 4.0, 'CFG 用内部条件学习\n替代外部分类器', 
            ha='center', fontsize=10, style='italic',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))
    ax.axis('off')
    ax.set_title('CG vs CFG：为何 CFG 胜出')

    # 右图: 一致性模型
    ax = axes[2]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.text(1.5, 9, '传统扩散', ha='center', fontsize=11, fontweight='bold')
    for i, x in enumerate([1, 2, 3, 4, 5]):
        y = 7.5 - i * 0.8
        circle = Circle((x, y), 0.3, color='blue', alpha=0.3 + 0.15*i)
        ax.add_patch(circle)
        if i > 0:
            ax.annotate('', xy=(x, y), xytext=(x-1, y+0.8),
                       arrowprops=dict(arrowstyle='->', color='blue', lw=1.5))
    ax.text(3, 5.5, '1000 步', ha='center', fontsize=9, color='blue')
    ax.text(7, 9, '一致性模型', ha='center', fontsize=11, fontweight='bold')
    ax.add_patch(Circle((6, 7.5), 0.3, color='red', alpha=0.3))
    ax.add_patch(Circle((9, 4.5), 0.3, color='red', alpha=0.9))
    ax.annotate('', xy=(9, 4.5), xytext=(6, 7.5),
                arrowprops=dict(arrowstyle='->', color='red', lw=3, linestyle='--'))
    ax.text(7.5, 6.2, '$f(x_t,t)=f(x_{t-1},t{-}1)$\n$=\\ldots=f(x_0,0)$', 
            ha='center', fontsize=10, color='red',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))
    ax.text(7.5, 3.5, '1-4 步！\n（实时生成）', ha='center', fontsize=10, 
            fontweight='bold', color='red')
    ax.text(5, 1.5, '一致性模型学习一个直接映射\n从任意噪声状态到干净输出', 
            ha='center', fontsize=10, style='italic',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))
    ax.axis('off')
    ax.set_title('一致性模型：单步生成')

    save(fig, 'fig_ch6_controlnet_cfg_consistency.png')


# =============================================================================
# Ch9 潜在扩散模型 + 交叉注意力 + 训练动态
# =============================================================================
def fig_ch9_latent_crossattention_training():
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    # 左图: 像素空间 vs 潜在空间
    ax = axes[0]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.add_patch(FancyBboxPatch((0.5, 6), 3, 3, boxstyle="round,pad=0.1",
                                   facecolor='lightcoral', edgecolor='red', linewidth=2, alpha=0.5))
    ax.text(2, 8.5, '像素空间', ha='center', fontsize=12, fontweight='bold', color='red')
    ax.text(2, 7.5, '512×512×3 = 786K 维', ha='center', fontsize=9)
    ax.text(2, 6.8, '此处扩散 = 慢', ha='center', fontsize=9, style='italic')
    ax.annotate('', xy=(4.5, 7.5), xytext=(3.7, 7.5), arrowprops=dict(arrowstyle='->', color='blue', lw=2))
    ax.text(4.1, 7.8, '编码器', ha='center', fontsize=9, color='blue')
    ax.add_patch(FancyBboxPatch((4.5, 6), 3, 3, boxstyle="round,pad=0.1",
                                   facecolor='lightgreen', edgecolor='green', linewidth=2))
    ax.text(6, 8.5, '潜空间', ha='center', fontsize=12, fontweight='bold', color='green')
    ax.text(6, 7.5, '64×64×4 = 16K 维', ha='center', fontsize=10)
    ax.text(6, 6.8, '此处扩散 = 快', ha='center', fontsize=9, style='italic')
    ax.annotate('', xy=(8.5, 7.5), xytext=(7.7, 7.5), arrowprops=dict(arrowstyle='->', color='blue', lw=2))
    ax.text(8.1, 7.8, '解码器', ha='center', fontsize=9, color='blue')
    ax.add_patch(FancyBboxPatch((8.5, 6), 1.5, 3, boxstyle="round,pad=0.1",
                                   facecolor='lightblue', edgecolor='blue', linewidth=2))
    ax.text(9.25, 8.5, '图片', ha='center', fontsize=10, fontweight='bold')
    ax.text(5, 4.5, 'Stable Diffusion 核心洞见：\n在潜空间扩散，而非像素空间', 
            ha='center', fontsize=10, style='italic', color='red',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))
    ax.text(5, 2.5, 'VAE 编码器/解码器是预训练的\n扩散模型在潜变量上运行', 
            ha='center', fontsize=10)
    ax.axis('off')
    ax.set_title("潜空间扩散：Stable Diffusion 的核心创新")

    # 中图: 交叉注意力
    ax = axes[1]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.add_patch(FancyBboxPatch((0.5, 7), 2.5, 2, boxstyle="round,pad=0.1",
                                   facecolor='lightyellow', edgecolor='orange', linewidth=2))
    ax.text(1.75, 8.5, '文本提示', ha='center', fontsize=10, fontweight='bold')
    ax.text(1.75, 7.7, '"a cat on a\nsofa"', ha='center', fontsize=9)
    ax.annotate('', xy=(4, 8), xytext=(3.2, 8), arrowprops=dict(arrowstyle='->', color='orange', lw=2))
    ax.text(3.6, 8.3, 'CLIP', ha='center', fontsize=9, color='orange')
    ax.add_patch(FancyBboxPatch((4, 7), 1.5, 2, boxstyle="round,pad=0.05",
                                   facecolor='lightblue', edgecolor='blue', linewidth=1.5))
    ax.text(4.75, 8.5, 'K', ha='center', fontsize=11, fontweight='bold', color='blue')
    ax.text(4.75, 7.7, 'V', ha='center', fontsize=11, fontweight='bold', color='blue')
    ax.text(4.75, 7.2, '来自文本', ha='center', fontsize=8)
    ax.add_patch(FancyBboxPatch((4, 4.5), 1.5, 2, boxstyle="round,pad=0.05",
                                   facecolor='lightgreen', edgecolor='green', linewidth=1.5))
    ax.text(4.75, 6, 'Q', ha='center', fontsize=11, fontweight='bold', color='green')
    ax.text(4.75, 5.2, '来自图片\n特征', ha='center', fontsize=8)
    ax.add_patch(FancyBboxPatch((6.5, 5.5), 2, 2, boxstyle="round,pad=0.1",
                                   facecolor='plum', edgecolor='purple', linewidth=2))
    ax.text(7.5, 7, '交叉', ha='center', fontsize=11, fontweight='bold', color='purple')
    ax.text(7.5, 6.2, '注意力', ha='center', fontsize=11, fontweight='bold', color='purple')
    ax.text(7.5, 5.5, '$Q\\cdot K^{\\mathsf{T}}\\to V$', ha='center', fontsize=9)
    ax.annotate('', xy=(6.5, 6.5), xytext=(5.7, 7.5), arrowprops=dict(arrowstyle='->', color='blue', lw=1.5))
    ax.annotate('', xy=(6.5, 6.5), xytext=(5.7, 5.5), arrowprops=dict(arrowstyle='->', color='green', lw=1.5))
    ax.annotate('', xy=(8.1, 6.5), xytext=(7.4, 6.5), arrowprops=dict(arrowstyle='->', color='purple', lw=2))
    ax.text(9.0, 6.5, '文本引导的\n特征', ha='center', fontsize=9, 
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))
    ax.text(5, 2.5, '交叉注意力 = "为匹配这段文本，\n我该关注图像的哪里？"', 
            ha='center', fontsize=10, style='italic',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))
    ax.axis('off')
    ax.set_title('交叉注意力：文本如何引导图像生成')

    # 右图: 训练损失曲线
    ax = axes[2]
    np.random.seed(42)
    epochs = np.arange(0, 100)
    normal_loss = 2.0 * np.exp(-epochs / 30) + 0.1 + 0.05 * np.random.randn(100)
    large_lr = 2.0 * np.exp(-epochs / 20) + 0.3 * np.sin(epochs * 0.5) + 0.1 + 0.08 * np.random.randn(100)
    small_lr = 2.0 * np.exp(-epochs / 80) + 0.1 + 0.03 * np.random.randn(100)
    # GAN典型训练：剧烈振荡+模式坍塌
    gan_loss = 1.0 + 0.8 * np.sin(epochs * 0.3) * np.exp(-epochs / 200) + 0.4 * np.random.randn(100)
    ax.plot(epochs, normal_loss, 'b-', linewidth=2, label='扩散（正常学习率）', alpha=0.8)
    ax.plot(epochs, large_lr, 'r-', linewidth=1.5, label='扩散（学习率过大）', alpha=0.6)
    ax.plot(epochs, small_lr, 'g-', linewidth=1.5, label='扩散（学习率过小）', alpha=0.6)
    ax.plot(epochs, gan_loss, 'k--', linewidth=1.5, label='GAN（典型振荡）', alpha=0.5)
    ax.axhline(y=0.1, color='gray', linestyle='--', alpha=0.5)
    ax.text(70, 0.15, '收敛下限', fontsize=9, color='gray')
    ax.set_xlabel('训练轮次'); ax.set_ylabel('MSE 损失')
    ax.set_title('训练动态：对比 GAN，\n扩散训练意外地稳定')
    ax.legend(loc='upper right', fontsize=8); ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 100); ax.set_ylim(-0.5, 2.5)

    save(fig, 'fig_ch9_latent_crossattention_training.png')


# =============================================================================
# Ch3 SDE vs ODE + 采样器家族 + 多模态
# =============================================================================
def fig_ch3_sde_ode_samplers_multimodal():
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    # 左图: SDE vs ODE
    ax = axes[0]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.add_patch(Ellipse((5, 1.5), 6, 2, facecolor='lightgreen', edgecolor='green', linewidth=2, alpha=0.5))
    ax.text(5, 1.5, '数据分布 p(x)', ha='center', fontsize=10, fontweight='bold')
    ax.add_patch(Ellipse((5, 8.5), 8, 2, facecolor='lightcoral', edgecolor='red', linewidth=2, alpha=0.3))
    ax.text(5, 8.5, '噪声分布 N(0,I)', ha='center', fontsize=10, fontweight='bold')
    np.random.seed(123)
    for i in range(5):
        x_path = [5 + np.random.randn() * 0.3]
        y_path = [8.5]
        for step in range(20):
            y_path.append(y_path[-1] - 0.35)
            x_path.append(x_path[-1] + np.random.randn() * 0.15)
        ax.plot(x_path, y_path, 'b-', alpha=0.3, linewidth=1)
    for x_start in [3.5, 4.5, 5.5, 6.5]:
        y_path = np.linspace(8.5, 1.5, 25)
        x_path = x_start + (5 - x_start) * (1 - (y_path - 1.5) / 7) + 0.1 * np.sin((y_path - 1.5) * 2)
        ax.plot(x_path, y_path, 'r-', linewidth=2, alpha=0.8)
    ax.text(1.5, 5, 'SDE\n（随机）', ha='center', fontsize=10, color='blue', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))
    ax.text(8.5, 5, 'ODE\n（确定性）', ha='center', fontsize=10, color='red', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.3))
    ax.text(5, 0.3, 'SDE = 多条随机路径\nODE = 一条确定性路径（概率流）', 
            ha='center', fontsize=10, style='italic',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))
    ax.axis('off')
    ax.set_title('SDE vs ODE：扩散的两种视角')

    # 中图: 采样器家族
    ax = axes[1]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.text(5, 9, '扩散采样器', ha='center', fontsize=12, fontweight='bold')
    ax.add_patch(FancyBboxPatch((1, 6.2), 3, 2.5, boxstyle="round,pad=0.1",
                                   facecolor='lightblue', edgecolor='blue', linewidth=2))
    ax.text(2.5, 8.4, '随机性', ha='center', fontsize=10, fontweight='bold', color='blue')
    ax.text(2.5, 7.05, 'DDPM\nDPM++ 2S\nEuler a', ha='center', fontsize=8, linespacing=1.25)
    ax.add_patch(FancyBboxPatch((5.5, 6.2), 3, 2.5, boxstyle="round,pad=0.1",
                                   facecolor='lightyellow', edgecolor='orange', linewidth=2))
    ax.text(7, 8.4, '确定性', ha='center', fontsize=10, fontweight='bold', color='orange')
    ax.text(7, 6.95, 'DDIM\nDPM++ 2M\nEuler\nHeun', ha='center', fontsize=8, linespacing=1.2)
    ax.annotate('', xy=(2.5, 8.9), xytext=(5, 9.1), arrowprops=dict(arrowstyle='->', color='blue', lw=1.5))
    ax.annotate('', xy=(7, 8.9), xytext=(5, 9.1), arrowprops=dict(arrowstyle='->', color='orange', lw=1.5))
    ax.text(2.5, 5, '• 更多样\n• 质量更高\n• 更慢', ha='center', fontsize=9, color='blue')
    ax.text(7, 5, '• 可复现\n• 步数更少\n• 快', ha='center', fontsize=9, color='orange')
    ax.text(5, 2.5, '经验法则：\n重质量 → 随机（DPM++ 2S）\n重速度 → 确定性（DPM++ 2M）\n实时 → Euler', 
            ha='center', fontsize=10, style='italic',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))
    ax.axis('off')
    ax.set_title('采样器家族：如何选择？')

    # 右图: 多模态扩散
    ax = axes[2]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    modalities = [
        (2, 8, '图片', 'Stable Diffusion\nDALL-E\nMidjourney', 'lightblue', 'blue'),
        (5, 8, '音频', 'AudioLDM\nMusicLM\nWaveGrad', 'lightgreen', 'green'),
        (8, 8, '视频', 'Sora\nVideoLDM\nAnimateDiff', 'lightyellow', 'orange'),
        (2, 4.5, '3D', 'Point-E\nShape-E\nDreamFusion', 'plum', 'purple'),
        (5, 4.5, '分子', 'DiffDock\nGeoDiff', 'lightcoral', 'red'),
        (8, 4.5, '文本', 'DiffuSeq\nSeqDiff', 'wheat', 'brown'),
    ]
    for x, y, title, examples, fc, ec in modalities:
        box = FancyBboxPatch((x-0.9, y-1.3), 1.8, 2.5, boxstyle="round,pad=0.05",
                              facecolor=fc, edgecolor=ec, linewidth=2)
        ax.add_patch(box)
        ax.text(x, y+0.75, title, ha='center', fontsize=10, fontweight='bold', color=ec)
        ax.text(x, y-0.35, examples, ha='center', fontsize=7.5, linespacing=1.3)
    ax.text(5, 1.5, '相同的数学（前向加噪 + 反向去噪）\n不同的数据表示', 
            ha='center', fontsize=10, style='italic',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))
    ax.axis('off')
    ax.set_title('扩散超越图像：多模态')

    save(fig, 'fig_ch3_sde_ode_samplers_multimodal.png')


# =============================================================================
# 主函数：生成全部 41 张图
# =============================================================================

# Ch1 · 2d forward noising
def fig_ch1_2d_forward_noising():
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    np.random.seed(42)
    N = 800
    mu1, mu2, sig = np.array([2, 2]), np.array([-2, -2]), 0.5
    x0 = np.vstack([mu1 + sig * np.random.randn(N // 2, 2), mu2 + sig * np.random.randn(N // 2, 2)])

    for ax, t, color, title in zip(axes, [0, 1.0, 5.0],
                                     ['green', 'orange', 'red'],
                                     ['t=0: Original Data', 't=1.0: Partially Noised', 't=5.0: Near Pure Noise']):
        a_t = np.exp(-t / 2)
        s_t = np.sqrt(1 - np.exp(-t))
        xt = a_t * x0 + s_t * np.random.randn(*x0.shape)
        ax.scatter(xt[:, 0], xt[:, 1], c=color, alpha=0.3, s=8)
        ax.set_xlim(-6, 6); ax.set_ylim(-6, 6)
        ax.set_aspect('equal')
        ax.set_xlabel('x1'); ax.set_ylabel('x2')
        ax.set_title(title)
        ax.grid(True, alpha=0.2)
    save(fig, 'fig_ch1_2d_forward_noising.png')


# Ch1 · ve vp comparison
def fig_ch1_ve_vp_comparison():
    """VE vs VP——双峰数据分布在不同时刻的演化"""
    fig, axes = plt.subplots(2, 3, figsize=(14, 9))

    # 双峰数据: 两个高斯团在 (2,2) 和 (-2,-2)
    np.random.seed(42)
    n_pts = 200
    cluster1 = np.random.randn(n_pts, 2) * 0.3 + [2, 2]
    cluster2 = np.random.randn(n_pts, 2) * 0.3 + [-2, -2]
    data = np.vstack([cluster1, cluster2])

    t_values = [0, 1.0, 3.0]
    t_labels = ['$t=0$\\n(data)', '$t=1$', '$t=3$']
    blue = '#4A90D9'
    red = '#FF4444'

    for col, (t, tlabel) in enumerate(zip(t_values, t_labels)):
        # ---- VE row ----
        ax = axes[0, col]
        if t == 0:
            ax.scatter(data[:, 0], data[:, 1], s=8, c=blue, alpha=0.4)
            ax.set_title(f'VE  {tlabel}', fontsize=11)
        else:
            sigma_ve = np.sqrt(t)  # VE: sigma = sqrt(t)
            noisy = data + np.random.randn(len(data), 2) * sigma_ve
            ax.scatter(noisy[:, 0], noisy[:, 1], s=8, c=red if t > 0 else blue, alpha=0.3)
            # Draw noise circle (radius = 2*sigma for visibility)
            theta = np.linspace(0, 2 * np.pi, 100)
            ax.plot(2 * sigma_ve * np.cos(theta), 2 * sigma_ve * np.sin(theta),
                    '--', color='gray', alpha=0.5, linewidth=1)
            ax.set_title(f'VE  {tlabel}\n$\\sigma_t=\\sqrt{{{t}}}={sigma_ve:.2f}$, $a_t=1$', fontsize=10)
        ax.set_xlim(-8, 8); ax.set_ylim(-8, 8)
        ax.set_aspect('equal'); ax.axis('off')

        # ---- VP row ----
        ax = axes[1, col]
        a_vp = np.exp(-t / 2)       # VP: a_t = e^{-t/2}
        sigma_vp = np.sqrt(1 - np.exp(-t))  # VP: sigma = sqrt(1-e^{-t})
        scaled = data * a_vp
        noisy = scaled + np.random.randn(len(data), 2) * sigma_vp
        color = blue if t == 0 else red
        ax.scatter(noisy[:, 0], noisy[:, 1], s=8, c=color, alpha=0.3)
        # Unit variance circle (VP total variance = 1)
        theta = np.linspace(0, 2 * np.pi, 100)
        ax.plot(np.cos(theta), np.sin(theta), '--', color='gray', alpha=0.5, linewidth=1)
        if t == 0:
            ax.set_title(f'VP  {tlabel}', fontsize=11)
        else:
            ax.set_title(f'VP  {tlabel}\n$a_t=e^{{-t/2}}={a_vp:.3f}$, $\\sigma_t={sigma_vp:.3f}$', fontsize=10)
        ax.set_xlim(-3.5, 3.5); ax.set_ylim(-3.5, 3.5)
        ax.set_aspect('equal'); ax.axis('off')

    # Row labels
    fig.text(0.02, 0.72, 'VE\n信号固定\n方差 $\\to \\infty$', fontsize=12,
             ha='center', va='center', fontweight='bold', color='#555555')
    fig.text(0.02, 0.28, 'VP\n信号收缩\n方差 $=1$', fontsize=12,
             ha='center', va='center', fontweight='bold', color='#555555')

    # Arrow showing time direction
    for row in range(2):
        ax = axes[row, 0]
        ax.annotate('', xy=(-0.3, -0.15), xycoords='axes fraction',
                    xytext=(-0.3, 1.15), arrowprops=dict(arrowstyle='->', color='gray', lw=1.5))

    fig.text(0.5, 0.02, '灰色虚线圆：VE 显示 $2\\sigma_t$ 噪声半径（增长）；VP 显示单位方差边界（固定）',
             ha='center', fontsize=9, color='#555555')
    plt.tight_layout(rect=(0.05, 0.04, 1, 1))
    save(fig, 'fig_ch1_ve_vp_comparison.png')


# Ch1 · discrete continuous bridge
def fig_ch1_discrete_continuous_bridge():
    fig, ax = plt.subplots(figsize=(8, 5))
    t = np.arange(0, 1001)
    beta = np.linspace(0.0001, 0.02, 1000)
    alpha_bar = np.concatenate([[1.0], np.cumprod(1 - beta)])
    ax.plot(t, np.sqrt(alpha_bar), 'b-', linewidth=2, label=r'信号 $\sqrt{\bar{\alpha}_t}$')
    ax.plot(t, np.sqrt(1 - alpha_bar), 'r-', linewidth=2, label=r'噪声 $\sqrt{1-\bar{\alpha}_t}$')
    t_disc = np.arange(0, 1001, 100)
    ax.scatter(t_disc, np.sqrt(alpha_bar[t_disc]), c='blue', s=50, zorder=5, label='离散步')
    ax.annotate('离散步\n是对连续曲线\n的采样', xy=(500, 0.65), fontsize=10,
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.set_xlabel('时间步 t'); ax.set_ylabel('系数')
    ax.set_title('离散步 = 连续 SDE 的采样')
    ax.set_xlim(0, 1000); ax.set_ylim(0, 1.1); ax.grid(True, alpha=0.3); ax.legend()
    save(fig, 'fig_ch1_discrete_continuous_bridge.png')


# Ch2 · multiscale score field
def fig_ch2_multiscale_score_field():
    fig, axes = plt.subplots(1, 4, figsize=(18, 4))
    np.random.seed(42)
    N = 300
    data = np.vstack([np.array([2, 2]) + 0.3 * np.random.randn(N // 2, 2),
                      np.array([-2, -2]) + 0.3 * np.random.randn(N // 2, 2)])
    grid = np.linspace(-4, 4, 15)
    X, Y = np.meshgrid(grid, grid)

    for ax, sigma, title in zip(axes, [0.3, 0.8, 1.5, 3.0],
                                 ['σ=0.3 (low noise)', 'σ=0.8', 'σ=1.5', 'σ=3.0 (high noise)']):
        # Compute p_t and score on grid
        P = np.zeros_like(X)
        sx = np.zeros_like(X); sy = np.zeros_like(X)
        for i in range(X.shape[0]):
            for j in range(X.shape[1]):
                x = np.array([X[i, j], Y[i, j]])
                diffs = x - data
                kers = np.exp(-np.sum(diffs**2, axis=1) / (2 * sigma**2))
                p_val = np.mean(kers) / (2 * np.pi * sigma**2)
                P[i, j] = p_val
                # Score = (E[x0|xt=x] - x) / sigma^2 ≈ weighted mean of (data - x) / sigma^2
                weights = kers / (kers.sum() + 1e-10)
                mean_x0 = np.sum(data * weights[:, None], axis=0)
                s = (mean_x0 - x) / sigma**2
                sx[i, j] = s[0]; sy[i, j] = s[1]

        ax.contour(X, Y, P, levels=5, colors='gray', alpha=0.3, linewidths=0.5)
        # Normalize arrow magnitudes for consistent visual size across panels
        magnitudes = np.sqrt(sx**2 + sy**2)
        max_mag = np.max(magnitudes) + 1e-10
        sx_norm = sx / max_mag * 0.4  # fixed visual length
        sy_norm = sy / max_mag * 0.4
        ax.quiver(X, Y, sx_norm, sy_norm, color='red', alpha=0.7, scale=1, width=0.004, pivot='middle')
        ax.set_title(title)
        ax.set_xlim(-4, 4); ax.set_ylim(-4, 4); ax.set_aspect('equal')
        ax.set_xlabel('x1'); ax.set_ylabel('x2')
    save(fig, 'fig_ch2_multiscale_score_field.png')


# Ch2 · tweedie geometry
def fig_ch2_tweedie_geometry():
    fig, ax = plt.subplots(figsize=(7, 6))
    # Background contour
    x = np.linspace(-1, 5, 50); y = np.linspace(-1, 5, 50)
    X, Y = np.meshgrid(x, y)
    Z = np.exp(-((X - 3)**2 + (Y - 3)**2) / 1.5)
    ax.contour(X, Y, Z, levels=5, colors='gray', alpha=0.2, linewidths=0.5)

    xt = np.array([1.5, 1.5])
    denoised = np.array([3.0, 3.0])
    sigma2 = 1.5

    ax.plot(*xt, 'o', color='red', markersize=12, zorder=5, label='$x_t$（噪声观测）')
    ax.plot(*denoised, 'o', color='green', markersize=12, zorder=5, label='$E[X_0|X_t]$（去噪估计）')
    ax.annotate('', xy=denoised, xytext=xt,
                arrowprops=dict(arrowstyle='->', color='blue', lw=2.5))
    ax.text(2.2, 2.0, '去噪\n方向', color='blue', fontsize=9)

    score_dir = (denoised - xt) / sigma2
    score_end = xt + 0.6 * score_dir
    ax.annotate('', xy=score_end, xytext=xt,
                arrowprops=dict(arrowstyle='->', color='red', lw=2.5))
    ax.text(0.3, 2.3, '分数 $s$ =\n（去噪估计 − $x_t$）$/\\sigma^2$', color='red', fontsize=9)

    ax.text(0.5, 4.5, 'Tweedie：分数 = 去噪方向 $/\\sigma^2$',
            fontsize=11, bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.set_title('Tweedie 恒等式：分数 = 去噪方向')
    ax.set_xlabel('x1'); ax.set_ylabel('x2')
    ax.set_xlim(-1, 5); ax.set_ylim(-1, 5); ax.set_aspect('equal')
    ax.grid(True, alpha=0.2); ax.legend(loc='lower right')
    save(fig, 'fig_ch2_tweedie_geometry.png')


# Ch2 · epsilon score equivalence
def fig_ch2_epsilon_score_equivalence():
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(0, 0, 'ko', markersize=12, zorder=5, label='$x_t$')

    eps = np.array([0.7, 0.7])
    sigma_t = 1.0
    score = -eps / sigma_t

    ax.annotate('', xy=eps, xytext=[0, 0], arrowprops=dict(arrowstyle='->', color='blue', lw=3))
    ax.text(0.4, 0.85, r'$\epsilon_\theta$（预测噪声）', color='blue', fontsize=10)

    ax.annotate('', xy=score, xytext=[0, 0], arrowprops=dict(arrowstyle='->', color='red', lw=3))
    ax.text(-1.8, -0.9, r'$s_\theta = -\epsilon_\theta / \sigma_t$（分数）', color='red', fontsize=10)

    ax.plot([eps[0], score[0]], [eps[1], score[1]], 'k--', alpha=0.3)

    ax.text(-0.8, 0.5, '同一份信息，\n方向相反', fontsize=10, ha='center',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.text(0, -1.5, r'$\epsilon_\theta = -\sigma_t \cdot s_\theta$  (Tweedie)', fontsize=12, ha='center',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.set_title('噪声预测 ↔ 分数估计')
    ax.set_xlabel('x1'); ax.set_ylabel('x2')
    ax.set_xlim(-2, 2); ax.set_ylim(-2, 2); ax.set_aspect('equal')
    ax.grid(True, alpha=0.2); ax.legend()
    save(fig, 'fig_ch2_epsilon_score_equivalence.png')


# Ch3 · forward reverse combined
def fig_ch3_forward_reverse_combined():
    fig, ax = plt.subplots(figsize=(10, 5.5))
    x0 = 2.0
    T = 1000
    beta = np.linspace(0.0001, 0.02, T)
    alpha_bar = np.cumprod(1 - beta)

    # 时间轴（含 t=0 数据点）与信号包络
    t_full = np.concatenate([[0], np.arange(1, T + 1)])
    mu = np.concatenate([[x0], np.sqrt(alpha_bar) * x0])        # 信号均值 √ᾱ·x0: 2 → ~0
    sigma = np.concatenate([[0.0], np.sqrt(1 - alpha_bar)])     # 噪声 std √(1-ᾱ): 0 → ~1

    # 1. 状态分布漏斗（±2σ）：数据端窄、噪声端宽——这就是"同一条统计路径"
    ax.fill_between(t_full, mu - 2 * sigma, mu + 2 * sigma,
                    color='#9dc3e6', alpha=0.7, label=r'状态分布 $\mu_t \pm 2\sigma_t$')
    # 2. 信号均值中心线（确定性骨架）
    ax.plot(t_full, mu, '--', color='#5b9bd5', lw=1.8,
            label=r'信号均值 $\sqrt{\bar\alpha_t}\,x_0$')

    ts = [0, 120, 280, 480, 720, 1000]

    # 3. 前向 realization（蓝）：从数据 x0 加噪到纯噪声
    np.random.seed(7)
    fwd = []
    for t in ts:
        if t == 0:
            fwd.append(x0)
        else:
            ab = alpha_bar[t - 1]
            fwd.append(np.sqrt(ab) * x0 + np.sqrt(1 - ab) * np.random.randn())
    xT = fwd[-1]  # 噪声终点——反向与前向共享这一端

    # 4. 反向 realization（橙）：从同一噪声点去噪回同一数据点，中间是另一次随机行走
    np.random.seed(31)
    rev = [0.0] * len(ts)
    rev[0], rev[-1] = x0, xT
    for i, t in enumerate(ts[1:-1], start=1):
        ab = alpha_bar[t - 1]
        rev[i] = np.sqrt(ab) * x0 + np.sqrt(1 - ab) * np.random.randn()

    ax.plot(ts, fwd, '-o', color='#1f5fb0', lw=2.5, ms=8, zorder=5, label='前向轨迹（一次采样）')
    ax.plot(ts, rev, '-o', color='#e8833a', lw=2.5, ms=8, zorder=5, alpha=0.9, label='反向轨迹（一次采样）')

    # 端点：两条轨迹在数据点与噪声点严格交汇
    ax.scatter([0], [x0], c='#228b22', s=200, zorder=7, edgecolors='white', linewidths=1.5)
    ax.text(-8, x0 + 0.35, r'数据 $x_0$', ha='left', color='#228b22', fontsize=12, fontweight='bold')
    ax.scatter([T], [xT], c='#555555', s=200, zorder=7, edgecolors='white', linewidths=1.5)
    ax.text(T, xT + 0.35, r'纯噪声 $x_T$', ha='right', color='#555555', fontsize=12, fontweight='bold')

    # 方向箭头：前向 → 在上，反向 ← 在下
    ax.annotate('', xy=(940, 3.15), xytext=(60, 3.15),
                arrowprops=dict(arrowstyle='-|>', color='#1f5fb0', lw=2.2))
    ax.text(500, 3.32, '前向：加噪（无需学习）', ha='center', color='#1f5fb0', fontsize=11, fontweight='bold')
    ax.annotate('', xy=(60, -2.55), xytext=(940, -2.55),
                arrowprops=dict(arrowstyle='-|>', color='#e8833a', lw=2.2))
    ax.text(500, -2.95, '反向：去噪（神经网络学习）', ha='center', color='#e8833a', fontsize=11, fontweight='bold')

    ax.set_xlabel('时间步 t（0=数据　1000=纯噪声）')
    ax.set_ylabel('状态 x')
    ax.set_title('前向与反向：同起点、同终点，两个方向共享一条统计路径')
    ax.set_xlim(-30, 1030)
    ax.set_ylim(-3.4, 3.7)
    ax.legend(loc='center right', fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.25)
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)
    save(fig, 'fig_ch3_forward_reverse_combined.png')


# Ch3 · ddpm ncsn comparison
def fig_ch3_ddpm_ncsn_comparison():
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    np.random.seed(42)
    x = np.linspace(-4, 4, 100); y = np.linspace(-4, 4, 100)
    X, Y = np.meshgrid(x, y)
    Z = np.exp(-((X-2)**2+(Y-2)**2)/0.5) + 0.9*np.exp(-((X+2)**2+(Y+2)**2)/0.5)

    for ax, title, color, is_vp in zip(axes,
            ['DDPM (VP): signal shrinks back + denoise', 'NCSN (VE): pure score + noise walk'],
            ['blue', 'red'], [True, False]):
        ax.contour(X, Y, Z, levels=6, colors='gray', alpha=0.2, linewidths=0.5)
        pos = np.array([0.0, 0.0])
        traj = [pos.copy()]
        n_steps = 80 if is_vp else 150
        eta = 0.05 if is_vp else 0.03

        for _ in range(n_steps):
            # Score toward nearest peak
            d1 = pos - np.array([2, 2])
            d2 = pos - np.array([-2, -2])
            w1 = np.exp(-np.sum(d1**2)/0.5)
            w2 = np.exp(-np.sum(d2**2)/0.5) * 0.9
            score = -(d1 * w1 + d2 * w2) / (w1 + w2 + 1e-8) / 0.25

            if is_vp:
                pos = pos + eta * (0.5 * pos + score) + np.sqrt(eta) * np.random.randn(2)
            else:
                pos = pos + eta * score + np.sqrt(2 * eta) * np.random.randn(2)
            traj.append(pos.copy())

        traj = np.array(traj)
        ax.plot(traj[:, 0], traj[:, 1], '-', color=color, alpha=0.5, linewidth=1)
        ax.scatter(traj[0, 0], traj[0, 1], c='red', s=100, zorder=5, label='起点（噪声）')
        ax.scatter(traj[-1, 0], traj[-1, 1], c='green', s=100, zorder=5, label='终点（数据）')
        ax.set_title(title)
        ax.set_xlabel('x1'); ax.set_ylabel('x2')
        ax.set_xlim(-5, 5); ax.set_ylim(-5, 5); ax.set_aspect('equal')
        ax.grid(True, alpha=0.2); ax.legend(loc='upper left', fontsize=8)

    fig.suptitle('Same reverse SDE, different discretization', fontsize=11, style='italic', y=0.02)
    save(fig, 'fig_ch3_ddpm_ncsn_comparison.png')


# Ch3 · reverse sde drift decomposition
def fig_ch3_reverse_sde_drift_decomposition():
    fig, ax = plt.subplots(figsize=(7, 6))
    origin = np.array([2.0, 2.0])
    f_neg = np.array([-1.0, -1.0]) * 0.3  # -f toward origin
    g2s = np.array([0.5, 0.5]) * 0.5      # g²·s toward data
    combined = f_neg + g2s

    ax.annotate('', xy=origin + f_neg, xytext=origin,
                arrowprops=dict(arrowstyle='->', color='blue', lw=3))
    ax.text(origin[0]+f_neg[0]-0.3, origin[1]+f_neg[1]-0.3, r'$-f(x)$'+'\n输运', color='blue', fontsize=9)

    ax.annotate('', xy=origin + g2s, xytext=origin,
                arrowprops=dict(arrowstyle='->', color='red', lw=3))
    ax.text(origin[0]+g2s[0]+0.1, origin[1]+g2s[1]+0.1, r'$g^2 s(x)$'+'\n分数修正', color='red', fontsize=9)

    ax.annotate('', xy=origin + combined, xytext=origin,
                arrowprops=dict(arrowstyle='->', color='green', lw=3))
    ax.text(origin[0]+combined[0]+0.1, origin[1]+combined[1]-0.3, r'$-f + g^2 s$'+'\n合成漂移', color='green', fontsize=9)

    ax.plot(*origin, 'ko', markersize=8)
    ax.text(origin[0]-0.3, origin[1]-0.3, 'x', fontsize=12)
    ax.set_title('反向 SDE 漂移 = 输运 + 分数修正')
    ax.set_xlabel('x1'); ax.set_ylabel('x2')
    ax.set_xlim(0, 4); ax.set_ylim(0, 4); ax.set_aspect('equal')
    ax.grid(True, alpha=0.2)
    save(fig, 'fig_ch3_reverse_sde_drift_decomposition.png')


# Ch4 · unified training
def fig_ch4_unified_training():
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 12); ax.set_ylim(0, 8)

    # DDPM row (top)
    ddpm_items = [(1, 6.5, '$x_0$', 'lightblue'), (3, 6.5, '+ε', 'lightblue'),
                  (5, 6.5, '$x_t$', 'lightblue'), (7.5, 6.5, 'UNet', 'lightblue'),
                  (9.5, 6.5, 'ε_θ', 'lightblue'), (11.5, 6.5, '||ε-ε_θ||²', 'lightblue')]
    for x, y, label, c in ddpm_items:
        box = FancyBboxPatch((x-0.6, y-0.4), 1.2, 0.8, boxstyle="round,pad=0.05",
                              facecolor=c, edgecolor='blue', linewidth=1.5)
        ax.add_patch(box)
        ax.text(x, y, label, ha='center', va='center', fontsize=10)
    for i in range(len(ddpm_items)-1):
        ax.annotate('', xy=(ddpm_items[i+1][0]-0.6, 6.5), xytext=(ddpm_items[i][0]+0.6, 6.5),
                    arrowprops=dict(arrowstyle='->', color='blue', lw=1.5))
    ax.text(6, 7.5, 'DDPM（VP）', ha='center', fontsize=12, color='blue', fontweight='bold')

    # NCSN row (bottom)
    ncsn_items = [(1, 2, '$x_0$', 'lightyellow'), (3, 2, '$+\\sigma Z$', 'lightyellow'),
                  (5, 2, '$x_t$', 'lightyellow'), (7.5, 2, 'UNet', 'lightyellow'),
                  (9.5, 2, '$s_\\theta$', 'lightyellow'), (11.5, 2, '$\\|s_\\theta{+}Z/\\sigma\\|^2$', 'lightyellow')]
    for x, y, label, c in ncsn_items:
        box = FancyBboxPatch((x-0.6, y-0.4), 1.2, 0.8, boxstyle="round,pad=0.05",
                              facecolor=c, edgecolor='orange', linewidth=1.5)
        ax.add_patch(box)
        ax.text(x, y, label, ha='center', va='center', fontsize=10)
    for i in range(len(ncsn_items)-1):
        ax.annotate('', xy=(ncsn_items[i+1][0]-0.6, 2), xytext=(ncsn_items[i][0]+0.6, 2),
                    arrowprops=dict(arrowstyle='->', color='orange', lw=1.5))
    ax.text(6, 1, 'NCSN（VE）', ha='center', fontsize=12, color='orange', fontweight='bold')

    # Connection
    ax.text(6, 4.25, 'Tweedie：$\\epsilon_\\theta = -\\sigma_t \\cdot s_\\theta$', ha='center', fontsize=13,
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
    ax.text(6, 4.75, '相同的总体目标，\n不同的参数化', ha='center', fontsize=10, style='italic')
    ax.set_title('统一训练：DDPM ε-MSE = NCSN 分数匹配')
    ax.axis('off')
    save(fig, 'fig_ch4_unified_training.png')


# Ch4 · training loss by t
def fig_ch4_training_loss_by_t():
    fig, ax = plt.subplots(figsize=(8, 5))
    t = np.arange(1, 1001)
    beta = np.linspace(0.0001, 0.02, 1000)
    alpha_bar = np.cumprod(1 - beta)
    # 信噪比 SNR = ᾱ_t / (1 - ᾱ_t)，可直接从调度算出
    snr = alpha_bar / (1 - alpha_bar + 1e-10)
    ax.semilogy(t, snr, 'b-', linewidth=2.5, label='SNR $= \\bar{\\alpha}_t / (1-\\bar{\\alpha}_t)$')
    ax.axvspan(1, 200, alpha=0.1, color='red', label='高SNR：信号清晰 → 须预测细节（难）')
    ax.axvspan(800, 1000, alpha=0.1, color='green', label='低SNR：信号淹没 → 只需粗略方向（易）')
    ax.set_xlabel('时间步 t')
    ax.set_ylabel('信噪比 SNR（对数轴）')
    ax.set_title('不同 t 的信噪比：决定网络需要学什么')
    ax.set_xlim(0, 1000); ax.grid(True, alpha=0.3, which='both')
    ax.legend(loc='upper right', fontsize=9)
    # 补充说明
    ax.text(500, snr[499] * 1.5,
            '高 SNR → 细节可辨 → 分数方向复杂\n低 SNR → 只剩轮廓 → 分数方向简单',
            fontsize=9, ha='center', style='italic',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.7))
    save(fig, 'fig_ch4_training_loss_by_t.png')


# Ch5 · three error sources
# 每个子图对应表格一行：误差 vs 它各自的控制变量（T / N / 网络质量）。
# 第3子图：固定 T 时分数项 ≈ c·T·ε² 是常数地板，故总 KL 随 N 单调降至地板。
def fig_ch5_three_error_sources():
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    # --- 子图1：初始化误差 vs 终止时刻 T（指数衰减，OU 过程收缩）---
    ax = axes[0]
    T = np.linspace(0.1, 5, 200)
    eps_init = np.exp(-T / 2)          # VP: ε_init ∝ e^{-T/2}（正文 §5.4）
    ax.plot(T, eps_init, '-', color='#1f4e79', linewidth=2.5,
            label=r'$\varepsilon_{\rm init}\propto e^{-T/2}$')
    for Tv, txt in [(1, 'T=1'), (4, 'T=4')]:
        ax.axvline(Tv, color='#888', linestyle=':', linewidth=1)
        ax.scatter([Tv], [np.exp(-Tv / 2)], color='#c00', s=45, zorder=5)
    ax.text(4.05, np.exp(-2) + 0.05, 'T=1~4 已足够',
            fontsize=9, color='#c00', fontproperties=CJK_FONT_NAME)
    ax.set_xlabel('终止时刻 $T$（前向跑多久）'); ax.set_ylabel(r'初始化误差 $\varepsilon_{\rm init}$')
    ax.set_title('初始化误差：随 $T$ 指数衰减')
    ax.legend(loc='upper right', fontsize=10); ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1.02)

    # --- 子图2：离散化误差 vs 离散步数 N（一阶 vs 二阶，log-log 看斜率）---
    ax = axes[1]
    N = np.logspace(np.log10(10), np.log10(1000), 100)
    euler = 1.0 / N                    # 一阶 Euler：O(1/N)，斜率 -1
    second = 3.0 / N**2               # 二阶方法：O(1/N^2)，斜率 -2
    ax.loglog(N, euler, '-', color='#1f4e79', linewidth=2.5, label=r'一阶 Euler $O(1/N)$')
    ax.loglog(N, second, '--', color='#5b9bd5', linewidth=2.5, label=r'二阶方法 $O(1/N^2)$')
    for Nv, txt, dy in [(20, 'DDIM≈20', 1.6), (1000, 'DDPM=1000', 1.6)]:
        ax.axvline(Nv, color='#888', linestyle=':', linewidth=1)
        ax.text(Nv, euler[np.argmin(np.abs(N - Nv))] * dy, txt,
                fontsize=8, color='#555', ha='center', fontproperties=CJK_FONT_NAME)
    ax.set_xlabel('离散步数 $N$'); ax.set_ylabel(r'离散化误差 $\varepsilon_{\rm disc}$')
    ax.set_title('离散化误差：随 $N$ 下降\n（高阶求解器掉得更快）')
    ax.legend(loc='lower left', fontsize=10, prop=CJK_FONT_NAME); ax.grid(True, which='both', alpha=0.3)

    # --- 子图3：总 KL vs N —— 单调降趋于"分数误差地板"，无假U形 ---
    ax = axes[2]
    N3 = np.logspace(np.log10(5), np.log10(300), 100)
    init_sq = np.exp(-2 * 3.0)        # T=3 时 ε_init^2，很小
    disc_sq = (1.5 / N3)**2           # ε_disc^2 ∝ 1/N^2，随 N 单调降
    floor_good, floor_bad = 0.010, 0.040   # 分数项 c·T·ε^2：常数地板，不随 N 变
    kl_good = init_sq + disc_sq + floor_good
    kl_bad = init_sq + disc_sq + floor_bad
    ax.loglog(N3, kl_bad, '-', color='#9dc3e6', linewidth=2.5, label='总 KL（弱网络）')
    ax.loglog(N3, kl_good, '-', color='#1f4e79', linewidth=2.5, label='总 KL（强网络）')
    ax.axhline(floor_bad, color='#9dc3e6', linestyle=':', linewidth=1.5)
    ax.axhline(floor_good, color='#1f4e79', linestyle=':', linewidth=1.5)
    ax.text(300, floor_good * 1.12, '分数误差地板（强）', fontsize=8,
            color='#1f4e79', ha='right', fontproperties=CJK_FONT_NAME)
    ax.text(300, floor_bad * 1.12, '分数误差地板（弱）', fontsize=8,
            color='#5b9bd5', ha='right', fontproperties=CJK_FONT_NAME)
    ax.annotate('增大 N 只让离散化误差下降，\n压不过分数误差地板', xy=(150, kl_good[np.argmin(np.abs(N3 - 150))]),
                xytext=(9, 0.0088), fontsize=8.5, color='#444', fontproperties=CJK_FONT_NAME,
                arrowprops=dict(arrowstyle='->', color='#444'))
    ax.set_xlabel('离散步数 $N$'); ax.set_ylabel('总 KL 散度')
    ax.set_title('总误差：随 $N$ 单调降至地板\n（地板由网络质量决定）')
    ax.set_ylim(0.0075, 0.16)
    ax.legend(loc='upper right', fontsize=9, prop=CJK_FONT_NAME); ax.grid(True, which='both', alpha=0.3)

    save(fig, 'fig_ch5_three_error_sources.png')


# Ch5 · sde ode density match
def fig_ch5_sde_ode_density_match():
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    x = np.linspace(-5, 5, 200)
    colors = plt.cm.Blues(np.linspace(0.3, 0.9, 5))
    labels = ['t=0.0', 't=0.25', 't=0.5', 't=0.75', 't=1.0']

    densities = []
    for i, t in enumerate([0.0, 0.25, 0.5, 0.75, 1.0]):
        sig = 0.5 + t * 1.5
        p = 0.5 * np.exp(-(x - 2)**2 / (2 * sig**2)) / (sig * np.sqrt(2 * np.pi)) + \
            0.5 * np.exp(-(x + 2)**2 / (2 * sig**2)) / (sig * np.sqrt(2 * np.pi))
        densities.append(p)
        axes[0].plot(x, p, color=colors[i], linewidth=2, label=labels[i])
        axes[1].plot(x, p, color=colors[i], linewidth=2, label=labels[i])

    # SDE: overlay noisy stochastic paths
    np.random.seed(7)
    for _ in range(4):
        x0 = np.random.choice([-2, 2]) + np.random.randn() * 0.3
        path_x = [x0]
        for step in range(50):
            path_x.append(path_x[-1] + 0.05 * (-path_x[-1] * 0.3) + np.random.randn() * 0.15)
        path_t = np.linspace(0, 1, 51)
        axes[0].plot(path_x, path_t * 4 - 0.5, 'r-', alpha=0.25, linewidth=0.8)
    axes[0].text(0, -0.3, '红色: 随机样本路径（有噪声）', fontsize=8, color='red', ha='center', alpha=0.7)

    # ODE: overlay smooth deterministic paths
    for x0 in [-3, -1.5, 0, 1.5, 3]:
        path_x = [x0]
        for step in range(50):
            path_x.append(path_x[-1] + 0.05 * (-path_x[-1] * 0.3))
        path_t = np.linspace(0, 1, 51)
        axes[1].plot(path_x, path_t * 4 - 0.5, 'g-', alpha=0.3, linewidth=1.2)
    axes[1].text(0, -0.3, '绿色: 确定性流线（无噪声）', fontsize=8, color='green', ha='center', alpha=0.7)

    for ax, title in zip(axes, ['SDE: 随机扩散 + 漂移\n（路径有噪声）',
                                  'ODE: 确定性传输\n（路径光滑）']):
        ax.set_title(title); ax.set_xlabel('x'); ax.set_ylabel('密度 $p_t(x)$')
        ax.set_xlim(-5, 5); ax.set_ylim(-0.5, 0.45); ax.grid(True, alpha=0.3); ax.legend(fontsize=8, loc='upper right')
    fig.suptitle('不同机制，同一密度演化：$p_t(x)$ 完全相同', fontsize=13, y=1.02)
    plt.tight_layout()
    save(fig, 'fig_ch5_sde_ode_density_match.png')


# Ch7 · masked diffusion process
def fig_ch7_masked_diffusion_process():
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.set_xlim(0, 12); ax.set_ylim(0, 4)

    tokens_fwd = [['cat', 'sits', 'on', 'mat'], ['cat', '[M]', 'on', '[M]'], ['[M]', '[M]', '[M]', '[M]']]
    tokens_rev = [['[M]', '[M]', '[M]', '[M]'], ['[M]', 'sits', '[M]', 'mat'], ['cat', 'sits', 'on', 'mat']]

    for row, tokens_list, label, y_base in [(0, tokens_fwd, '前向\n掩码', 2.5), (1, tokens_rev, '反向\n解码', 0.5)]:
        for step, tokens in enumerate(tokens_list):
            x_start = 1 + step * 4
            for j, tok in enumerate(tokens):
                color = 'lightgreen' if tok != '[M]' else 'lightgray'
                box = FancyBboxPatch((x_start + j * 0.7, y_base), 0.6, 0.5, boxstyle="round,pad=0.05",
                                      facecolor=color, edgecolor='black', linewidth=1)
                ax.add_patch(box)
                ax.text(x_start + j * 0.7 + 0.3, y_base + 0.25, tok, ha='center', va='center', fontsize=9)
            if step < len(tokens_list) - 1:
                ax.annotate('', xy=(x_start + 4, y_base + 0.25), xytext=(x_start + 3, y_base + 0.25),
                            arrowprops=dict(arrowstyle='->', color='black', lw=1.5))
        ax.text(0.3, y_base + 0.25, label, ha='center', va='center', fontsize=9, rotation=0)

    ax.set_title('掩码扩散：token 级的前向与反向')
    ax.axis('off')
    save(fig, 'fig_ch7_masked_diffusion_process.png')


# Ch7 · continuous discrete parallel
def fig_ch7_continuous_discrete_parallel():
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Continuous
    ax = axes[0]
    circle1 = plt.Circle((3, 5), 0.5, color='green', alpha=0.5)
    ax.add_patch(circle1)
    circle2 = plt.Circle((3, 3), 1.0, color='orange', alpha=0.3)
    ax.add_patch(circle2)
    circle3 = plt.Circle((3, 1), 1.8, color='red', alpha=0.2)
    ax.add_patch(circle3)
    ax.text(3, 5, 'data', ha='center', fontsize=9)
    ax.text(3, 3, 't=0.5', ha='center', fontsize=9)
    ax.text(3, 1, 't=1.0', ha='center', fontsize=9)
    ax.text(6, 5, 'SDE', fontsize=10, color='blue')
    ax.text(6, 4, '分数 $\\nabla\\log p$', fontsize=10, color='blue')
    ax.text(6, 3, 'Tweedie', fontsize=10, color='blue')
    ax.set_title('连续扩散')
    ax.set_xlim(0, 8); ax.set_ylim(0, 6); ax.axis('off')

    # Discrete
    ax = axes[1]
    steps = [('A B C D', 'lightgreen'), ('A [M] C [M]', 'orange'), ('[M] [M] [M] [M]', 'lightgray')]
    for i, (seq, color) in enumerate(steps):
        y = 5 - i * 2
        ax.text(2, y, seq, fontsize=11, family='monospace',
                bbox=dict(boxstyle='round', facecolor=color, alpha=0.5))
        if i < 2:
            ax.annotate('', xy=(2, y - 1.2), xytext=(2, y - 0.5),
                        arrowprops=dict(arrowstyle='->', color='black', lw=1.5))
    ax.text(6, 5, 'CTMC', fontsize=10, color='blue')
    ax.text(6, 4, '比率分数\np(y)/p(x)', fontsize=10, color='blue')
    ax.text(6, 2, '后验\n去噪器', fontsize=10, color='blue')
    ax.set_title('离散扩散')
    ax.set_xlim(0, 8); ax.set_ylim(0, 6); ax.axis('off')

    fig.text(0.5, 0.02, '相同的贝叶斯结构，不同的状态空间', ha='center', fontsize=11, style='italic')
    save(fig, 'fig_ch7_continuous_discrete_parallel.png')


# Ch8 · video worldmodel
def fig_ch8_video_worldmodel():
    """视频生成 vs 世界模型：闭环 vs 开环 (文档引用文件名 fig_ch8_video_worldmodel.png)"""
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, 12); ax.set_ylim(0, 8)

    # Top: Video generation (open loop)
    ax.text(6, 7.5, '视频生成（开环）', ha='center', fontsize=12, fontweight='bold', color='blue')
    for i in range(5):
        box = FancyBboxPatch((1 + i * 2, 6), 1.5, 1, boxstyle="round,pad=0.05",
                              facecolor='lightblue', edgecolor='blue', linewidth=1.5)
        ax.add_patch(box)
        ax.text(1.75 + i * 2, 6.5, f'f{i+1}', ha='center', fontsize=10)
        if i < 4:
            ax.annotate('', xy=(1 + (i+1) * 2, 6.5), xytext=(2.5 + i * 2, 6.5),
                        arrowprops=dict(arrowstyle='->', color='blue', lw=1.5))
    ax.text(6, 5.5, '一次生成所有帧（无反馈）', ha='center', fontsize=10, style='italic', color='blue')

    ax.axhline(y=5, color='gray', linestyle='--', alpha=0.3)

    # Bottom: World model (closed loop)
    ax.text(6, 4.5, '世界模型（闭环）', ha='center', fontsize=12, fontweight='bold', color='green')
    for i in range(3):
        x_offset = 1 + i * 3.5
        # State
        box_s = FancyBboxPatch((x_offset, 2.5), 1.2, 0.8, boxstyle="round,pad=0.05",
                                facecolor='lightgreen', edgecolor='green', linewidth=1.5)
        ax.add_patch(box_s)
        ax.text(x_offset + 0.6, 2.9, f's_t', ha='center', fontsize=10)
        # Action
        diamond = Polygon([(x_offset + 2, 3.7), (x_offset + 2.5, 3.3), (x_offset + 2, 2.9), (x_offset + 1.5, 3.3)],
                          facecolor='lightyellow', edgecolor='orange', linewidth=1.5)
        ax.add_patch(diamond)
        ax.text(x_offset + 2, 3.3, f'a_t', ha='center', fontsize=9)
        # Diffusion model
        circ = Circle((x_offset + 3, 2.9), 0.35, facecolor='lightcoral', edgecolor='red', linewidth=1.5)
        ax.add_patch(circ)
        ax.text(x_offset + 3, 2.9, 'p(s)', ha='center', fontsize=8)

        ax.annotate('', xy=(x_offset + 1.5, 3.3), xytext=(x_offset + 1.2, 2.9),
                    arrowprops=dict(arrowstyle='->', color='orange', lw=1.5))
        ax.annotate('', xy=(x_offset + 2.65, 2.9), xytext=(x_offset + 2.5, 3.3),
                    arrowprops=dict(arrowstyle='->', color='red', lw=1.5))
        if i < 2:
            ax.annotate('', xy=(x_offset + 3.5 + 0.6, 2.9), xytext=(x_offset + 3.35, 2.9),
                        arrowprops=dict(arrowstyle='->', color='green', lw=1.5, linestyle='--'))

    ax.text(6, 1.5, '预测 → 行动 → 观察 → 重复', ha='center', fontsize=10, style='italic', color='green')
    ax.set_title('视频生成 vs 世界模型')
    ax.axis('off')
    save(fig, 'fig_ch8_video_worldmodel.png')


# Ch8 · frame consistency
def fig_ch8_frame_consistency():
    fig, axes = plt.subplots(2, 1, figsize=(10, 8))
    np.random.seed(42)
    frames = np.arange(10)

    # Independent (random)
    pos_indep = np.cumsum(np.random.randn(10) * 0.3)
    axes[0].plot(frames, pos_indep, 'r-o', linewidth=2, markersize=8)
    axes[0].set_title('独立生成每帧：物体会闪烁')
    axes[0].set_xlabel('帧序号'); axes[0].set_ylabel('小球位置')
    axes[0].grid(True, alpha=0.3)
    axes[0].annotate('帧间\n随机跳变', xy=(0.5, 0.88), xycoords='axes fraction',
                     fontsize=10, color='red', ha='center', va='top')

    # Joint (smooth)
    pos_joint = np.sin(frames * 0.5) * 0.5
    axes[1].plot(frames, pos_joint, 'b-o', linewidth=2, markersize=8)
    axes[1].set_title('联合时空生成：运动平滑')
    axes[1].set_xlabel('帧序号'); axes[1].set_ylabel('小球位置')
    axes[1].grid(True, alpha=0.3)
    axes[1].annotate('平滑轨迹\n（时间一致性）', xy=(0.5, 0.88), xycoords='axes fraction',
                     fontsize=10, color='blue', ha='center', va='top')

    plt.tight_layout()
    save(fig, 'fig_ch8_frame_consistency.png')


# Ch8 · spacetime attention
def fig_ch8_spacetime_attention():
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Full joint
    ax = axes[0]
    T, S = 3, 4
    points = [(s, t) for t in range(T) for s in range(S)]
    for i, (s1, t1) in enumerate(points):
        ax.plot(s1, t1, 'ko', markersize=8)
        for j, (s2, t2) in enumerate(points):
            if i < j:
                ax.plot([s1, s2], [t1, t2], 'gray', alpha=0.15, linewidth=0.5)
    ax.set_title('完全联合：O((n·T)²) — 太昂贵')
    ax.set_xlabel('空间位置'); ax.set_ylabel('时间步')
    ax.set_xlim(-0.5, 3.5); ax.set_ylim(-0.5, 2.5); ax.grid(True, alpha=0.2)

    # Factorized
    ax = axes[1]
    for t in range(T):
        for s in range(S):
            ax.plot(s, t, 'ko', markersize=8)
    # Spatial (within rows)
    for t in range(T):
        for s1 in range(S):
            for s2 in range(s1+1, S):
                ax.plot([s1, s2], [t, t], 'blue', alpha=0.3, linewidth=1)
    # Temporal (within columns)
    for s in range(S):
        for t1 in range(T):
            for t2 in range(t1+1, T):
                ax.plot([s, s], [t1, t2], 'orange', alpha=0.3, linewidth=1)
    ax.set_title('因子分解：O(n² + T²) — 实用')
    ax.set_xlabel('空间位置'); ax.set_ylabel('时间步')
    ax.set_xlim(-0.5, 3.5); ax.set_ylim(-0.5, 2.5); ax.grid(True, alpha=0.2)

    # Legend
    from matplotlib.lines import Line2D
    legend_elements = [Line2D([0], [0], color='blue', alpha=0.5, label='空间注意力'),
                       Line2D([0], [0], color='orange', alpha=0.5, label='时间注意力')]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=9)
    save(fig, 'fig_ch8_spacetime_attention.png')


# =============================================================================
# Ch8 扩散策略 vs 传统策略——多峰动作分布对比
# =============================================================================
def fig_ch8_diffusion_policy_multimodal():
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))

    a = np.linspace(-3, 3, 400)
    # 三个高斯峰：从左/上/右抓取
    p = (0.35 * np.exp(-((a + 1.6) ** 2) / (2 * 0.25))
         + 0.35 * np.exp(-((a - 1.6) ** 2) / (2 * 0.25))
         + 0.30 * np.exp(-(a ** 2) / (2 * 0.20)))

    # ---- 左：多峰动作分布 p(a|s) ----
    ax = axes[0]
    ax.fill_between(a, p, alpha=0.35, color='#4C72B0')
    ax.plot(a, p, color='#1F4E79', linewidth=1.8)
    for x, txt in [(-1.6, '从左抓'), (0, '从上抓'), (1.6, '从右抓')]:
        idx = np.argmin(np.abs(a - x))
        ax.plot(x, p[idx], 'o', color='#C44E52', markersize=8)
        ax.annotate(txt, xy=(x, p[idx]), xytext=(x, p[idx] + 0.12),
                    ha='center', fontsize=10, color='#333')
    ax.set_xlim(-3, 3); ax.set_ylim(0, 0.9)
    ax.set_xlabel('动作 a（抓取角度）', fontsize=11)
    ax.set_ylabel('概率密度 $p(a\\mid s)$', fontsize=11)
    ax.set_title('演示数据里的动作分布是多峰的\n$p(a\\mid s)$ 有 3 个模式（三种正确抓法）', fontsize=11)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.set_yticks([])

    # ---- 中：传统策略——回归到均值 ----
    ax = axes[1]
    ax.fill_between(a, p, alpha=0.18, color='#4C72B0')
    ax.plot(a, p, color='#4C72B0', linewidth=1.2, alpha=0.6)
    mean_a = np.sum(a * p) / np.sum(p)
    mean_idx = np.argmin(np.abs(a - mean_a))
    ax.axvline(mean_a, color='#C44E52', linewidth=2.5, linestyle='--')
    ax.annotate('', xy=(mean_a, 0.05), xytext=(mean_a, 0.7),
                arrowprops=dict(arrowstyle='->', color='#C44E52', lw=2.5))
    ax.text(mean_a, 0.78, f'$E[a\\mid s]$ ≈ {mean_a:.1f}\n（三峰平均）', ha='center',
            fontsize=10, color='#C44E52', fontweight='bold')
    ax.annotate('均值落在低概率区\n——手臂在空中犹豫\n没有一种真实抓法在这',
                xy=(mean_a, p[mean_idx]), xytext=(mean_a + 0.05, 0.35),
                fontsize=9, color='#333',
                arrowprops=dict(arrowstyle='->', color='#666', lw=1))
    ax.set_xlim(-3, 3); ax.set_ylim(0, 0.9)
    ax.set_xlabel('动作 a', fontsize=11)
    ax.set_title('传统策略：MSE 回归 → 只输出 $E[a\\mid s]$\n三种正确姿态被平均成一个"错误的中间"', fontsize=11)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.set_yticks([])

    # ---- 右：扩散策略——保留所有模式 ----
    ax = axes[2]
    ax.fill_between(a, p, alpha=0.35, color='#4A90D9')
    ax.plot(a, p, color='#1F4E79', linewidth=1.8)
    rng = np.random.default_rng(42)
    cdf = np.cumsum(p); cdf /= cdf[-1]
    samples = np.interp(rng.uniform(size=15), cdf, a)
    for s in samples:
        ax.axvline(s, ymin=0, ymax=0.15, color='#C44E52', lw=1.2, alpha=0.75)
    for x, arrow in [(-1.6, '←'), (0, '↑'), (1.6, '→')]:
        idx = np.argmin(np.abs(a - x))
        ax.annotate(arrow, xy=(x, p[idx]), xytext=(x, p[idx] + 0.05),
                    ha='center', fontsize=16, color='#1F4E79', fontweight='bold')
    ax.text(0, 0.78, '每次采样从多峰分布里\n落到某一个真实模式',
            ha='center', fontsize=10, color='#1F4E79', fontweight='bold')
    ax.set_xlim(-3, 3); ax.set_ylim(0, 0.9)
    ax.set_xlabel('动作 a', fontsize=11)
    ax.set_title('扩散策略：从 $p(a\\mid s)$ 里采样 → 保留多峰\n每次动作是一种真实抓法，多样但都能完成任务', fontsize=11)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.set_yticks([])

    plt.tight_layout()
    save(fig, 'fig_ch8_diffusion_policy_multimodal.png')


# Ch9 · inference rl
def fig_ch9_inference_rl():
    """推理时控制路线图 (文档引用文件名 fig_ch9_inference_rl.png)"""
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6)

    # Root
    root = FancyBboxPatch((3.5, 5), 3, 0.8, boxstyle="round,pad=0.1",
                           facecolor='gold', edgecolor='black', linewidth=2)
    ax.add_patch(root)
    ax.text(5, 5.4, '奖励倾斜目标 $p^\\beta$', ha='center', fontsize=10, fontweight='bold')

    # Three branches
    branches = [
        (1, 3, 'Exact Guidance', 'lightblue', 'Doob Transform\n(needs value $h_k$, intractable)'),
        (4, 3, 'Unbiased Approx', 'lightgreen', 'SMC / Feynman-Kac\n(particle filter, exact)'),
        (7, 3, 'Biased Approx', 'lightcoral', 'Inference-time RL\n(policy network, flexible)')
    ]

    for x, y, title, color, desc in branches:
        box1 = FancyBboxPatch((x, y), 2.5, 0.7, boxstyle="round,pad=0.05",
                               facecolor=color, edgecolor='black', linewidth=1.5)
        ax.add_patch(box1)
        ax.text(x + 1.25, y + 0.35, title, ha='center', fontsize=9, fontweight='bold')
        ax.annotate('', xy=(x + 1.25, y + 0.7), xytext=(5, 5),
                    arrowprops=dict(arrowstyle='->', color='gray', lw=1.5))

        box2 = FancyBboxPatch((x, y - 1.5), 2.5, 1.0, boxstyle="round,pad=0.05",
                               facecolor='white', edgecolor=color, linewidth=1, linestyle='--')
        ax.add_patch(box2)
        ax.text(x + 1.25, y - 1.0, desc, ha='center', fontsize=8)
        ax.annotate('', xy=(x + 1.25, y - 0.5), xytext=(x + 1.25, y),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1))

    ax.set_title('推理期控制：从奖励到采样器的三条路线')
    ax.axis('off')
    save(fig, 'fig_ch9_inference_rl.png')


# Ch9 · flow matching vs diffusion
def fig_ch9_flow_matching_vs_diffusion():
    """Ch9 §9.1: 扩散 vs 流匹配 vs 一致性模型——相同起终点，不同路径"""
    fig, ax = plt.subplots(figsize=(8, 7))
    np.random.seed(7)

    # 共同起终点：噪声 (t=1, 底部) → 数据 (t=0, 顶部)
    x_noise, t_noise = 0.2, 1.0
    x_data, t_data = 0.8, 0.0

    # 1. 扩散 SDE：弯曲随机路径，多步
    n_steps = 40
    t_sde = np.linspace(t_noise, t_data, n_steps)
    # 从噪声到数据的直线 + 随机偏移（中间大、两端小）
    x_base = np.linspace(x_noise, x_data, n_steps)
    envelope = np.sin(np.linspace(0, np.pi, n_steps)) * 0.12
    x_sde = x_base + np.cumsum(np.random.randn(n_steps) * 0.02) * envelope * 3
    x_sde[0], x_sde[-1] = x_noise, x_data  # 确保端点精确
    ax.plot(x_sde, t_sde, 'b-', linewidth=1.5, alpha=0.7, label='扩散 SDE（多步随机）')
    # 标记几个中间步
    for i in range(0, n_steps, 8):
        ax.plot(x_sde[i], t_sde[i], 'b.', markersize=5, alpha=0.5)

    # 2. Rectified Flow：直线，少步（4步）
    n_rf = 5
    t_rf = np.linspace(t_noise, t_data, n_rf)
    x_rf = np.linspace(x_noise, x_data, n_rf)
    ax.plot(x_rf, t_rf, 'o-', color='orange', linewidth=2.5, markersize=7,
            label='Rectified Flow（直线，4 步）')

    # 3. 一致性模型：单步跳跃（弧线箭头，区别于直线）
    from matplotlib.patches import FancyArrowPatch
    import matplotlib.path as mpath
    # 用弧线表示"一步直达"
    mid_x = (x_noise + x_data) / 2 + 0.25  # 弧线向右偏
    mid_t = (t_noise + t_data) / 2
    verts = [(x_noise, t_noise), (mid_x, mid_t), (x_data, t_data)]
    codes = [mpath.Path.MOVETO, mpath.Path.CURVE3, mpath.Path.CURVE3]
    path = mpath.Path(verts, codes)
    patch = FancyArrowPatch(path=path, arrowstyle='->', color='green',
                            lw=2.5, linestyle='--', mutation_scale=20)
    ax.add_patch(patch)
    ax.text(mid_x + 0.02, mid_t, '一致性模型\n（1 步直达）', ha='left', va='center',
            fontsize=9, color='green', fontproperties=CJK_FONT_NAME)

    # 起终点
    ax.plot(x_noise, t_noise, 'ro', markersize=14, zorder=5)
    ax.plot(x_data, t_data, 'go', markersize=14, zorder=5)
    ax.text(x_noise - 0.05, t_noise + 0.05, '噪声 $x_T$', ha='right', va='bottom',
            fontsize=10, color='red', fontproperties=CJK_FONT_NAME)
    ax.text(x_data + 0.05, t_data - 0.05, '数据 $x_0$', ha='left', va='top',
            fontsize=10, color='green', fontproperties=CJK_FONT_NAME)

    ax.set_title('相同起终点，不同生成路径', fontsize=13, fontproperties=CJK_FONT_NAME, fontweight='bold')
    ax.set_xlabel('数据空间坐标 $x$', fontsize=11, fontproperties=CJK_FONT_NAME)
    ax.set_ylabel('生成过程（$t$: $T$→0，噪声→数据）', fontsize=11, fontproperties=CJK_FONT_NAME)
    ax.set_xlim(-0.1, 1.2); ax.set_ylim(-0.15, 1.15)
    ax.invert_yaxis()  # t=T(噪声)在上，t=0(数据)在下——匹配"从噪声走向数据"的阅读方向
    ax.grid(True, alpha=0.2)
    ax.legend(fontsize=9, prop=CJK_FONT_NAME, loc='lower left')
    save(fig, 'fig_ch9_flow_matching_vs_diffusion.png')


# ====== Ch9 §9.2: DiT 架构（合并自 make_dit_figs.py） ======

def fig_ch9_dit_vs_unet():
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # === 左：U-Net 结构 ===
    ax = axes[0]
    ax.set_xlim(-0.5, 10.5)
    ax.set_ylim(-1, 9)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('U-Net：勾线笔（卷积 + 跳跃连接）', fontsize=13, fontweight='bold', pad=10)

    # U-Net 形状（对称编码器-解码器）
    levels = [
        (1, 7, 2.5, 1.2, '#4ECDC4', 'Encoder\n64×64'),
        (3, 5.5, 2.0, 1.0, '#4ECDC4', '32×32'),
        (5, 4, 1.5, 0.8, '#4ECDC4', '16×16'),
        (7, 5.5, 2.0, 1.0, '#FF4444', '32×32'),
        (9, 7, 2.5, 1.2, '#FF4444', 'Decoder\n64×64'),
    ]
    for x, y, w, h, color, label in levels:
        rect = FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle="round,pad=0.1",
                               facecolor=color, edgecolor='#333', linewidth=1.5, alpha=0.8)
        ax.add_patch(rect)
        ax.text(x, y, label, ha='center', va='center', fontsize=8, fontweight='bold')

    # 跳跃连接
    for (y1, y2) in [(7, 7), (5.5, 5.5)]:
        ax.annotate('', xy=(9, y2), xytext=(1, y1),
                    arrowprops=dict(arrowstyle='->', color='#FF4444', lw=1.5,
                                   connectionstyle='arc3,rad=-0.3'))
    ax.text(5, 8.5, '跳跃连接（skip）', ha='center', fontsize=8, color='#FF4444', fontweight='bold')

    # 瓶颈
    ax.annotate('瓶颈', xy=(5, 4), xytext=(5, 2.5),
                arrowprops=dict(arrowstyle='->', color='#666', lw=1),
                fontsize=9, ha='center', color='#666')

    # 强归纳偏置标签
    ax.text(5, 0.5, '强归纳偏置：局部性 + 多尺度\n小数据赢，大数据变枷锁',
            ha='center', va='center', fontsize=8, style='italic',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFFACD', edgecolor='#DAA520', alpha=0.8))

    # === 右：DiT 结构 ===
    ax = axes[1]
    ax.set_xlim(-1.3, 10.5)
    ax.set_ylim(-1, 9)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('DiT：大板刷（Transformer 块堆叠）', fontsize=13, fontweight='bold', pad=10)

    # Patchify
    rect = FancyBboxPatch((0.5, 6.5), 2, 1, boxstyle="round,pad=0.1",
                           facecolor='#4ECDC4', edgecolor='#333', linewidth=1.5, alpha=0.8)
    ax.add_patch(rect)
    ax.text(1.5, 7, 'Patchify\n2×2 → token', ha='center', va='center', fontsize=8, fontweight='bold')

    # Transformer 块堆叠
    block_colors = ['#9370DB', '#9370DB', '#9370DB', '#9370DB', '#9370DB']
    block_labels = ['DiT 块\n(adaLN-zero)', 'DiT 块', 'DiT 块', 'DiT 块', 'DiT 块']
    for i, (color, label) in enumerate(zip(block_colors, block_labels)):
        y = 5.8 - i * 1.0
        rect = FancyBboxPatch((0.5, y), 2, 0.7, boxstyle="round,pad=0.08",
                               facecolor=color, edgecolor='#333', linewidth=1.2, alpha=0.8)
        ax.add_patch(rect)
        ax.text(1.5, y+0.35, label, ha='center', va='center', fontsize=7, fontweight='bold')
        if i < 4:
            ax.annotate('', xy=(1.5, y), xytext=(1.5, y+0.7),
                        arrowprops=dict(arrowstyle='->', color='#333', lw=1))

    # adaLN-zero 注入
    for i in range(5):
        y = 5.8 - i * 1.0 + 0.35
        ax.annotate('t,c', xy=(0.5, y), xytext=(-0.2, y),
                    arrowprops=dict(arrowstyle='->', color='#FF6600', lw=1.2),
                    fontsize=7, color='#FF6600', fontweight='bold', va='center')

    ax.text(-0.75, 4.3, '条件注入\n(adaLN)', ha='center', va='center', fontsize=7,
            color='#FF6600', fontweight='bold', rotation=90)

    # 输出
    ax.annotate('', xy=(1.5, 0.3), xytext=(1.5, 1.3),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.5))
    ax.text(1.5, 0, '输出：噪声预测 ε\n(逐 token)', ha='center', va='center', fontsize=8, fontweight='bold')

    # 右侧标注：扩展方式
    ax.annotate('', xy=(5.5, 6), xytext=(2.8, 6),
                arrowprops=dict(arrowstyle='->', color='#228B22', lw=2))
    ax.text(6, 6, '扩展方式：\n加层数 → 加宽度\n线性堆叠', ha='left', va='center', fontsize=8,
            color='#228B22', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#90EE90', edgecolor='#228B22', alpha=0.5))

    ax.annotate('', xy=(5.5, 3), xytext=(2.8, 3),
                arrowprops=dict(arrowstyle='->', color='#228B22', lw=2))
    ax.text(6, 3, '所有 patch\n互相看到\n(全局注意力)', ha='left', va='center', fontsize=8,
            color='#228B22', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#90EE90', edgecolor='#228B22', alpha=0.5))

    # 弱归纳偏置标签
    ax.text(5, -0.5, '弱归纳偏置：无局部性假设\n小数据吃亏，大数据大算力反而赢',
            ha='center', va='center', fontsize=8, style='italic',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFFACD', edgecolor='#DAA520', alpha=0.8))

    plt.tight_layout()
    save(fig, 'fig_ch9_dit_vs_unet.png')


def fig_ch9_dit_scaling_law():
    fig, ax = plt.subplots(figsize=(10, 6))

    # DiT 论文真实数据（Peebles & Xie 2023, arXiv:2212.09748, 附录规格表）
    # ImageNet 256x256, 400K 训练步, 无 CFG, patch size /2
    models = ['DiT-S/2', 'DiT-B/2', 'DiT-L/2', 'DiT-XL/2']
    gflops = np.array([6.06, 23.01, 80.71, 118.6])   # 前向计算量
    params = [33, 130, 458, 675]                       # 参数量(M)
    fid    = np.array([68.40, 43.47, 23.33, 19.47])    # FID-50K, 无 CFG

    # 幂律拟合线（真实数据 R²=0.99）
    lx = np.log10(gflops)
    slope, intercept = np.polyfit(lx, np.log10(fid), 1)
    gg = np.logspace(np.log10(5), np.log10(140), 50)
    fit = 10**intercept * gg**slope

    # 深浅蓝：拟合线浅、数据点深（全蓝系）
    ax.plot(gg, fit, '-', color='#9dc3e6', linewidth=2, alpha=0.9,
            label=f'幂律拟合：FID $\\propto$ Gflops$^{{{slope:.2f}}}$')
    ax.plot(gflops, fid, 'o', color='#1f4e79', markersize=11, zorder=5,
            label='DiT 各型号（真实数据）')

    # 每个数据点标注：型号 + 参数量 + FID（具体数字）
    offs = [(1.18, 1.12), (1.15, 1.12), (0.30, 0.72), (0.62, 1.62)]
    for mo, g, p, f, (ox, oy) in zip(models, gflops, params, fid, offs):
        ax.text(g * ox, f * oy, f'{mo}\n{p}M · FID {f}',
                fontsize=8.5, color='#1f4e79', fontproperties=CJK_FONT_NAME,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#555555',
                          edgecolor='#9dc3e6', alpha=0.9))

    # DiT-XL/2 带 CFG 的最优点（摘要确证 FID 2.27）——单独一点，说明上限
    ax.plot([118.6], [2.27], '*', color='#2e75b6', markersize=20, zorder=6)
    ax.annotate('DiT-XL/2 + CFG\nFID 2.27（论文最优）', xy=(118.6, 2.27),
                xytext=(20, 3.2), fontsize=8.5, color='#2e75b6', fontproperties=CJK_FONT_NAME,
                arrowprops=dict(arrowstyle='->', color='#2e75b6', lw=1.3),
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#555555',
                          edgecolor='#2e75b6', alpha=0.9))

    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_xlabel('前向计算量 Gflops（对数轴）', fontproperties=CJK_FONT_NAME, fontsize=12)
    ax.set_ylabel('FID（对数轴，越低越好）', fontproperties=CJK_FONT_NAME, fontsize=12)
    ax.set_title('DiT 的 Scaling Law：计算量越大，FID 沿幂律稳步下降',
                 fontproperties=CJK_FONT_NAME, fontsize=13)
    ax.legend(loc='upper right', fontsize=10, prop=CJK_FONT_NAME)
    ax.grid(True, which='both', ls='--', alpha=0.3)
    ax.set_xlim(4.5, 160)
    ax.set_ylim(1.8, 90)

    plt.tight_layout()
    save(fig, 'fig_ch9_dit_scaling_law.png')


def fig_ch9_dit_video_spatime():
    """DiT 在视频生成中的优势：时空注意力 vs 3D U-Net 卷积"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # === 左：3D U-Net 卷积在时间维度上笨重 ===
    ax = axes[0]
    ax.set_xlim(-0.5, 10)
    ax.set_ylim(-1, 7)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('3D U-Net：卷积在时间维度上笨重', fontsize=12, fontweight='bold', pad=10)

    # 画几帧
    for t in range(4):
        x = 1 + t * 2.2
        rect = FancyBboxPatch((x-0.8, 3), 1.6, 2, boxstyle="round,pad=0.1",
                               facecolor='#4ECDC4', edgecolor='#333', linewidth=1, alpha=0.6)
        ax.add_patch(rect)
        ax.text(x, 4, f't={t}', ha='center', va='center', fontsize=9, fontweight='bold')

    # 卷积核（只覆盖局部时间窗口）
    for t in range(3):
        x = 2.1 + t * 2.2
        rect = FancyBboxPatch((x-0.6, 2.5), 1.2, 3, boxstyle="round,pad=0.05",
                               facecolor='none', edgecolor='#FF4444', linewidth=2, linestyle='--')
        ax.add_patch(rect)

    ax.text(5, 1.5, '3D 卷积核只能看到\n局部时间窗口（如 3 帧）\n长程时序依赖需要堆很多层',
            ha='center', va='center', fontsize=8, color='#FF4444',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#FF4444', edgecolor='#FF4444', alpha=0.5))

    ax.text(5, 0, '要看到 t=0 和 t=15 的关系？\n得堆 8+ 层卷积',
            ha='center', va='center', fontsize=8, color='#666', style='italic')

    # === 右：DiT 自注意力全局覆盖 ===
    ax = axes[1]
    ax.set_xlim(-0.5, 10)
    ax.set_ylim(-1, 7)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('DiT：自注意力一次覆盖全部时空', fontsize=12, fontweight='bold', pad=10)

    # 画几帧
    for t in range(4):
        x = 1 + t * 2.2
        rect = FancyBboxPatch((x-0.8, 3), 1.6, 2, boxstyle="round,pad=0.1",
                               facecolor='#9370DB', edgecolor='#333', linewidth=1, alpha=0.6)
        ax.add_patch(rect)
        ax.text(x, 4, f't={t}', ha='center', va='center', fontsize=9, fontweight='bold')

    # 全局注意力连线
    positions = [(1, 4), (3.2, 4), (5.4, 4), (7.6, 4)]
    for i in range(4):
        for j in range(i+1, 4):
            ax.plot([positions[i][0], positions[j][0]], [positions[i][1], positions[j][1]],
                    '-', color='#1565C0', linewidth=1, alpha=0.4)

    ax.text(4.3, 6.2, '所有 patch 互相看到\n第一层就能建立长程依赖',
            ha='center', va='center', fontsize=8, color='#1565C0', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#9DC3E6', edgecolor='#1565C0', alpha=0.4))

    ax.text(4.3, 0, 'Sora / MovieGen / Step-Video\n全部选 DiT 不是巧合',
            ha='center', va='center', fontsize=8, color='#666', style='italic',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFFACD', edgecolor='#DAA520', alpha=0.6))

    plt.tight_layout()
    save(fig, 'fig_ch9_dit_video_spatime.png')


# =============================================================================
# 新增图（P0）：§2.0 数据流形假设
# =============================================================================
def fig_ch2_data_manifold():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))

    # ---- 左：高维空间里数据只占低维流形 ----
    ax = axes[0]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.set_aspect('equal'); ax.axis('off')
    ax.add_patch(FancyBboxPatch((0.3, 0.3), 9.4, 9.4, boxstyle="round,pad=0.1",
                                facecolor='#555555', edgecolor='#999', linewidth=1.2))
    ax.text(0.6, 9.2, '高维像素空间（~300 万维）', ha='left', fontsize=11, fontweight='bold', color='#333')
    # 低维流形：一条弯曲的带
    t = np.linspace(0, 2*np.pi, 200)
    mx = 5 + 2.6*np.cos(t) + 0.5*np.cos(2*t)
    my = 5 + 2.2*np.sin(t)
    ax.plot(mx, my, color='#1F4E79', linewidth=3, zorder=3)
    ax.fill(mx, my, color='#4A90D9', alpha=0.18, zorder=2)
    # 真实数据点（在流形上）
    idx = np.linspace(0, 199, 7).astype(int)
    ax.scatter(mx[idx], my[idx], c='#1F4E79', s=70, zorder=5, label='真实图片（在流形上）')
    # 随机点（几乎全是垃圾，落在流形外）
    rng = np.random.default_rng(1)
    rx = rng.uniform(1, 9, 12); ry = rng.uniform(1, 9, 12)
    ax.scatter(rx, ry, c='#C44E52', s=45, marker='x', zorder=4, label='随机像素（几乎全是噪声）')
    ax.text(5, 1.0, '真实数据只浸在低维"面"上\n其余广袤空间几乎全是垃圾图',
            ha='center', fontsize=10, style='italic', color='#555',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFFACD', alpha=0.7))
    ax.legend(loc='upper right', fontsize=8, prop=CJK_FONT_NAME, framealpha=0.85)
    ax.set_title('数据流形假设：真实数据 ≪ 全空间', fontsize=12)

    # ---- 右：分数只需在流形附近有效 ----
    ax = axes[1]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.set_aspect('equal'); ax.axis('off')
    ax.plot(mx, my, color='#1F4E79', linewidth=3, zorder=3)
    ax.fill(mx, my, color='#4A90D9', alpha=0.18, zorder=2)
    # 流形外的噪声点 + 指回流形的分数箭头
    noise_pts = [(2.2, 8.2), (8.4, 7.6), (8.6, 2.4), (2.0, 2.6)]
    for nx, ny in noise_pts:
        d2 = (mx - nx)**2 + (my - ny)**2
        j = np.argmin(d2)
        ax.scatter([nx], [ny], c='#C44E52', s=55, zorder=5)
        ax.annotate('', xy=(mx[j], my[j]), xytext=(nx, ny),
                    arrowprops=dict(arrowstyle='->', color='#4C72B0', lw=2))
    ax.scatter([], [], c='#C44E52', s=55, label='噪声点（流形外）')
    ax.plot([], [], color='#4C72B0', lw=2, label='分数方向（指回流形）')
    ax.text(5, 1.0, '分数只需在流形附近有效\n远离流形的地方，指哪都无所谓',
            ha='center', fontsize=10, style='italic', color='#555',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#555555', alpha=0.8))
    ax.legend(loc='upper left', fontsize=9, prop=CJK_FONT_NAME)
    ax.set_title('去噪 = 指回流形 = 分数方向', fontsize=12)

    plt.tight_layout()
    save(fig, 'fig_ch2_data_manifold.png')


# =============================================================================
# 新增图（P0）：§5.2 DDIM——换坐标让 ODE 变直线
# =============================================================================
def fig_ch5_ddim_straight_line():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))

    # VP 调度轨迹（从数据到噪声的一条确定性 ODE 路径）
    ab = np.linspace(0.999, 0.02, 60)          # ᾱ 从接近1到接近0
    a = np.sqrt(ab)                             # 信号系数
    b = np.sqrt(1 - ab)                         # 噪声系数
    eps = 0.9                                   # 固定 ε_θ 方向（示意）
    x0 = 1.6
    x = a * x0 + b * eps                        # 原始 x 空间轨迹

    # ---- 左：原始 x 空间——轨迹是弯的 ----
    ax = axes[0]
    ax.plot(b, x, color='#C44E52', linewidth=2.6, zorder=3)
    ax.scatter([b[0]], [x[0]], c='#1F4E79', s=90, zorder=5, label='数据端 ($t\\to 0$)')
    ax.scatter([b[-1]], [x[-1]], c='#4C72B0', s=90, zorder=5, label='噪声端 ($t\\to T$)')
    for k in np.linspace(0, 59, 7).astype(int):
        ax.scatter([b[k]], [x[k]], c='#C44E52', s=22, zorder=4)
    ax.set_xlabel('噪声水平 $\\sqrt{1-\\bar{\\alpha}_t}$', fontsize=11)
    ax.set_ylabel('状态 $x_t$', fontsize=11)
    ax.set_title('原始 $x$ 空间：ODE 轨迹是弯的\n（信号在收缩，看不出形状）', fontsize=11)
    ax.grid(True, alpha=0.25); ax.legend(fontsize=9, prop=CJK_FONT_NAME)

    # ---- 右：归一化坐标——轨迹变直线 ----
    ax = axes[1]
    xt = x / a          # 归一化状态 x̃ = x/√ᾱ
    st = b / a          # 归一化噪声比 σ̃ = √(1-ᾱ)/√ᾱ
    ax.plot(st, xt, color='#1F4E79', linewidth=2.6, zorder=3)
    ax.scatter([st[0]], [xt[0]], c='#1F4E79', s=90, zorder=5)
    ax.scatter([st[-1]], [xt[-1]], c='#4C72B0', s=90, zorder=5)
    for k in np.linspace(0, 59, 7).astype(int):
        ax.scatter([st[k]], [xt[k]], c='#1F4E79', s=22, zorder=4)
    # 斜率标注
    ax.annotate('斜率 = $\\varepsilon_\\theta$\n（真的是一条直线）',
                xy=(st[30], xt[30]), xytext=(st[30]*0.35, xt[30]+0.4),
                fontsize=10, color='#1F4E79',
                arrowprops=dict(arrowstyle='->', color='#666', lw=1))
    ax.set_xlabel('归一化噪声比 $\\tilde{\\sigma}_t = \\sqrt{1/\\bar{\\alpha}_t - 1}$', fontsize=11)
    ax.set_ylabel('归一化状态 $\\tilde{x}_t = x_t/\\sqrt{\\bar{\\alpha}_t}$', fontsize=11)
    ax.set_title('归一化坐标：ODE 变成直线\n$d\\tilde{x}/d\\tilde{\\sigma} = \\varepsilon_\\theta$（DDIM 一步就是走直线）', fontsize=11)
    ax.grid(True, alpha=0.25)

    plt.tight_layout()
    save(fig, 'fig_ch5_ddim_straight_line.png')


# =============================================================================
# 新增图（P1）：§6.3 CFG——噪声空间里的外推
# =============================================================================
def fig_ch6_cfg_extrapolation():
    fig, ax = plt.subplots(figsize=(9, 6.5))

    eps_unc = np.array([0.3, 0.2])
    eps_cond = np.array([0.5, 0.1])
    delta = eps_cond - eps_unc

    ws = [0, 1, 3, 7.5, 10]
    colors = ['#555555', '#4C72B0', '#E8833A', '#C44E52', '#C62828']
    pts = [eps_unc + w * delta for w in ws]

    # 方向线（从 unc 沿 Δ 延伸）
    line_t = np.linspace(-0.3, 11, 50)
    line = np.array([eps_unc + t * delta for t in line_t])
    ax.plot(line[:, 0], line[:, 1], '--', color='#BBB', linewidth=1.2, zorder=1)

    # 内插区 vs 外推区底色
    ax.annotate('', xy=tuple(eps_cond), xytext=tuple(eps_unc),
                arrowprops=dict(arrowstyle='->', color='#4C72B0', lw=2.5), zorder=2)

    for w, c, p in zip(ws, colors, pts):
        ax.scatter([p[0]], [p[1]], c=c, s=110, zorder=5, edgecolors='white', linewidths=1.2)
        label = {0: '$w=0$（纯无条件）', 1: '$w=1$（=条件模型）', 3: '$w=3$（SD 常用）',
                 7.5: '$w=7.5$（SD 默认）', 10: '$w=10$（接近坍塌）'}[w]
        # w=0/1 标签放左上避开"条件方向"文字；其余放右上
        if w in (0, 1):
            ax.annotate(label, xy=(p[0], p[1]), xytext=(p[0]-0.04, p[1]+0.16),
                        fontsize=9, color=c, fontweight='bold', ha='right')
        else:
            dy = 0.06 if w != 7.5 else -0.09
            ax.annotate(label, xy=(p[0], p[1]), xytext=(p[0]+0.05, p[1]+dy),
                        fontsize=9, color=c, fontweight='bold', ha='left')

    # 标注两个基准点
    ax.annotate('$\\varepsilon_{unc}$\n(自由发挥)', xy=tuple(eps_unc), xytext=(eps_unc[0]-0.14, eps_unc[1]-0.14),
                fontsize=10, color='#333', ha='center')
    ax.annotate('$\\varepsilon_{cond}$\n(听甲方)', xy=tuple(eps_cond), xytext=(eps_cond[0]+0.16, eps_cond[1]-0.16),
                fontsize=10, color='#333', ha='center')
    ax.text(0.52, 0.30, '条件方向 $\\Delta = \\varepsilon_{cond}-\\varepsilon_{unc}$', fontsize=10,
            color='#4C72B0', rotation=-27)

    # 内插/外推分区说明（左对齐，压在底部空白区）
    ax.text(-0.05, -0.62, '$w\\leq 1$：内插（两点连线之间）', fontsize=9.5, color='#666')
    ax.text(-0.05, -0.80, '$w>1$：外推（冲出连线之外）——CFG 的关键', fontsize=9.5, color='#C44E52', fontweight='bold')
    ax.text(-0.05, -0.98, '$w$ 过大 → 拉出典型分布区 → 模式坍塌', fontsize=9.5, color='#C62828')

    ax.set_xlabel('噪声预测第 1 维', fontsize=11)
    ax.set_ylabel('噪声预测第 2 维', fontsize=11)
    ax.set_title('CFG 是噪声空间里的外推：$\\hat{\\varepsilon}=\\varepsilon_{unc}+w(\\varepsilon_{cond}-\\varepsilon_{unc})$\n沿"条件方向"这条线冲出去，$w$ 控制冲多远', fontsize=12)
    ax.grid(True, alpha=0.2)
    ax.set_xlim(-0.2, 3.5); ax.set_ylim(-1.15, 0.6)

    plt.tight_layout()
    save(fig, 'fig_ch6_cfg_extrapolation.png')


# =============================================================================
# 新增图（P2）：§1.5 高斯噪声的唯一性——可处理 vs 崩溃
# =============================================================================
def fig_ch1_gaussian_uniqueness():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=False)
    xx = np.linspace(-4, 4, 400)

    def gauss(x, mu, s):
        return np.exp(-((x-mu)**2)/(2*s*s)) / (s*np.sqrt(2*np.pi))

    # ---- 左：高斯噪声——加噪后仍是高斯，闭式可跳步 ----
    ax = axes[0]
    for mu, s, c, lab in [(0, 0.5, '#1F4E79', '$x_0$（干净）'),
                          (0, 0.9, '#4A90D9', '$t$ 中期'),
                          (0, 1.5, '#4A90D9', '$t$ 后期')]:
        ax.plot(xx, gauss(xx, mu, s), color=c, linewidth=2.2, label=lab)
        ax.fill_between(xx, gauss(xx, mu, s), color=c, alpha=0.12)
    ax.text(0, 0.02, '每个 $t$ 的 $p(x_t\\mid x_0)$\n都是高斯，均值方差已知\n→ 闭式跳步 / Tweedie / 反向 SDE',
            ha='center', fontsize=10, color='#1F4E79',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#555555', edgecolor='#1F4E79', alpha=0.9))
    ax.set_title('加高斯噪声：条件分布永远是高斯\n（整个框架"算得下去"的地基）', fontsize=11)
    ax.set_xlabel('$x_t$', fontsize=11); ax.set_yticks([])
    ax.legend(fontsize=9, prop=CJK_FONT_NAME, loc='upper right')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    # ---- 右：换成非高斯——条件分布失去解析形式 ----
    ax = axes[1]
    # 均匀 + 拉普拉斯 卷积后畸形分布（示意：非光滑/非高斯）
    lap = np.exp(-np.abs(xx)/0.7)/(2*0.7)
    uni = np.where(np.abs(xx) <= 1.2, 1/2.4, 0)
    # 数值卷积示意
    conv = np.convolve(lap, uni, mode='same')
    conv /= conv.sum() * (xx[1] - xx[0])   # 归一化为概率密度（避免 np.trapz/trapezoid 版本差异）
    ax.plot(xx, lap, color='#E8833A', linewidth=2, label='拉普拉斯噪声')
    ax.plot(xx, uni, color='#9370DB', linewidth=2, label='均匀噪声')
    ax.plot(xx, conv, color='#C44E52', linewidth=2.6, label='多步叠加后（畸形）')
    ax.fill_between(xx, conv, color='#C44E52', alpha=0.12)
    ax.text(0, 0.02, '换非高斯噪声：\n$p(x_t\\mid x_0)$ 无解析式\n→ 跳步 / Tweedie / 反向 SDE 同时崩溃',
            ha='center', fontsize=10, color='#C44E52',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#555555', edgecolor='#C44E52', alpha=0.9))
    ax.set_title('换成别的噪声：解析性崩溃\n（不是不美观，是根本算不动）', fontsize=11)
    ax.set_xlabel('$x_t$', fontsize=11); ax.set_yticks([])
    ax.legend(fontsize=9, prop=CJK_FONT_NAME, loc='upper right')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    plt.tight_layout()
    save(fig, 'fig_ch1_gaussian_uniqueness.png')


# =============================================================================
# 新增图（P2）：§6.2 CLIP + 交叉注意力——文字如何进入生成
# =============================================================================
def fig_ch6_clip_conditioning():
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_xlim(0, 12); ax.set_ylim(0, 6); ax.axis('off')

    def box(x, y, w, h, text, fc, ec):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                                    facecolor=fc, edgecolor=ec, linewidth=1.6))
        ax.text(x+w/2, y+h/2, text, ha='center', va='center', fontsize=10, color='#222')

    def arrow(x1, y1, x2, y2, txt='', c='#555'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=c, lw=2))
        if txt:
            ax.text((x1+x2)/2, (y1+y2)/2+0.22, txt, ha='center', fontsize=9, color=c)

    # 文字 → CLIP → 向量 c
    box(0.3, 4.2, 1.9, 1.0, '"一只猫"\n(文字条件)', '#E8833A', '#DAA520')
    box(2.9, 4.2, 1.9, 1.0, 'CLIP\n文本编码器', '#9DC3E6', '#5B9BD5')
    box(5.5, 4.2, 1.7, 1.0, '语义向量 $c$', '#555555', '#55A868')
    arrow(2.2, 4.7, 2.9, 4.7)
    arrow(4.8, 4.7, 5.5, 4.7)

    # 图片特征 Q，向量 c 作 K,V，交叉注意力
    box(0.3, 1.0, 1.9, 1.0, '图片特征\n(查询 $Q$)', '#FF4444', '#C62828')
    box(5.3, 1.0, 2.1, 1.0, '交叉注意力\n$Q$ 看一眼 $K,V$', '#555555', '#9370DB')
    box(8.6, 1.0, 2.2, 1.0, '条件化的\n图片特征', '#555555', '#55A868')
    arrow(2.2, 1.5, 5.3, 1.5, '$Q$')
    arrow(7.4, 1.5, 8.6, 1.5)
    # c 作为 K,V 下注入交叉注意力
    arrow(6.35, 4.2, 6.35, 2.0, '作键 $K$、值 $V$', '#5B9BD5')

    ax.text(6, 5.6, '文生图的条件通路：文字 → CLIP → 向量 $c$ → 交叉注意力 → 条件生成',
            ha='center', fontsize=12, fontweight='bold', color='#333')
    ax.text(6, 0.3, '每一层都让图片特征"看一眼"文本：文本说画猫，这里就该是猫的轮廓',
            ha='center', fontsize=9.5, style='italic', color='#666')

    save(fig, 'fig_ch6_clip_conditioning.png')


def main():
    print("=" * 60)
    print("扩散：从噪声生成 - 生成全部 41 张插图")
    print("=" * 60)

    # Ch1: 前向过程
    fig_ch1_forward_process()
    fig_ch1_2d_forward_noising()
    fig_ch1_gaussian_uniqueness()       # 新增 §1.5 高斯噪声唯一性
    fig_ch1_ve_vp_comparison()
    fig_ch1_discrete_continuous_bridge()

    # Ch2: 反向过程
    fig_ch2_data_manifold()             # 新增 §2.0 数据流形假设
    fig_ch3_reverse_process()
    fig_ch3_forward_reverse_combined()

    # Ch3: 分数函数
    fig_ch2_score_function()
    fig_ch2_multiscale_score_field()
    fig_ch2_tweedie_geometry()
    fig_ch2_epsilon_score_equivalence()

    # Ch4: 训练目标
    fig_ch4_training_objective()
    fig_ch4_unified_training()
    fig_ch4_training_loss_by_t()

    # Ch5: 采样策略
    fig_ch5_sampling_strategies()
    fig_ch3_ddpm_ncsn_comparison()
    fig_ch3_reverse_sde_drift_decomposition()
    fig_ch5_three_error_sources()
    fig_ch5_sde_ode_density_match()
    fig_ch3_sde_ode_samplers_multimodal()
    fig_ch5_ddim_straight_line()        # 新增 §5.2 DDIM 换坐标变直线

    # Ch6: 条件控制
    fig_ch6_conditional_control()
    fig_ch1_schedules_models_inpainting()
    fig_ch6_clip_conditioning()         # 新增 §6.2 CLIP + 交叉注意力
    fig_ch6_cfg_extrapolation()         # 新增 §6.3 CFG 外推
    fig_ch6_controlnet_cfg_consistency()
    fig_ch9_latent_crossattention_training()

    # Ch7: 前沿
    fig_ch9_frontier()
    fig_ch4_time_embedding()
    fig_ch7_masked_diffusion_process()
    fig_ch7_continuous_discrete_parallel()

    # Ch8: 视频与世界模型
    fig_ch8_video_worldmodel()
    fig_ch8_frame_consistency()
    fig_ch8_spacetime_attention()
    fig_ch8_diffusion_policy_multimodal()

    # 扩展
    fig_ch9_inference_rl()
    fig_ch9_flow_matching_vs_diffusion()

    # Ch9 §9.2: DiT 架构
    fig_ch9_dit_vs_unet()
    fig_ch9_dit_scaling_law()
    fig_ch9_dit_video_spatime()

    print("=" * 60)
    print("全部 41 张图生成完毕！")
    print("=" * 60)


if __name__ == '__main__':
    main()
