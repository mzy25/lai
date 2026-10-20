# -*- coding: utf-8 -*-
"""series 配图单一来源：一图一函数（P0 试点 3 张，P1 全量 22 张）。

用法：
    .venv/bin/python series/tools/generate_figures.py            # 全部（当前=P0 三张 + 已注册）
    .venv/bin/python series/tools/generate_figures.py 0-2 T4-2   # 单张重建

产出：
    series/figures/<file>.png      图件
    series/figures/manifest.json   图号 → {file, func}（build_site 渲染与门禁读它）

规范：图内文字中文；标题短句；解释归正文图注；颜色一律取 fig_common 语义色板。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon
from matplotlib.path import Path as MplPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fig_common import (  # noqa: E402
    FIGDIR, INK, BLUE, RED, GREEN, ORANGE, PURPLE, GRAY,
    ROLE_PRIMARY, ROLE_DANGER, ROLE_SUCCESS, ROLE_WARNING, ROLE_PURPLE,
    setup_rc, save_fig,
)

FIGURES: dict[str, tuple[str, object]] = {}


def figure(fid: str, file: str):
    """注册一张图：图号（与正文〔图 X：…〕一致）→ 文件名 + 函数。"""
    def deco(fn):
        FIGURES[fid] = (file, fn)
        return fn
    return deco


# ---------------------------------------------------------------- 画布小工具

def _box(ax, x, y, w, h, text, fc, ec, fs=9, weight=None, radius=0.06):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle=f"round,pad=0.02,rounding_size={radius}",
                 fc=fc, ec=ec, lw=1.4))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=INK, fontweight=weight, linespacing=1.4)


def _arr(ax, p1, p2, color=None, lw=1.4, style="-|>", rad=0.0, ms=11, ls=None):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=ms,
                 lw=lw, color=color or GRAY["d"], linestyle=ls,
                 connectionstyle=f"arc3,rad={rad}",
                 shrinkA=1, shrinkB=1))


# ---------------------------------------------------------------- 图 0-2 四级火箭

@figure("0-2", "fig_0_2_rocket.png")
def fig_0_2_rocket():
    fig, ax = plt.subplots(figsize=(9.4, 4.9))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    cx, w = 3.0, 1.9

    stages = [
        ("一级｜表示", "切成 token、变成向量（§1）", GRAY["l"], GRAY["d"], 0.7, 2.5),
        ("二级｜预训练", "吃数据，练通用能力（§6）", BLUE["l"], BLUE["d"], 2.5, 4.3),
        ("三级｜后训练", "练指令遵循（§7）", BLUE["xl"], BLUE["d"], 4.3, 6.1),
    ]
    for name, desc, fc, ec, y0, y1 in stages:
        _box(ax, cx - w / 2, y0, w, y1 - y0, name, fc, ec, fs=10)
        ax.text(cx + w / 2 + 0.35, (y0 + y1) / 2, desc, ha="left", va="center",
                fontsize=8.5, color=INK)
    # 顶段：推理与生成（本级 + 整流罩）
    _box(ax, cx - w / 2, 6.1, w, 1.2, "四级｜推理与生成", GREEN["l"], GREEN["d"], fs=10)
    ax.add_patch(Polygon([(cx - w / 2, 7.3), (cx + w / 2, 7.3), (cx, 8.9)],
                 closed=True, fc=GREEN["l"], ec=GREEN["d"], lw=1.4))
    ax.text(cx + w / 2 + 0.35, 6.7, "写上下文、出内容（§9）", ha="left", va="center",
            fontsize=8.5, color=INK)

    # 读法箭头（自下而上）
    _arr(ax, (1.25, 1.0), (1.25, 8.3), color=GRAY["d"], lw=1.6)
    ax.text(0.85, 4.6, "读法自下而上", rotation=90, ha="center", va="center",
            fontsize=8.5, color=GRAY["d"])

    # 训练括号（只占中间两级）
    bx = 8.65
    ax.plot([bx, bx], [2.5, 6.1], color=ROLE_WARNING, lw=1.6)
    for yy in (2.5, 6.1):
        ax.plot([bx - 0.12, bx + 0.12], [yy, yy], color=ROLE_WARNING, lw=1.6)
    ax.text(bx + 0.22, 4.3, "训练：只占中间两级", rotation=90, ha="center", va="center",
            fontsize=8.5, color=ROLE_WARNING)

    ax.text(cx, 0.35, "原料装舱", ha="center", va="center", fontsize=8, color=GRAY["d"])
    ax.text(cx, 9.25, "载荷入轨", ha="center", va="center", fontsize=8, color=GREEN["d"])
    return save_fig(fig, "fig_0_2_rocket.png")


# ---------------------------------------------------------------- 图 T1-2 前向加噪

def _cat_image(n: int = 96) -> np.ndarray:
    """程序化“一张图”：简笔猫（单位方差归一，兑现 T1 的演示前提）。"""
    y, x = np.mgrid[0:1:n * 1j, 0:1:n * 1j]
    pts = np.column_stack([x.ravel(), y.ravel()])

    def circ(cx, cy, r):
        return ((x - cx) ** 2 + (y - cy) ** 2 <= r * r)

    def tri(p1, p2, p3):
        return MplPath([p1, p2, p3]).contains_points(pts).reshape(n, n)

    head = circ(0.5, 0.46, 0.27)
    earL = tri((0.30, 0.60), (0.45, 0.62), (0.32, 0.88))
    earR = tri((0.55, 0.62), (0.70, 0.60), (0.68, 0.88))
    eyes = circ(0.42, 0.48, 0.045) | circ(0.58, 0.48, 0.045)
    body = head | earL | earR
    img = np.where(body, 1.0, -0.6)
    img = np.where(eyes, -0.6, img)
    img = (img - img.mean()) / img.std()  # 单位方差：T1 演示前提
    return img


@figure("T1-2", "fig_t1_2_noising.png")
def fig_t1_2_noising():
    img = _cat_image()
    a = lambda t: np.exp(-t / 2.0)
    s = lambda t: np.sqrt(1.0 - np.exp(-t))
    ts = [0, 1, 2, 4, 1000]
    rng = np.random.default_rng(7)

    fig = plt.figure(figsize=(11.4, 5.4))
    gs = fig.add_gridspec(2, 5, height_ratios=[1.0, 0.92], hspace=0.42, wspace=0.06)
    for i, t in enumerate(ts):
        eps = rng.normal(size=img.shape)
        xt = a(t) * img + s(t) * eps
        ax = fig.add_subplot(gs[0, i])
        ax.imshow(xt, cmap="gray", vmin=-2.6, vmax=2.6, origin="lower")
        ax.set_title(f"t = {t}", fontsize=9, color=INK)
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_color(GRAY["line"])

    ax2 = fig.add_subplot(gs[1, :])
    tt = np.linspace(0, 7, 400)
    ax2.plot(tt, a(tt), color=ROLE_PRIMARY, lw=2.0, label="信号 a_t（原图还剩多少）")
    ax2.plot(tt, s(tt), color=ROLE_WARNING, lw=2.0, label="噪声 σ_t（噪声涨到多少）")
    for t, txt, off in [(1, "t=1：0.61／0.79", (10, 30)), (5, "t=5：0.08／0.996", (-96, 20))]:
        ax2.plot([t], [a(t)], "o", color=ROLE_PRIMARY, ms=5)
        ax2.plot([t], [s(t)], "o", color=ROLE_WARNING, ms=5)
        ax2.annotate(txt, (t, a(t)), textcoords="offset points",
                     xytext=off, fontsize=8.5, color=INK)
    ax2.set_xlabel("加噪步数 t", fontsize=9)
    ax2.set_ylabel("幅度", fontsize=9)
    ax2.set_ylim(0, 1.18)
    ax2.grid(color=GRAY["line"], lw=0.6, alpha=0.7)
    ax2.legend(loc="center right", fontsize=8.5, frameon=False)
    ax2.text(0.02, 0.95, "演示调度：a_t = e^(−t/2)，σ_t = √(1−e^(−t))，a_t² + σ_t² = 1",
             transform=ax2.transAxes, fontsize=8.5, color=GRAY["d"], va="top")
    return save_fig(fig, "fig_t1_2_noising.png")


# ---------------------------------------------------------------- 图 T4-2 ControlNet vs CFG

@figure("T4-2", "fig_t4_2_controlnet_vs_cfg.png")
def fig_t4_2_controlnet_vs_cfg():
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.6, 4.9))
    for ax in (axL, axR):
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis("off")

    # 左：ControlNet —— 改输入结构
    axL.text(5, 9.5, "ControlNet：改的是输入结构", ha="center", va="center",
             fontsize=11, color=INK, fontweight="bold")
    _box(axL, 5.2, 1.8, 3.1, 6.0, "U-Net 主干\n（冻结，不重训）", BLUE["l"], BLUE["d"], fs=9.5)
    _box(axL, 0.9, 7.0, 2.9, 1.0, "条件图（草图／深度图）", GRAY["l"], GRAY["d"], fs=8)
    _box(axL, 0.9, 5.0, 2.9, 1.1, "零卷积\n（初始输出 = 0）", ORANGE["l"], ORANGE["d"], fs=8.5)
    _arr(axL, (2.35, 7.0), (2.35, 6.1))
    for yy in (2.9, 4.8, 6.7):
        _arr(axL, (3.85, 5.5), (5.2, yy), color=ROLE_WARNING, rad=0.12)
    axL.text(5, 0.7, "条件从输入侧接进来；主干只加不重训", ha="center", va="center",
             fontsize=8.5, color=GRAY["d"])

    # 右：CFG —— 改采样方向
    axR.text(5, 9.5, "CFG：改的是采样方向", ha="center", va="center",
             fontsize=11, color=INK, fontweight="bold")
    _box(axR, 3.9, 3.9, 2.9, 2.6, "同一张 U-Net\n（跑两次）", BLUE["l"], BLUE["d"], fs=9.5)
    _box(axR, 0.5, 6.9, 2.6, 0.9, "带条件 c", GREEN["l"], GREEN["d"], fs=8.5)
    _box(axR, 0.5, 4.6, 2.6, 0.9, "空条件 ∅", GRAY["l"], GRAY["d"], fs=8.5)
    _arr(axR, (3.1, 7.35), (3.9, 6.0))
    _arr(axR, (3.1, 5.05), (3.9, 4.8))
    _box(axR, 7.2, 6.6, 2.3, 0.9, "ε_cond", BLUE["l"], BLUE["d"], fs=8.5)
    _box(axR, 7.2, 4.6, 2.3, 0.9, "ε_unc", GRAY["l"], GRAY["d"], fs=8.5)
    _arr(axR, (6.8, 5.8), (7.2, 6.9))
    _arr(axR, (6.8, 4.6), (7.2, 5.0))
    _box(axR, 6.9, 2.1, 2.9, 1.1, "差向量 × w\n（放大条件方向）", PURPLE["l"], PURPLE["d"], fs=8.5)
    _arr(axR, (8.35, 6.6), (8.35, 3.2), color=ROLE_PURPLE)
    _arr(axR, (9.5, 4.6), (9.6, 3.2), color=ROLE_PURPLE, rad=-0.35)
    _arr(axR, (6.9, 2.65), (5.6, 2.2), color=ROLE_PURPLE, rad=0.15)
    axR.text(4.4, 1.9, "融进采样方向", ha="center", va="center", fontsize=8.5, color=ROLE_PURPLE)
    axR.text(5, 0.7, "同一网络两用；条件融进方向里", ha="center", va="center",
             fontsize=8.5, color=GRAY["d"])

    fig.subplots_adjust(wspace=0.08)
    return save_fig(fig, "fig_t4_2_controlnet_vs_cfg.png")



# ---------------------------------------------------------------- 批次 A：结构/流程（7 张）

@figure("0-1", "fig_0_1_loop.png")
def fig_0_1_loop():
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.0, 4.4),
                                   gridspec_kw={"width_ratios": [1.1, 1.0]})
    # 左：训练回路（预测→比对→调整→再预测）
    axL.set_xlim(0, 10); axL.set_ylim(0, 10); axL.axis("off")
    axL.text(5, 9.5, "训练回路", ha="center", fontsize=11, fontweight="bold", color=INK)
    _box(axL, 3.4, 6.6, 2.6, 1.3, "预测", BLUE["l"], BLUE["d"], fs=10)
    _box(axL, 6.4, 4.0, 3.0, 1.3, "比对（损失）", GREEN["l"], GREEN["d"], fs=10)
    _box(axL, 3.4, 1.4, 2.6, 1.3, "调整（旋钮）", ORANGE["l"], ORANGE["d"], fs=10)
    _arr(axL, (6.0, 7.1), (6.6, 5.3), color=GRAY["d"], rad=-0.15)
    _arr(axL, (7.6, 4.0), (6.0, 2.4), color=GRAY["d"], rad=-0.15)
    _arr(axL, (4.4, 2.7), (3.9, 6.6), color=GRAY["d"], rad=-0.2)
    axL.text(7.7, 8.0, "再预测", fontsize=8.5, color=GRAY["d"])
    axL.text(1.9, 6.9, "一: 猜", fontsize=8.5, color=GRAY["d"])
    axL.text(8.6, 3.2, "二: 算错多大", fontsize=8.5, color=GRAY["d"])
    axL.text(0.3, 2.9, "三: 改一点", fontsize=8.5, color=GRAY["d"])
    # 右：单旋钮碗形曲线与下山轨迹
    axR.set_xlim(-3.2, 3.4); axR.set_ylim(-0.4, 9.6); axR.axis("off")
    axR.text(0, 9.5, "单旋钮：碗形曲线与下山", ha="center", fontsize=11,
             fontweight="bold", color=INK)
    w = np.linspace(-3.0, 3.0, 200)
    axR.plot(w, w * w, color=ROLE_PRIMARY, lw=2.0)
    ws = [2.6]; x = 2.6
    for _ in range(4):
        x = x - 0.3 * 2 * x  # 学习率 0.3 的梯度下降
        ws.append(x)
    for i, wx in enumerate(ws):
        axR.plot([wx], [wx * wx], "o", color=ROLE_WARNING, ms=5)
        if i < len(ws) - 1:
            axR.annotate("", xy=(ws[i + 1], ws[i + 1] ** 2),
                         xytext=(wx, wx * wx),
                         arrowprops=dict(arrowstyle="-|>", color=ROLE_WARNING,
                                         lw=1.2, connectionstyle="arc3,rad=0.25",
                                         shrinkA=2, shrinkB=2))
    axR.text(2.7, 8.2, "损失", fontsize=8.5, color=ROLE_PRIMARY, rotation=72)
    axR.text(-2.4, -0.1, "参数 w", fontsize=8.5, color=INK)
    axR.annotate("一路滚到碗底", (0.15, 0.5), xytext=(-2.9, 4.6), fontsize=8.5,
                 color=GRAY["d"], arrowprops=dict(arrowstyle="-|>", color=GRAY["d"], lw=1.0))
    fig.subplots_adjust(wspace=0.05)
    return save_fig(fig, "fig_0_1_loop.png")


@figure("15-1", "fig_15_1_pomdp.png")
def fig_15_1_pomdp():
    fig, ax = plt.subplots(figsize=(9.8, 5.2))
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
    ax.text(5, 9.6, "部分可观测：状态看不全，靠信念 $b_t$ 猜", ha="center",
            fontsize=11, fontweight="bold", color=INK)
    _box(ax, 0.5, 4.6, 2.4, 1.7, "环境·状态 s\n（看不全）", GRAY["l"], GRAY["d"], fs=9)
    _box(ax, 3.7, 4.6, 2.8, 1.7, "信念 $b_t$\n（可能性分配表）", BLUE["l"], BLUE["d"], fs=9.5)
    _arr(ax, (2.9, 5.8), (3.7, 5.5), color=ROLE_PRIMARY)
    ax.text(3.3, 6.7, "观测 $o_t$\n（观测模型 Z）", ha="center", fontsize=8, color=ROLE_PRIMARY)
    _arr(ax, (5.1, 4.6), (5.1, 2.6), color=ROLE_WARNING)
    ax.text(5.75, 3.6, "动作 $a_t$\n（动作空间 A）", ha="left", fontsize=8, color=ROLE_WARNING)
    _arr(ax, (5.1, 2.6), (1.7, 2.6), color=ROLE_WARNING, style="-")
    _arr(ax, (1.7, 2.6), (1.7, 4.6), color=ROLE_WARNING)
    ax.text(3.4, 2.15, "状态转移 T：世界怎么变", fontsize=8, color=ROLE_WARNING)
    chips = [
        "状态空间：世界可能处于的全部情形",
        "动作空间：能做的全部动作",
        "观测空间：能看到的信息",
        "状态转移：做完动作，世界怎么变",
        "观测模型：状态与观测的概率关系",
        "奖励：好不好的衡量（看一整条轨迹）",
        "折扣因子：越远的未来越打折",
    ]
    for i, txt in enumerate(chips):
        ax.text(7.0, 8.55 - i * 1.05, "· " + txt, fontsize=8, color=INK, va="center")
    ax.text(0.5, 1.0, "观察、推断、行动、反馈：一轮又是一轮", fontsize=9, color=GRAY["d"])
    return save_fig(fig, "fig_15_1_pomdp.png")


@figure("16-1", "fig_16_1_harness.png")
def fig_16_1_harness():
    fig, ax = plt.subplots(figsize=(10.2, 5.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
    ax.text(4.6, 9.6, "Harness 六层：模型的外围，每层一个工程动作", ha="center",
            fontsize=11, fontweight="bold", color=INK)
    layers = [
        ("L1 推理", "接任何 OpenAI 兼容端点"),
        ("L2 协议与工具", "注册一个带 schema 的工具"),
        ("L3 记忆与知识", "把会话事件日志写进上下文"),
        ("L4 编排", "决定何时重试、何时中断"),
        ("L5 评估与可观测", "让每一步可回放、可打分"),
        ("L6 护栏与安全", "给一个动作过一道安全的门"),
    ]
    for i, (name, act) in enumerate(layers):
        y = 0.9 + i * 1.32
        fc = BLUE["xl"] if i % 2 == 0 else BLUE["l"]
        _box(ax, 0.7, y, 3.4, 1.05, name, fc, BLUE["d"], fs=9.5)
        ax.text(4.35, y + 0.52, act, fontsize=8.5, color=INK, va="center")
    ax.plot([0.5, 0.5], [0.9, 8.4], color=GRAY["m"], lw=1.4)
    ax.text(0.22, 4.6, "模型外", rotation=90, ha="center", va="center",
            fontsize=8.5, color=GRAY["d"])
    ax.text(0.7, 0.15, "六层全在模型外面；按翻车点补层（L5／L6 是缺口）"
            "。权重里只装了推理与工具用法。", fontsize=8.5, color=GRAY["d"])
    return save_fig(fig, "fig_16_1_harness.png")


@figure("16-2", "fig_16_2_agent_loop.png")
def fig_16_2_agent_loop():
    fig, ax = plt.subplots(figsize=(11.0, 4.8))
    ax.set_xlim(0, 11); ax.set_ylim(0, 10); ax.axis("off")
    # L4 编排虚线框
    ax.add_patch(FancyBboxPatch((0.6, 3.3), 9.8, 5.4,
                 boxstyle="round,pad=0.05,rounding_size=0.12",
                 fc="none", ec=ROLE_PURPLE, lw=1.5, ls="--"))
    ax.text(5.5, 9.1, "L4 编排：何时调用模型／重试／中断／升级给人",
            ha="center", fontsize=9.5, color=ROLE_PURPLE)
    boxes = [("$o_t$\n观测", 1.1), ("$b_t$\n信念", 3.6), ("$a_t$\n动作", 6.1), ("$o_{t+1}$\n新观测", 8.6)]
    for txt, x in boxes:
        _box(ax, x, 5.4, 1.7, 1.5, txt, BLUE["l"], BLUE["d"], fs=9.5)
    for x, lab in [(3.25, "L3 记忆"), (5.75, "L1 推理"), (8.25, "L2 工具")]:
        _arr(ax, (x - 0.5, 6.15), (x + 0.4, 6.15), color=GRAY["d"])
        ax.text(x, 7.2, lab, ha="center", fontsize=8, color=GRAY["d"])
    _arr(ax, (9.45, 5.4), (9.45, 3.95), color=GRAY["m"], style="-")
    _arr(ax, (9.45, 3.95), (1.95, 3.95), color=GRAY["m"], style="-")
    _arr(ax, (1.95, 3.95), (1.95, 5.4), color=GRAY["m"])
    ax.text(5.7, 4.3, "下一轮（输出接回输入）", ha="center", fontsize=8.5, color=GRAY["d"])
    # 三种停车信号
    sigs = [("end_turn", "模型判断任务完成"), ("max_turns", "步数上限"),
            ("error_budget", "连续失败超阈值")]
    for i, (k, v) in enumerate(sigs):
        x = 0.9 + i * 3.35
        _box(ax, x, 0.8, 3.0, 1.1, f"{k}\n{v}", RED["l"], RED["d"], fs=8)
    ax.text(5.5, 0.25, "三种停车信号（stopReason）：防死循环与防失控的两道刹车",
            ha="center", fontsize=8.5, color=ROLE_DANGER)
    return save_fig(fig, "fig_16_2_agent_loop.png")


@figure("T4-3", "fig_t4_3_clip_path.png")
def fig_t4_3_clip_path():
    fig, ax = plt.subplots(figsize=(10.6, 5.0))
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
    ax.text(5, 9.6, "CLIP 条件通路：条件在每一层反复注入", ha="center",
            fontsize=11, fontweight="bold", color=INK)
    _box(ax, 0.4, 6.4, 2.2, 1.2, "提示词", GRAY["l"], GRAY["d"], fs=9)
    _box(ax, 3.0, 6.4, 2.6, 1.2, "CLIP 文本塔\n（冻结）", GREEN["l"], GREEN["d"], fs=9)
    _arr(ax, (2.6, 7.0), (3.0, 7.0), color=GRAY["d"])
    _box(ax, 0.4, 3.6, 5.2, 1.6, "c：77 个 token × 768 维\n（文字意图向量）",
         BLUE["l"], BLUE["d"], fs=9)
    _arr(ax, (4.3, 6.4), (3.6, 5.2), color=ROLE_PRIMARY)
    for i, (y, lname) in enumerate([(7.2, "浅层"), (4.6, "中间层"), (2.0, "深层")]):
        _box(ax, 6.6, y, 3.0, 1.9, f"U-Net {lname}\n交叉注意力：\nQ 来自图像，K／V 来自 c",
             BLUE["l"], BLUE["d"], fs=8)
        _arr(ax, (5.6, 4.4), (6.6, y + 0.95), color=ROLE_PRIMARY, rad=0.12)
    ax.text(5.0, 0.9, "条件不只在起点；图像每一步都在“看”文本意图", ha="center",
            fontsize=8.5, color=GRAY["d"])
    return save_fig(fig, "fig_t4_3_clip_path.png")


@figure("T4-5", "fig_t4_5_open_closed.png")
def fig_t4_5_open_closed():
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.2, 4.4))
    for ax in (axL, axR):
        ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
    axL.text(5, 9.4, "开环：放电影", ha="center", fontsize=11,
             fontweight="bold", color=INK)
    for i in range(4):
        _box(axL, 0.8 + i * 2.25, 5.6, 1.75, 1.5, f"画面 {i + 1}", GRAY["l"], GRAY["d"], fs=9)
        if i < 3:
            _arr(axL, (2.55 + i * 2.25, 6.35), (2.85 + i * 2.25, 6.35),
                 color=GRAY["d"])
    axL.text(5, 4.4, "一路播下去；观众不能干预", ha="center", fontsize=9, color=GRAY["d"])
    axL.text(5, 2.6, "误差按步数平方根累积", ha="center", fontsize=8.5, color=ROLE_WARNING)
    axL.text(5, 1.6, "（轨迹越长，漂得越远）", ha="center", fontsize=8, color=GRAY["m"])
    axR.text(5, 9.4, "闭环：玩游戏", ha="center", fontsize=11,
             fontweight="bold", color=INK)
    _box(axR, 3.4, 6.4, 3.2, 1.4, "世界画面 $o_t$", BLUE["l"], BLUE["d"], fs=9.5)
    _box(axR, 3.4, 3.2, 3.2, 1.4, "玩家操作 $a_t$", GREEN["l"], GREEN["d"], fs=9.5)
    _arr(axR, (6.6, 7.0), (7.6, 6.0), color=GRAY["d"], rad=-0.25)
    _arr(axR, (7.6, 6.0), (7.6, 4.5), color=GRAY["d"], style="-")
    _arr(axR, (7.6, 4.5), (6.6, 5.2), color=GRAY["d"], rad=-0.25)
    axR.text(8.35, 5.5, "操作改变\n后续画面", fontsize=8.5, color=GRAY["d"], va="center")
    _arr(axR, (5.0, 6.4), (5.0, 4.6), color=ROLE_PRIMARY)
    axR.text(4.85, 5.5, "看到画面", ha="right", fontsize=8.5, color=ROLE_PRIMARY)
    axR.text(5, 1.9, "要建模动作条件与反馈；状态在环里", ha="center",
             fontsize=8.5, color=GRAY["d"])
    fig.subplots_adjust(wspace=0.05)
    return save_fig(fig, "fig_t4_5_open_closed.png")


@figure("T4-6", "fig_t4_6_studio.png")
def fig_t4_6_studio():
    fig, ax = plt.subplots(figsize=(11.0, 5.2))
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
    ax.text(5, 9.6, "画室挂架：四类技法 × 三把工具刷", ha="center",
            fontsize=11, fontweight="bold", color=INK)
    cols = ["大板刷\n（Transformer）", "勾线笔\n（U-Net）", "海绵滚轮\n（Mamba 一系）"]
    rows = ["晕染（扩散 SDE）", "平涂（流匹配）", "线描（自回归）", "补全（离散扩散）"]
    cells = [
        ["DiT、Sora", "原始 SD", "—"],
        ["SD3", "—", "—"],
        ["LlamaGen、GPT-4", "—", "—"],
        ["MDLM", "—", "—"],
    ]
    x0, y0, cw, ch = 2.6, 1.0, 2.3, 1.55
    for j, cname in enumerate(cols):
        _box(ax, x0 + j * cw, 7.1, cw - 0.15, 1.4, cname, PURPLE["l"], PURPLE["d"], fs=8.5)
    for i, rname in enumerate(rows):
        y = y0 + (3 - i) * ch
        _box(ax, 0.4, y, 2.0, ch - 0.2, rname, BLUE["l"], BLUE["d"], fs=8.5)
        for j in range(3):
            txt = cells[i][j]
            fc = GRAY["xlight"] if txt == "—" else GREEN["l"]
            ec = GRAY["line"] if txt == "—" else GREEN["d"]
            _box(ax, x0 + j * cw, y, cw - 0.15, ch - 0.2, txt, fc, ec, fs=8)
    ax.text(0.4, 0.35, "技法与工具互不绑定（交叉处是代表模型）；海绵滚轮为补记、未进主表。",
            fontsize=8.5, color=GRAY["d"])
    return save_fig(fig, "fig_t4_6_studio.png")



# ---------------------------------------------------------------- 批次 B：数据/几何（8 张）

def _gauss_mix_score(x, y, centers, sig, weights=None):
    """混合高斯密度 p 的 score 场：Σ_i 后验_i · (c_i − x)/var_i。"""
    if weights is None:
        weights = np.ones(len(centers))
    weights = np.asarray(weights, dtype=float)
    logits = []
    for (cx, cy), w in zip(centers, weights):
        var = sig ** 2
        logits.append(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * var) + np.log(w))
    L = np.stack(logits)
    L -= L.max(axis=0, keepdims=True)
    post = np.exp(L)
    post /= post.sum(axis=0, keepdims=True)
    ux = np.zeros_like(x); uy = np.zeros_like(y)
    for (cx, cy), p in zip(centers, post):
        ux += p * (cx - x) / sig ** 2
        uy += p * (cy - y) / sig ** 2
    return ux, uy


@figure("10-1", "fig_10_1_double_descent.png")
def fig_10_1_double_descent():
    """双下降曲线：与 assets/§10-体验实验/double_descent.py 同配方（seed 0）重算。"""
    PS = [10, 20, 40, 60, 80, 90, 95, 100, 105, 110, 120, 150, 200, 400, 800]

    def sweep(noise):
        r = np.random.default_rng(0)
        X, Xt = r.normal(0, 1, (100, 800)), r.normal(0, 1, (5000, 800))
        w = np.zeros(800); w[:3] = 1.0
        y = X @ w + noise * r.normal(size=100)
        yt = Xt @ w + noise * r.normal(size=5000)
        out = []
        for p in PS:
            A = X[:, :p]
            b = np.linalg.solve(A.T @ A + 1e-8 * np.eye(p), A.T @ y)
            out.append(float(np.mean((Xt[:, :p] @ b - yt) ** 2)))
        return out

    mse, ctl = sweep(0.3), sweep(0.01)
    assert abs(mse[7] - 35.202) < 0.01 and abs(mse[-1] - 2.713) < 0.01, "与脚本酒方不一致"
    fig, ax = plt.subplots(figsize=(9.0, 5.0))
    ax.plot(PS, mse, "o-", color=ROLE_PRIMARY, lw=1.8, ms=5, label="噪声 0.3（主实验，15 个实测点）")
    ax.plot(PS, ctl, "s--", color=ROLE_WARNING, lw=1.6, ms=4.5, label="噪声 0.01（对照组，尖峰消失）")
    ax.axvline(100, color=GRAY["m"], ls=":", lw=1.2)
    ax.text(103, 30, "维度 = 样本数 100", fontsize=8.5, color=GRAY["d"])
    ax.set_xscale("log")
    ax.set_xlabel("特征维度（容量轴，对数刻度）", fontsize=9.5)
    ax.set_ylabel("测试 MSE", fontsize=9.5)
    ax.grid(color=GRAY["line"], lw=0.6, alpha=0.7)
    ax.legend(fontsize=8.5, frameon=False)
    return save_fig(fig, "fig_10_1_double_descent.png")


def _droplet_image(n=96):
    y, x = np.mgrid[0:1:n * 1j, 0:1:n * 1j]
    pts = np.column_stack([x.ravel(), y.ravel()])
    body = ((x - 0.5) ** 2 + (y - 0.42) ** 2 <= 0.28 ** 2)
    tip = MplPath([(0.5, 0.96), (0.24, 0.44), (0.76, 0.44)]).contains_points(pts).reshape(n, n)
    img = np.where(body | tip, 1.0, -0.6)
    return (img - img.mean()) / img.std()


@figure("T1-1", "fig_t1_1_ink.png")
def fig_t1_1_ink():
    img = _droplet_image()
    ks = [0.0, 0.30, 0.55, 1.0]
    labels = ["第 0 步：清晰", "第 1 步：泛起细颗粒", "第 100 步：勉强看出轮廓", "第 1000 步：只剩雪花点"]
    rng = np.random.default_rng(11)
    fig, axes = plt.subplots(1, 4, figsize=(11.4, 3.6))
    for ax, k, lab in zip(axes, ks, labels):
        eps = rng.normal(size=img.shape)
        xt = (1 - k) * img + k * eps
        ax.imshow(xt, cmap="gray", vmin=-2.6, vmax=2.6, origin="lower")
        ax.set_title(lab, fontsize=9, color=INK)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_color(GRAY["line"])
    fig.text(0.5, 0.02, "加噪不是模糊（模糊是卷积）；是一勺勺撒随机数（示意）",
             ha="center", fontsize=9, color=GRAY["d"])
    fig.subplots_adjust(wspace=0.06, bottom=0.14)
    return save_fig(fig, "fig_t1_1_ink.png")


@figure("T1-4", "fig_t1_4_peaks.png")
def fig_t1_4_peaks():
    rng = np.random.default_rng(3)
    n = 260
    half = rng.normal(0, 0.5, (n // 2, 2))
    pts = np.vstack([half + [2, 2], -half - [2, 2]])
    schedule = [(0, 1.0, 0.0), (1, 0.61, 0.79), (5, 0.08, 0.996), (50, 0.0, 1.0)]
    fig, axes = plt.subplots(1, 4, figsize=(11.6, 3.4))
    for ax, (t, a, s) in zip(axes, schedule):
        eps = rng.normal(size=pts.shape)
        p = a * pts + s * eps
        ax.scatter(p[:, 0], p[:, 1], s=12, color=ROLE_PRIMARY, alpha=0.55, lw=0)
        ax.set_xlim(-4.6, 4.6); ax.set_ylim(-4.6, 4.6)
        ax.set_aspect("equal")
        ax.set_title(f"t = {t}", fontsize=9, color=INK)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_color(GRAY["line"])
    fig.text(0.5, 0.03, "同一设定（两簇、标准差 0.5）：两峰被抹成一个圆斑（与正文玩具同设定）",
             ha="center", fontsize=9, color=GRAY["d"])
    fig.subplots_adjust(wspace=0.08, bottom=0.16)
    return save_fig(fig, "fig_t1_4_peaks.png")


@figure("T1-5", "fig_t1_5_manifold.png")
def fig_t1_5_manifold():
    fig, ax = plt.subplots(figsize=(9.6, 4.6))
    x = np.linspace(0.4, 9.6, 300)
    yc = 2.4 + 1.1 * np.sin(0.75 * x)
    ax.fill_between(x, yc - 0.55, yc + 0.55, color=BLUE["l"], edgecolor=BLUE["d"], lw=1.2)
    rng = np.random.default_rng(5)
    xi = np.linspace(0.8, 9.2, 26)
    ax.scatter(xi, 2.4 + 1.1 * np.sin(0.75 * xi) + rng.normal(0, 0.16, xi.size),
               s=16, color=ROLE_PRIMARY, alpha=0.75, lw=0)
    ax.plot([2.4, 3.05], [6.0, 3.35], color=ROLE_DANGER, lw=1.6)
    ax.plot([2.4], [6.0], "o", color=ROLE_DANGER, ms=6)
    ax.text(2.15, 6.35, "不在带上的随机点", fontsize=8.5, color=ROLE_DANGER)
    ax.text(6.3, 4.35, "真实图片只占一小条带（数据流形）", fontsize=9, color=BLUE["d"])
    ax.text(6.3, 0.9, "箭头只要在带附近指得对，就够把噪声引回家", fontsize=8.5, color=GRAY["d"])
    ax.set_xlim(0, 10); ax.set_ylim(0, 7.2); ax.axis("off")
    return save_fig(fig, "fig_t1_5_manifold.png")


@figure("T1-6", "fig_t1_6_field.png")
def fig_t1_6_field():
    centers = [(2.0, 2.0), (-2.0, -2.0), (2.0, -1.6)]
    gx, gy = np.meshgrid(np.linspace(-5, 5, 22), np.linspace(-5, 5, 22))
    sx, sy = _gauss_mix_score(gx, gy, centers, 0.9, [0.45, 0.45, 0.10])
    fx = np.linspace(-5, 5, 240)
    FY, FX = np.meshgrid(np.linspace(-5, 5, 240), fx)
    dens = np.zeros_like(FX)
    for cx, cy in centers:
        dens += np.exp(-((FX - cx) ** 2 + (FY - cy) ** 2) / (2 * 0.9 ** 2))
    fig, ax = plt.subplots(figsize=(6.6, 5.6))
    ax.contour(FX, FY, dens, levels=8, colors=GRAY["m"], linewidths=0.8)
    ax.quiver(gx, gy, sx, sy, color=ROLE_PRIMARY, alpha=0.9)
    ax.set_xlabel("第一维", fontsize=9); ax.set_ylabel("第二维", fontsize=9)
    ax.set_title("分数函数：等高线与向量场（指向密度增长最快处）", fontsize=10)
    ax.set_aspect("equal")
    for sp in ax.spines.values():
        sp.set_color(GRAY["line"])
    return save_fig(fig, "fig_t1_6_field.png")


@figure("T1-7", "fig_t1_7_two_sigmas.png")
def fig_t1_7_two_sigmas():
    # 非对称权重（0.7／0.3）让“重心 ≠ 任何一峰”，方向差才读得出来；箭头单位化后对比方向。
    centers = [(2.6, 2.6), (-2.2, -2.2)]
    weights = [0.7, 0.3]
    com = (weights[0] * centers[0][0] + weights[1] * centers[1][0],
           weights[0] * centers[0][1] + weights[1] * centers[1][1])
    gx, gy = np.meshgrid(np.linspace(-5, 5, 16), np.linspace(-5, 5, 16))
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 5.2))
    for ax, sig, title in [(axes[0], 3.0, "σ = 3.0：方向≈指向整体重心（粗略）"),
                           (axes[1], 0.3, "σ = 0.3：方向≈指向最近的数据峰（精细）")]:
        sx, sy = _gauss_mix_score(gx, gy, centers, sig, weights)
        n = np.hypot(sx, sy); n[n == 0] = 1
        ax.quiver(gx, gy, sx / n, sy / n, color=ROLE_PRIMARY, alpha=0.9)
        for (cx, cy), w in zip(centers, weights):
            ax.plot([cx], [cy], "o", color=ROLE_WARNING, ms=7 + 4 * w)
        ax.plot([com[0]], [com[1]], "*", color=ROLE_PURPLE, ms=14)
        ax.text(com[0] + 0.25, com[1] + 0.15, "整体重心", fontsize=8, color=ROLE_PURPLE)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(title, fontsize=10)
        ax.set_aspect("equal")
        for sp in ax.spines.values():
            sp.set_color(GRAY["line"])
    fig.subplots_adjust(wspace=0.08)
    return save_fig(fig, "fig_t1_7_two_sigmas.png")


@figure("T1-8", "fig_t1_8_arrows.png")
def fig_t1_8_arrows():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    rng = np.random.default_rng(9)
    x = np.linspace(0.6, 7.4, 160)
    yc = 2.2 + 0.9 * np.sin(0.8 * x)
    ax.plot(x, yc, color=BLUE["m"], lw=1.2, alpha=0.8)
    ax.scatter(x[::5] + rng.normal(0, 0.05, x[::5].size), yc[::5] + rng.normal(0, 0.12, x[::5].size),
               s=14, color=ROLE_PRIMARY, alpha=0.55, lw=0)
    xi, yi = 3.0, 5.4
    xh, yh = 3.0, 2.85
    ax.plot([xi], [yi], "o", color=ROLE_DANGER, ms=7)
    ax.plot([xh], [yh], "o", color=ROLE_SUCCESS, ms=7)
    _arr(ax, (xi, yi), (xh, yh), color=ROLE_PRIMARY, lw=2.6)
    _arr(ax, (xi, yi), (xi, 0.25), color=ROLE_PURPLE, lw=2.2, ls=(0, (5, 3)))
    ax.text(3.2, 5.6, "噪声观测 x_t", fontsize=9, color=ROLE_DANGER)
    ax.text(3.2, 2.5, "去噪估计（后验均值）", fontsize=9, color=ROLE_SUCCESS)
    ax.text(1.1, 4.3, "去噪方向", fontsize=8.5, color=ROLE_PRIMARY)
    ax.text(0.55, 0.5, "分数方向（更长，差 1/σ_t²）", fontsize=8.5, color=ROLE_PURPLE)
    ax.set_xlim(0, 8); ax.set_ylim(-0.6, 6.8); ax.axis("off")
    return save_fig(fig, "fig_t1_8_arrows.png")


@figure("T1-9", "fig_t1_9_noise_vs_score.png")
def fig_t1_9_noise_vs_score():
    centers = [(2.0, 2.0), (-2.0, -2.0)]
    gx, gy = np.meshgrid(np.linspace(-4.5, 4.5, 15), np.linspace(-4.5, 4.5, 15))
    sx, sy = _gauss_mix_score(gx, gy, centers, 1.0)
    st = 0.7
    fig, ax = plt.subplots(figsize=(6.8, 5.6))
    ax.quiver(gx, gy, sx, sy, color=ROLE_PRIMARY, alpha=0.9, label="分数 s_θ")
    ax.quiver(gx, gy, -st * sx, -st * sy, color=ROLE_WARNING, alpha=0.55, label="预测噪声 ε_θ = −σ_t·s_θ")
    for cx, cy in centers:
        ax.plot([cx], [cy], "o", color=GRAY["d"], ms=6)
    ax.set_title("预测噪声与预测分数：同一信息，差一个缩放", fontsize=10)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect("equal")
    ax.legend(fontsize=8.5, frameon=False, loc="upper right")
    for sp in ax.spines.values():
        sp.set_color(GRAY["line"])
    return save_fig(fig, "fig_t1_9_noise_vs_score.png")


# ---------------------------------------------------------------- 批次 C：对比/序列（3 张）

@figure("T1-3", "fig_t1_3_gauss.png")
def fig_t1_3_gauss():
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.0, 4.3))
    x = np.linspace(-6, 7, 500)
    g1 = np.exp(-((x - 0.4) ** 2) / (2 * 1.0 ** 2))
    g2 = np.exp(-((x - 2.8) ** 2) / (2 * 0.6 ** 2))
    gs = np.exp(-((x - 1.36) ** 2) / (2 * (1.0 ** 2 + 0.6 ** 2)))
    axL.plot(x, g1 / g1.max(), color=ROLE_PRIMARY, lw=1.6, label="两个独立高斯")
    axL.plot(x, g2 / g2.max(), color=ROLE_PRIMARY, lw=1.6)
    axL.plot(x, gs / gs.max(), color=ROLE_WARNING, lw=2.2, label="相加之后：还是高斯")
    axL.set_title("理由一：可处理性（闭式跳步全靠它）", fontsize=10)
    axL.legend(fontsize=8.5, frameon=False)
    axL.set_yticks([]); axL.set_xticks([])
    for sp in axL.spines.values():
        sp.set_color(GRAY["line"])
    x2 = np.linspace(-4, 4, 500)
    gauss = np.exp(-x2 ** 2 / 2)
    b = np.sqrt(0.5)
    lap = np.exp(-np.abs(x2) / b)
    axR.plot(x2, gauss / gauss.max(), color=ROLE_PRIMARY, lw=2.0, label="高斯（方差 = 1）")
    axR.plot(x2, lap / lap.max(), color=GRAY["m"], lw=1.6, ls="--", label="更尖的分布（同方差）")
    axR.set_title("理由二：最大熵（约束下最“不偏心”）", fontsize=10)
    axR.legend(fontsize=8.5, frameon=False)
    axR.set_yticks([]); axR.set_xticks([])
    for sp in axR.spines.values():
        sp.set_color(GRAY["line"])
    fig.subplots_adjust(wspace=0.08)
    return save_fig(fig, "fig_t1_3_gauss.png")


@figure("T4-1", "fig_t4_1_cfg_extrapolation.png")
def fig_t4_1_cfg_extrapolation():
    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    ax.add_patch(FancyBboxPatch((-0.35, -0.5), 2.0, 2.2, boxstyle="round,pad=0.06",
                 fc=GRAY["l"], ec=GRAY["line"], lw=1.2, zorder=0))
    ax.text(0.65, 2.4, "训练分布典型区", fontsize=8.5, color=GRAY["d"], ha="center")
    u = (1.0, 0.0)
    for w, col in [(1, ROLE_SUCCESS), (3, ROLE_PRIMARY), (7.5, ROLE_PRIMARY), (10, ROLE_DANGER)]:
        tip = (u[0], w)
        _arr(ax, (0, 0), tip, color=col, lw=1.8)
        ax.text(u[0] + 0.12, w, f"w = {w}", fontsize=9, color=col)
    ax.plot([u[0]], [u[1]], "o", color=INK, ms=6)
    ax.text(u[0], u[1] - 0.42, "ε_unc（无条件预测）", fontsize=8.5, color=INK, ha="center")
    ax.text(-0.7, 1.45, "w=1 的终点即 ε_cond（不是“无引导”）；w>1 是外推", fontsize=8.5, color=ROLE_SUCCESS)
    ax.set_xlim(-0.8, 2.6); ax.set_ylim(-0.8, 11.0)
    ax.set_xlabel("第一维：无条件预测方向 ε_unc", fontsize=9)
    ax.set_ylabel("第二维：条件修正方向（ε_cond − ε_unc 的倍数）", fontsize=9)
    ax.set_title("CFG 外推：w 拧大 = 沿条件方向走出去", fontsize=10)
    ax.grid(color=GRAY["line"], lw=0.6, alpha=0.6)
    return save_fig(fig, "fig_t4_1_cfg_extrapolation.png")


@figure("T4-4", "fig_t4_4_mask.png")
def fig_t4_4_mask():
    words = ["猫", "坐", "在", "窗台", "上"]
    steps = [
        ("第 0 步：全文完好", [True] * 5),
        ("第 1 步：两个词被遮", [True, False, True, False, True]),
        ("第 2 步：只剩骨架", [False] * 5),
        ("第 3 步：反向填回第一个词", [True, False, False, False, False]),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(11.6, 3.0))
    for ax, (title, vis) in zip(axes, steps):
        ax.set_xlim(0, 5); ax.set_ylim(0, 3); ax.axis("off")
        ax.set_title(title, fontsize=9, color=INK)
        for i, wtxt in enumerate(words):
            x = 0.15 + i * 0.95
            if vis[i]:
                _box(ax, x, 1.0, 0.8, 1.0, wtxt, BLUE["l"], BLUE["d"], fs=10)
            else:
                _box(ax, x, 1.0, 0.8, 1.0, "▢", GRAY["l"], GRAY["l"], fs=10)
    fig.text(0.5, 0.04, "前向：越遮越多；反向：一步步填回来（先填最确定的空）",
             ha="center", fontsize=8.5, color=GRAY["d"])
    fig.subplots_adjust(wspace=0.05, bottom=0.2)
    return save_fig(fig, "fig_t4_4_mask.png")



# ---------------------------------------------------------------- 增量三张（2026-10-14）

@figure("7-1", "fig_7_1_rag_chain.png")
def fig_7_1_rag_chain():
    steps = [
        ("① 切块入库", "文档切成小块\n编码进向量库"),
        ("② 向量检索", "问题变向量\n比余弦远近"),
        ("③ 重排", "初检一批候选\n精排留最相关"),
        ("④ 写进检索内容格", "片段按顺序装好\n连出处一起"),
        ("⑤ 带引用作答", "答案附出处\n查不到就明说"),
    ]
    fig, ax = plt.subplots(figsize=(11.8, 4.0))
    ax.set_xlim(0, 11.8); ax.set_ylim(0, 6.2); ax.axis("off")
    w, gap = 2.02, 0.36
    for i, (name, sub) in enumerate(steps):
        x = 0.25 + i * (w + gap)
        _box(ax, x, 3.4, w, 1.5, name, BLUE["l"] if i % 2 == 0 else BLUE["xl"],
             BLUE["d"], fs=9)
        ax.text(x + w / 2, 2.75, sub, ha="center", va="top", fontsize=8, color=GRAY["d"])
        if i < 4:
            _arr(ax, (x + w + 0.03, 4.15), (x + w + gap - 0.03, 4.15), color=GRAY["d"])
    ax.text(5.9, 5.6, "先检索，再作答：把“装不下、装不起”的部分移出上下文",
            ha="center", fontsize=10, fontweight="bold", color=INK)
    ax.text(5.9, 0.9, "索引更新、权限、召回评估是这条链的工程账（§16）；引用可核查的价值在 §14",
            ha="center", fontsize=8.5, color=GRAY["d"])
    return save_fig(fig, "fig_7_1_rag_chain.png")


@figure("10-2", "fig_10_2_map.png")
def fig_10_2_map():
    qs = [("反常", "§10"), ("凭什么", "§11"), ("可预测", "§12"), ("内部", "§13"), ("边界", "§14")]
    fig, ax = plt.subplots(figsize=(11.2, 4.6))
    ax.set_xlim(0, 11.2); ax.set_ylim(0, 7.0); ax.axis("off")
    ax.text(5.6, 6.5, "规律部五问：先从反常开始", ha="center", fontsize=11,
            fontweight="bold", color=INK)
    w, gap = 1.85, 0.42
    for i, (name, sec) in enumerate(qs):
        x = 0.35 + i * (w + gap)
        fc = GREEN["l"] if i == 0 else BLUE["l"]
        ec = GREEN["d"] if i == 0 else BLUE["d"]
        _box(ax, x, 3.3, w, 1.2, name, fc, ec, fs=10)
        ax.text(x + w / 2, 2.95, sec, ha="center", va="top", fontsize=8.5, color=GRAY["d"])
        if i < 4:
            _arr(ax, (x + w + 0.04, 3.9), (x + w + gap - 0.04, 3.9), color=GRAY["d"])
    subs = ["双下降", "grokking", "涌现"]
    for j, sx in enumerate(subs):
        _box(ax, 0.35 + j * 0.86, 0.9, 0.8, 0.75, sx, ORANGE["l"], ORANGE["d"], fs=7)
    _arr(ax, (0.35 + 1.95 / 2, 3.3), (0.35 + 1.95 / 2, 1.68), color=ROLE_WARNING)
    ax.text(0.35 + 1.95 / 2, 0.35, "第一问下挂三个“不该发生却发生”的现象",
            ha="center", fontsize=8.5, color=GRAY["d"])
    ax.text(7.2, 0.95, "本章只答第一问；其余四问，一章一问", fontsize=8.5, color=GRAY["d"])
    return save_fig(fig, "fig_10_2_map.png")


@figure("13-1", "fig_13_1_tests.png")
def fig_13_1_tests():
    fig, ax = plt.subplots(figsize=(11.4, 4.6))
    ax.set_xlim(0, 11.4); ax.set_ylim(0, 7.0); ax.axis("off")
    ax.text(5.7, 6.5, "解释的三道检验：全过才算解释", ha="center", fontsize=11,
            fontweight="bold", color=INK)
    _box(ax, 0.3, 3.6, 1.7, 1.5, "观测到线索", GRAY["l"], GRAY["d"], fs=9.5)
    gates = [("① 独立数据复现", "换数据、换模型，它还在吗"),
             ("② 干预看行为", "改变特征，行为是否按预测变"),
             ("③ 声明失效条件", "把工具的假设与边界说清楚")]
    w, gap = 2.15, 0.45
    for i, (name, sub) in enumerate(gates):
        x = 2.4 + i * (w + gap)
        _box(ax, x, 3.6, w, 1.5, name, BLUE["l"], BLUE["d"], fs=8.5)
        ax.text(x + w / 2, 3.15, sub, ha="center", va="top", fontsize=7.5, color=GRAY["d"])
        if i == 0:
            _arr(ax, (2.0, 4.35), (x, 4.35), color=GRAY["d"])
        if i < 2:
            _arr(ax, (x + w + 0.04, 4.35), (x + w + gap - 0.04, 4.35), color=GRAY["d"])
    _box(ax, 10.1, 3.6, 1.05, 1.5, "解释", GREEN["l"], GREEN["d"], fs=10)
    _arr(ax, (2.4 + 2 * (w + gap) + w + 0.04, 4.35), (10.1, 4.35), color=ROLE_SUCCESS)
    _arr(ax, (6.08, 3.6), (6.08, 2.0), color=ROLE_DANGER, style="-")
    _arr(ax, (6.08, 2.0), (1.15, 2.0), color=ROLE_DANGER, style="-")
    _arr(ax, (1.15, 2.0), (1.15, 3.6), color=ROLE_DANGER)
    ax.text(3.3, 1.55, "任何一道断了 → 退回标“线索”", fontsize=9, color=ROLE_DANGER)
    ax.text(0.3, 0.7, "起点不是“找到了什么”，而是“观测到线索”；解释要用证据换。",
            fontsize=8.5, color=GRAY["d"])
    return save_fig(fig, "fig_13_1_tests.png")


# ---------------------------------------------------------------- 入口

def main(argv: list[str]) -> int:
    setup_rc()
    want = argv[1:] or list(FIGURES)
    bad = [f for f in want if f not in FIGURES]
    if bad:
        print(f"未知图号：{bad}", file=sys.stderr)
        return 2
    for fid in want:
        _, fn = FIGURES[fid]
        fn()
        print(f"✓ 图 {fid} -> {FIGURES[fid][0]}")
    man = {fid: {"file": f, "func": FIGURES[fid][1].__name__}
           for fid, (f, _) in FIGURES.items()}
    FIGDIR.mkdir(parents=True, exist_ok=True)
    (FIGDIR / "manifest.json").write_text(
        json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"✓ manifest.json（{len(man)} 图）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
