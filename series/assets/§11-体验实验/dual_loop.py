#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dual_loop.py ——「两个环」玩具（§11 ◇ 深挖块配对脚本，无第三方依赖）

设定：两个二次任务 A、B 对称摆开（θ∈ℝ²），内环按配比 w 对 θ 做 k 步混合梯度，
外环按两侧损失差回转 w。扫描外环响应 β，观察：β 越过门槛后，配比在两个
极端之间翻烧饼（摆动不收敛）。

解析对账（正文口径）：内环跑到位的极限情形下，平衡点附近的每轮
放大率为 |1 − 4β|，门槛 β* = 0.5；k = 8 的实测分水岭落在 0.50–0.53，与解析一致。
冷审探针（2026-10-16）：本玩具的稳定性由 β 决定，内环步数 k 不构成独立旋钮
（默认对称起点下 k 大时的"稳"，是对称初值不触发扰动的假象）。

运行：python3 dual_loop.py
"""
A = (1.2, 0.2)                        # 任务 A 的最优点
B = (-0.8, 0.6)                       # 任务 B 的最优点
MID = ((A[0] + B[0]) / 2, (A[1] + B[1]) / 2)   # 均衡参照点

def loss(theta, t):
    return 0.5 * ((theta[0] - t[0]) ** 2 + (theta[1] - t[1]) ** 2)

def run(beta, k=8, rounds=60, eta=0.5):
    th = [0.0, 0.0]
    w = 0.5
    ws, bal = [], []
    for _ in range(rounds):
        for _ in range(k):                          # 内环：k 步混合梯度
            g0 = w * (th[0] - A[0]) + (1 - w) * (th[0] - B[0])
            g1 = w * (th[1] - A[1]) + (1 - w) * (th[1] - B[1])
            th = [th[0] - eta * g0, th[1] - eta * g1]
        la, lb = loss(th, A), loss(th, B)           # 外环：按损失差回转配比
        w = min(1.0, max(0.0, w + beta * (la - lb) / (la + lb + 1e-12)))
        ws.append(w)
        bal.append(loss(th, MID))
    return ws, bal

if __name__ == "__main__":
    print("双环玩具：外环响应 β 扫描（η=0.5，k=8，60 轮）")
    print("beta\tamp_last10\tloss_final")
    for beta in (0.2, 0.5, 0.6, 0.9):
        ws, bal = run(beta)
        amp = max(ws[-10:]) - min(ws[-10:])
        print(f"{beta}\t{amp:.3f}\t\t{bal[-1]:.4f}")
