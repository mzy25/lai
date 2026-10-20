# 拟合公开曲线并外推（§12 动手配对）
# 方法：ℓ(D)=ℓ∞+c·D^-α。地板 ℓ∞ 两条路：auto=网格扫（0 到最小损失之下，按窗内
# 残差选格）；已知=实验设计给出的地板，只剩 log(ℓ-ℓ∞) 对 log D 的线性回归。纯 NumPy。
# 练习一：真实公开曲线——OLMo-2-7B 的 TriviaQA-wiki 评测交叉熵（wandb 公开日志），
#         只用 ≤1.0T token 的评测点拟合，外推扣住的后段（留一法口径：目标点不参与拟合）。
# 练习二：同一段代码拟合《AI规律》ch4 书中表。地板已知版（0.09=噪声方差）做主拟合
#         ＋留一法诊断；auto 网格版做对照（R² 更高，外推全落空）。断言只钉在书中表上。
import csv
import numpy as np


def fit(D, L, l0="auto", n_grid=401):
    if l0 == "auto":
        cands = np.linspace(0.0, L.min() - 1e-4, n_grid)
    else:
        cands = np.array([float(l0)])
    x = np.log(D)
    best = None
    for f in cands:
        y = np.log(L - f)
        A = np.vstack([x, np.ones_like(x)]).T
        (s, i), *_ = np.linalg.lstsq(A, y, rcond=None)
        sse = float(((y - A @ np.array([s, i])) ** 2).sum())
        if best is None or sse < best[0]:
            r2 = 1 - sse / float(((y - y.mean()) ** 2).sum())
            best = (float(f), float(-s), float(np.exp(i)), r2)
    return best


def predict(p, d):
    return p[0] + p[2] * d ** (-p[1])


def main():
    rows = [(float(r["tokens"]), float(r["trivia_qa_wiki_ce"]))
            for r in csv.DictReader(open("raw/olmo2_7b_trivia_ce.csv", encoding="utf-8"))]
    D = np.array([d for d, _ in rows])
    L = np.array([l for _, l in rows])
    print("== 练习一：真实公开曲线（OLMo-2-7B TriviaQA-wiki 评测交叉熵）==")
    print("数据：%d 个评测点，%.3e -> %.3e tokens，CE %.3f -> %.3f"
          % (len(D), D[0], D[-1], L[0], L[-1]))
    for cut in [5e11, 1e12, 1.5e12]:
        m = D <= cut
        f, a, c, r2 = fit(D[m], L[m])
        print("拟合窗 ≤%.1e tokens：%d 点，ℓ∞=%.4f，α=%.4f，R²=%.4f"
              % (cut, int(m.sum()), f, a, r2))
    m = D <= 1e12
    f, a, c, r2 = fit(D[m], L[m])
    print("留出外推（拟合窗 ≤1.0T；目标点扣住，不参与拟合）：")
    for tgt in [2e12, 3e12, 3.8923e12]:
        i = int(np.argmin(np.abs(D - tgt)))
        pred = predict((f, a, c), D[i])
        print("  D=%.4e：预测 %.4f，实测 %.4f，相对误差 %.2f%%"
              % (D[i], pred, L[i], abs(pred - L[i]) / L[i] * 100))

    print()
    print("== 练习二（自对账）：《AI规律》ch4 书中表 ==")
    P = np.array([8.0, 16, 32, 64, 128, 256, 512, 1024])
    BL = np.array([0.538, 0.379, 0.274, 0.212, 0.169, 0.139, 0.120, 0.111])
    bm = P <= 64
    f, a, c, r2 = fit(P[bm], BL[bm], l0=0.09)
    print("地板已知版（ℓ∞=0.09=噪声方差）：α=%.4f，c=%.4f，R²=%.4f（理论 α=0.6；旧版 0.63）"
          % (a, c, r2))
    ok = abs(a - 0.63) <= 0.05
    for p_, act in zip([128, 256, 512, 1024], [0.169, 0.139, 0.120, 0.111]):
        pred = predict((f, a, c), float(p_))
        err = abs(pred - act) / act
        print("  p=%4d：预测 %.4f，实测 %.4f，相对误差 %.2f%%" % (p_, pred, act, err * 100))
        ok &= err <= 0.05
    print("  留一法诊断（扣一个拟合点，重估 α、c，回测被扣点）：")
    for j in range(4):
        keep = np.array([k for k in range(4) if k != j])
        f2, a2, c2, _ = fit(P[bm][keep], BL[bm][keep], l0=0.09)
        pred = predict((f2, a2, c2), P[bm][j])
        print("    扣 p=%-4d 预测 %.4f，实测 %.4f，残差 %.2f%%"
              % (P[bm][j], pred, BL[bm][j], abs(pred - BL[bm][j]) / BL[bm][j] * 100))
    f, a, c, r2 = fit(P[bm], BL[bm])
    print("对照：auto 网格选地板（练习一的方法直接搬来）→ ℓ∞=%.4f，α=%.4f，R²=%.4f"
          % (f, a, r2))
    for p_, act in zip([128, 1024], [0.169, 0.111]):
        pred = predict((f, a, c), float(p_))
        print("    p=%4d：预测 %.4f，实测 %.4f，相对误差 %.2f%%"
              % (p_, pred, act, abs(pred - act) / act * 100))
    print("自对账断言：地板已知版 α≈0.63、外推误差≤5%% → %s" % ("PASS" if ok else "FAIL"))


if __name__ == "__main__":
    main()
