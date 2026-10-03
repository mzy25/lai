#!/usr/bin/env python3
"""EoS 复算：edge of stability（《AI规律》§2.5）。

固定设置（与正文一致）：2 输入-24 隐藏（tanh）-1 输出的小网络，16 个采样点上的
全批量 MSE，梯度下降步长 eta=0.5（稳定性上限 2/eta=4）。
Hessian 最大特征值（锐度）用幂迭代＋中心差分 Hessian-向量积估算。

输出：
  - 里程碑表（stdout，正文表格同源）
  - 逐步轨迹 TSV（--out，默认本目录 demo_edge_of_stability_trace.tsv），
    generate_figures.fig_ch2_edge_of_stability 直接读该文件绘图

复算：.venv/bin/python 4_ai_law/demo_edge_of_stability.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "demo_edge_of_stability_trace.tsv"
MILESTONES = (0, 30, 60, 100, 300, 600)
DIVERGE_LIMIT = 1e6


def make_data(n: int = 16, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    X = rng.uniform(-1.0, 1.0, size=(n, 2))
    y = np.sin(np.pi * X[:, 0]) * np.cos(np.pi * X[:, 1])
    return X, y.reshape(-1, 1)


class Net:
    def __init__(self, h: int = 24, seed: int = 1, wscale: float = 0.24):
        rng = np.random.default_rng(seed)
        self.W1 = rng.normal(0.0, wscale, (h, 2))
        self.b1 = np.zeros(h)
        self.W2 = rng.normal(0.0, wscale, (1, h))
        self.b2 = np.zeros(1)

    def params(self) -> list[np.ndarray]:
        return [self.W1, self.b1, self.W2, self.b2]

    def set_params(self, params: list[np.ndarray]) -> None:
        self.W1, self.b1, self.W2, self.b2 = [q.copy() for q in params]

    def loss_and_grad(self, X: np.ndarray, y: np.ndarray) -> tuple[float, list[np.ndarray]]:
        n = X.shape[0]
        z = X @ self.W1.T + self.b1
        a = np.tanh(z)
        out = a @ self.W2.T + self.b2
        r = out - y
        loss = float(np.mean(r**2))
        dout = 2.0 * r / n
        gW2 = dout.T @ a
        gb2 = dout.sum(axis=0)
        da = dout @ self.W2
        dz = da * (1.0 - a**2)
        gW1 = dz.T @ X
        gb1 = dz.sum(axis=0)
        return loss, [gW1, gb1, gW2, gb2]


def lam_max(net: Net, X: np.ndarray, y: np.ndarray, iters: int = 25, seed: int = 0) -> float:
    """Hessian 最大特征值：幂迭代 + 中心差分 HVP。"""
    rng = np.random.default_rng(seed)
    v = [rng.normal(size=q.shape) for q in net.params()]
    norm = np.sqrt(sum((vi**2).sum() for vi in v))
    v = [vi / norm for vi in v]
    eps = 1e-5
    lam = float("nan")
    for _ in range(iters):
        p = net.params()
        net.set_params([q + eps * vi for q, vi in zip(p, v)])
        _, gp = net.loss_and_grad(X, y)
        net.set_params([q - eps * vi for q, vi in zip(p, v)])
        _, gm = net.loss_and_grad(X, y)
        net.set_params(p)
        Hv = [(a - b) / (2.0 * eps) for a, b in zip(gp, gm)]
        lam = float(sum((vi * hi).sum() for vi, hi in zip(v, Hv)))
        hnorm = np.sqrt(sum((hi**2).sum() for hi in Hv))
        if not np.isfinite(hnorm) or hnorm == 0.0:
            return float("nan")
        v = [hi / hnorm for hi in Hv]
    return lam


def run(steps: int, eta: float, seed: int, wscale: float, n: int) -> np.ndarray:
    X, y = make_data(n)
    net = Net(seed=seed, wscale=wscale)
    rows: list[tuple[int, float, float]] = []
    for k in range(steps + 1):
        loss, grad = net.loss_and_grad(X, y)
        rows.append((k, loss, lam_max(net, X, y)))
        if not np.isfinite(loss) or loss > DIVERGE_LIMIT:
            raise SystemExit(f"训练在 step {k} 发散（loss={loss}）——调整 wscale/seed 后重跑")
        if k == steps:
            break
        p = net.params()
        net.set_params([q - eta * gi for q, gi in zip(p, grad)])
    return np.array(rows, dtype=float)


def write_trace(trace: np.ndarray, out: Path) -> None:
    lines = ["step\tloss\tsharpness"]
    lines += [f"{int(k)}\t{loss:.6f}\t{lam:.6f}" for k, loss, lam in trace]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="edge of stability 复算")
    ap.add_argument("--steps", type=int, default=600)
    ap.add_argument("--eta", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--wscale", type=float, default=0.24)
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    trace = run(args.steps, args.eta, args.seed, args.wscale, args.n)
    out = Path(args.out)
    write_trace(trace, out)

    print(f"轨迹 → {out}（{len(trace)} 步；eta={args.eta}，2/eta={2/args.eta:g}）")
    print("步数\t训练损失\t锐度")
    for k, loss, lam in trace:
        if int(k) in MILESTONES:
            print(f"{int(k)}\t{loss:.3f}\t\t{lam:.2f}")
    tail = trace[10:, 2]
    print(f"锐度 10..{args.steps} 步：min={tail.min():.2f} max={tail.max():.2f} mean={tail.mean():.2f}")
    print(f"损失：起点 {trace[0, 1]:.3f}，终点 {trace[-1, 1]:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
