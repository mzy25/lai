#!/usr/bin/env python3
"""故障曲线诊断：edge of stability 教学版（§11 体验实验）。

改造自旧版五篇 tag `five-books-final` 的 4_ai_law/demo_edge_of_stability.py（2-24-1 tanh 小网络，16 个采样点，
固定 seed：数据 0／网络 1／wscale 0.24）。教学版相对源 demo 的六处增补：
  1. 批大小扫描：mini-batch SGD，batch ∈ {4, 8, 16}（16=全批量），固定 600 步，
     在独立的验证集（64 点，seed 7）上记录末段验证损失；
     读数"批越小，末态锐度越低"。（玩具只有 16 个样本：有放回抽 64 与全批量
     几乎无差别，所以扫描档取 4/8/16——这本身是个诚实读数。）
  2. 故障注入四组预设（诊断卡）：
       healthy      全批量 η=0.5   —— 健康的 EoS：损失总体降，锐度在 2/η=4 附近震荡
       lr_too_big   全批量 η=0.8   —— 学习率过大：2/η=2.5 低于初始锐度，训练发散
       lr_too_small 全批量 η=0.02  —— 学习率过小：蜗牛曲线
       small_batch  批 4  η=0.5   —— 小批量噪声把解压平：末态锐度远低于 2/η
  3. 线性缩放对照：批 4／η 0.125／2400 步 vs 批 16／η 0.5／600 步
     （样本数同为 9600），看两条损失曲线是否大体同行；
     再加一组"线性缩放建议值"：批若从 4 提到 16，η 要 0.5→2.0，本玩具立刻发散
     （2/η=1）——线性缩放的方向与稳定性边界 2/η 的正面相撞。
  4. 锐度只在里程碑处计算（0/30/60/100/300/600 或 0/50/100/200/300/450/600），
     正文明示"锐度是抽样读数"。
  5. 复算断言：healthy 组里程碑值必须等于正文表（旧版逐点四舍五入值）；
     批大小-锐度单调性断言。
  6. 题面：三张诊断卡的读数汇总，供"给曲线→下诊断"教学环节使用。

用法：python fault_curve_diagnosis.py
输出：trace_*.tsv、fig_*.png、stdout 里程碑表（逐字留档 run_log.txt）
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DIVERGE_LIMIT = 1e6
MILESTONES_HEALTHY = (0, 30, 60, 100, 300, 600)
MILESTONES = (0, 50, 100, 200, 300, 450, 600)

# healthy 组里程碑断言值（旧版正文表，见 §11.素材挖掘笔记 5a：已逐点核对一致）
EXPECTED = {
    0: (0.314, 3.88),
    30: (0.289, 4.00),
    60: (0.335, 4.58),
    100: (0.155, 3.43),
    300: (0.064, 4.12),
    600: (0.037, 3.97),
}


def make_data(n: int = 16, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    X = rng.uniform(-1.0, 1.0, size=(n, 2))
    y = np.sin(np.pi * X[:, 0]) * np.cos(np.pi * X[:, 1])
    return X, y.reshape(-1, 1)


class Net:
    """2 输入 - 24 隐藏（tanh）- 1 输出，与源 demo 完全同构。"""

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
    """Hessian 最大特征值（锐度）：幂迭代 + 中心差分 HVP，与源 demo 同法。"""
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


def run(name: str, steps: int, eta: float, batch: int,
        seed_batch: int = 123, milestones: tuple[int, ...] = MILESTONES) -> dict:
    """跑一组配置；返回轨迹（每步 loss/val_loss，里程碑处锐度）与汇总。"""
    X, y = make_data()
    Xv, yv = make_data(n=64, seed=7)  # 独立验证集
    n = X.shape[0]
    net = Net()
    rng = np.random.default_rng(seed_batch)
    rows: list[tuple[int, float, float, float]] = []  # step, loss, sharpness(nan=未测), val
    diverged_at: int | None = None
    for k in range(steps + 1):
        loss, _ = net.loss_and_grad(X, y)
        val, _ = net.loss_and_grad(Xv, yv)
        sharp = lam_max(net, X, y) if k in milestones else float("nan")
        rows.append((k, loss, sharp, val))
        if not np.isfinite(loss) or loss > DIVERGE_LIMIT:
            diverged_at = k
            break
        if k == steps:
            break
        if batch >= n:
            Xb, yb = X, y  # 全批量（与源 demo 一致，无放回）
        else:
            idx = rng.integers(0, n, size=batch)  # 小批量：有放回抽样
            Xb, yb = X[idx], y[idx]
        _, grad = net.loss_and_grad(Xb, yb)
        p = net.params()
        net.set_params([q - eta * gi for q, gi in zip(p, grad)])
    tail_val = [r[3] for r in rows[-100:]]
    final_sharp = [r[2] for r in rows if not np.isnan(r[2])][-1]
    summary = {
        "name": name, "batch": batch, "eta": eta, "steps": steps,
        "final_loss": rows[-1][1], "final_val": float(np.mean(tail_val)),
        "final_sharp": final_sharp, "diverged_at": diverged_at,
    }
    write_trace(rows, HERE / f"trace_{name}.tsv")
    return {"rows": rows, "summary": summary}


def write_trace(rows: list[tuple[int, float, float, float]], out: Path) -> None:
    lines = ["step\tloss\tsharpness\tval_loss"]
    for k, loss, sharp, val in rows:
        s = f"{sharp:.6f}" if not np.isnan(sharp) else ""
        lines.append(f"{k}\t{loss:.6f}\t{s}\t{val:.6f}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_milestones(tag: str, rows: list[tuple[int, float, float, float]],
                     milestones: tuple[int, ...]) -> None:
    print(f"[{tag}] 步数\t训练损失\t锐度\t验证损失")
    for k, loss, sharp, val in rows:
        if k in milestones:
            s = f"{sharp:.2f}" if not np.isnan(sharp) else "-"
            print(f"  {k}\t{loss:.3f}\t{s}\t{val:.3f}")


def main() -> int:
    results: dict[str, dict] = {}

    print("=" * 64)
    print("卡 A（健康基线）：全批量 batch=16，η=0.5，600 步（EoS 里程碑对账）")
    r = run("healthy", 600, 0.5, 16, milestones=MILESTONES_HEALTHY)
    results["healthy"] = r
    print_milestones("healthy", r["rows"], MILESTONES_HEALTHY)
    got = {k: (loss, sharp) for k, loss, sharp, _ in r["rows"] if k in EXPECTED}
    for k, (el, es) in EXPECTED.items():
        gl, gs = got[k]
        assert round(gl, 3) == el and round(gs, 2) == es, (
            f"里程碑 {k} 对账失败：实测 {gl:.6f}/{gs:.6f}，正文表 {el}/{es}")
    print("  断言 PASS：里程碑与正文表逐点一致")
    print(f"  末态：损失 {r['summary']['final_loss']:.3f}，"
          f"锐度 {r['summary']['final_sharp']:.2f}，末段验证损失 {r['summary']['final_val']:.3f}")

    print("=" * 64)
    print("卡 B（lr 过大）：全批量，η=0.8（2/η=2.5 < 初始锐度 3.88）")
    r = run("lr_too_big", 200, 0.8, 16)
    results["lr_too_big"] = r
    s = r["summary"]
    if s["diverged_at"] is not None:
        print(f"  第 {s['diverged_at']} 步 loss 超过 1e6，训练发散")
    print("  里程碑处锐度读数见 trace_lr_too_big.tsv（损失早已起飞）")

    print("=" * 64)
    print("卡 C（lr 过小）：全批量，η=0.02（蜗牛曲线）")
    r = run("lr_too_small", 600, 0.02, 16)
    results["lr_too_small"] = r
    print_milestones("lr_too_small", r["rows"], MILESTONES)
    print(f"  600 步只从 0.314 降到 {r['summary']['final_loss']:.3f}")

    print("=" * 64)
    print("卡 D（小批量噪声）：批 4（有放回），η=0.5")
    r = run("small_batch", 600, 0.5, 4)
    results["small_batch"] = r
    print_milestones("small_batch", r["rows"], MILESTONES)
    print(f"  末态锐度 {r['summary']['final_sharp']:.2f}（远低于 2/η=4），"
          f"末段验证损失 {r['summary']['final_val']:.3f}")

    print("=" * 64)
    print("批大小扫描：batch ∈ {4, 8, 16}，η=0.5，600 步（16=全批量）")
    scan = {}
    for b in (4, 8, 16):
        r = run(f"batch{b}", 600, 0.5, b)
        scan[b] = r["summary"]
        print(f"  批 {b:3d}：末态锐度 {r['summary']['final_sharp']:.2f}，"
              f"末段验证损失 {r['summary']['final_val']:.3f}")
    sh = [scan[b]["final_sharp"] for b in (4, 8, 16)]
    assert sh[0] < sh[1] < sh[2], f"批大小-锐度单调性不成立：{sh}"
    print(f"  断言 PASS：批越小，末态锐度越低（{sh[0]:.2f} < {sh[1]:.2f} < {sh[2]:.2f}）")

    print("=" * 64)
    print("线性缩放对照：批 4／η 0.125／2400 步 vs 批 16／η 0.5／600 步（样本数同为 9600）")
    r4 = run("scaling_b4", 2400, 0.125, 4)
    results["scaling_b4"] = r4
    r16 = results["healthy"]
    print(f"  批 4 组终点：训练损失 {r4['summary']['final_loss']:.3f}，"
          f"锐度 {r4['summary']['final_sharp']:.2f}（2/η=16）")
    print(f"  批 16 组终点：训练损失 {r16['summary']['final_loss']:.3f}，"
          f"锐度 {r16['summary']['final_sharp']:.2f}（2/η=4）")

    print("=" * 64)
    print("线性缩放的建议值在本玩具撞墙：批 4→16 则 η 要 0.5→2.0，全批量试 η=2.0")
    r = run("scaling_capped", 200, 2.0, 16)
    results["scaling_capped"] = r
    s = r["summary"]
    if s["diverged_at"] is not None:
        print(f"  第 {s['diverged_at']} 步发散（2/η=1，远低于初始锐度 3.88）")

    make_figs(results, scan)
    print("=" * 64)
    print("图已产出：fig_cards.png（四卡诊断）／fig_batch_scan.png（批大小扫描）／"
          "fig_scaling_pair.png（线性缩放对照）")
    return 0


def make_figs(results: dict, scan: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
# 中文字体：按环境自动挑选（Windows 用微软雅黑，Colab 用 Noto Sans CJK）
    from matplotlib import font_manager
    avail = {f.name for f in font_manager.fontManager.ttflist}
    cjk = [f for f in ['Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC',
                       'Noto Sans CJK JP', 'WenQuanYi Micro Hei'] if f in avail]
    plt.rcParams['font.sans-serif'] = cjk + plt.rcParams['font.sans-serif']
    plt.rcParams['axes.unicode_minus'] = False

    # 图 1：四张诊断卡
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    cards = [
        ("healthy", "卡 A 健康基线：批=16，η=0.5（边缘稳定）"),
        ("lr_too_big", "卡 B 学习率过大：批=16，η=0.8"),
        ("lr_too_small", "卡 C 学习率过小：批=16，η=0.02"),
        ("small_batch", "卡 D 小批量：批=4，η=0.5"),
    ]
    for ax, (key, title) in zip(axes.flat, cards):
        rows = results[key]["rows"]
        steps = [r_[0] for r_ in rows]
        loss = [min(r_[1], 1.0) for r_ in rows]  # 发散组截到 1 便于同图读
        ms = [(r_[0], r_[2]) for r_ in rows if not np.isnan(r_[2])]
        ax.plot(steps, loss, lw=1, label="训练损失（截到 1）")
        if ms:
            ax.plot([m[0] for m in ms], [min(m[1], 8) for m in ms], "o-", lw=1,
                    label="里程碑锐度")
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("步数")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7)
    fig.suptitle("故障曲线诊断：四张训练卡（2-24-1 tanh，16 个样本）")
    fig.tight_layout()
    fig.savefig(HERE / "fig_cards.png", dpi=130)
    plt.close(fig)

    # 图 2：批大小扫描
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.6))
    bs = [4, 8, 16]
    ax1.bar([str(b) for b in bs], [scan[b]["final_sharp"] for b in bs])
    ax1.set_title("末态锐度 vs 批大小（η=0.5）")
    ax1.set_xlabel("批大小")
    ax1.grid(alpha=0.3, axis="y")
    ax2.bar([str(b) for b in bs], [scan[b]["final_val"] for b in bs])
    ax2.set_title("验证损失（末 100 步均值）")
    ax2.set_xlabel("批大小")
    ax2.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(HERE / "fig_batch_scan.png", dpi=130)
    plt.close(fig)

    # 图 3：线性缩放对照（按看过的样本数对齐横轴）
    fig, ax = plt.subplots(figsize=(6.5, 4))
    rows4 = results["scaling_b4"]["rows"]
    rows16 = results["healthy"]["rows"]
    ax.plot([r_[0] * 4 for r_ in rows4], [r_[1] for r_ in rows4], lw=1,
            label="批=4，η=0.125，跑 2400 步")
    ax.plot([r_[0] * 16 for r_ in rows16], [r_[1] for r_ in rows16], lw=1,
            label="批=16，η=0.5，跑 600 步")
    ax.set_xlabel("看过的样本数")
    ax.set_ylabel("训练损失")
    ax.set_title("线性缩放对拍：两条轨迹大体同行")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(HERE / "fig_scaling_pair.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())
