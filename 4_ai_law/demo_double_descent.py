#!/usr/bin/env python3
"""双下降复算：随机特征双下降（《AI规律》§1.5）。

设定：n=100 训练样本、d=800 维标准高斯特征，真实信号只在前 3 维；最小范数最小二乘
（lstsq，含微小岭回归可视为同一极限）；测试集 5000 个新样本。另附低噪声对照
（噪声标准差 0.01，方差 1e-4）。

输出：
  - 里程碑表（stdout，正文表格同源）
  - 轨迹 TSV（--out，默认本目录 demo_double_descent_trace.tsv）：
    generate_figures.fig_ch1_double_descent 直接读该文件绘图

复算：.venv/bin/python 4_ai_law/demo_double_descent.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "demo_double_descent_trace.tsv"
PS = [10, 20, 40, 60, 80, 90, 95, 100, 105, 110, 120, 150, 200, 400, 800]
NOISE_STD = 0.3
CONTROL_STD = 0.01


def run(noise_std: float, seed: int = 0, n: int = 100, d: int = 800, n_test: int = 5000):
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, (n, d))
    Xt = rng.normal(0, 1, (n_test, d))
    w = np.zeros(d)
    w[:3] = 1.0
    y = X @ w + noise_std * rng.normal(size=n)
    yt = Xt @ w + noise_std * rng.normal(size=n_test)
    rows = []
    for p in PS:
        beta, *_ = np.linalg.lstsq(X[:, :p], y, rcond=None)
        te = float(np.mean((Xt[:, :p] @ beta - yt) ** 2))
        tr = float(np.mean((X[:, :p] @ beta - y) ** 2))
        rows.append((p, tr, te))
    return rows


def write_trace(rows, out: Path) -> None:
    lines = ["p\ttrain_mse\ttest_mse"]
    lines += [f"{p}\t{tr:.6f}\t{te:.6f}" for p, tr, te in rows]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="随机特征双下降复算")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    rows = run(NOISE_STD)
    out = Path(args.out)
    write_trace(rows, out)
    print(f"轨迹 → {out}（n=100，d=800，噪声标准差 {NOISE_STD}，seed 0）")
    print("p\t训练 MSE\t测试 MSE")
    for p, tr, te in rows:
        print(f"{p}\t{tr:.3f}\t\t{te:.3f}")

    ctrl = run(CONTROL_STD)
    cmap = {p: te for p, _, te in ctrl}
    print(f"\n对照（噪声标准差 {CONTROL_STD}，方差 1e-4）："
          f"p=100 {cmap[100]:.3f}；p=800 {cmap[800]:.3f}；峰值 {max(cmap.values()):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
