# 产出图两张（仅画图，数字全部来自 fit_and_extrapolate.py 的口径）
# fig_olmo_fit.png：真实曲线 + ≤1T 拟合线外推到 3.9T + 扣住点误差标注
# fig_book_table.png：书中表 8 点 + 固定地板 0.09 的拟合线与外推段
import csv
import numpy as np

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

from fit_and_extrapolate import fit, predict

rows = [(float(r["tokens"]), float(r["trivia_qa_wiki_ce"]))
        for r in csv.DictReader(open("raw/olmo2_7b_trivia_ce.csv", encoding="utf-8"))]
D = np.array([d for d, _ in rows])
L = np.array([l for _, l in rows])
m = D <= 1e12
f, a, c, r2 = fit(D[m], L[m])
dd = np.logspace(np.log10(D[0]), np.log10(D[-1]), 200)

fig, ax = plt.subplots(figsize=(7, 4.2))
ax.plot(D[m], L[m], ".", ms=2, color="0.6", label="参与拟合的评测点（≤1.0T token）")
ax.plot(D[~m], L[~m], ".", ms=3, color="tab:blue", label="留出点（>1.0T token）")
ax.plot(dd, predict((f, a, c), dd), "-", color="tab:red", lw=1.5,
        label="拟合：ℓ∞=%.3f，α=%.3f（外推段）" % (f, a))
for tgt, off in [(2e12, (8, 10)), (3e12, (-48, 12)), (3.8923e12, (8, -14))]:
    i = int(np.argmin(np.abs(D - tgt)))
    err = abs(predict((f, a, c), D[i]) - L[i]) / L[i] * 100
    ax.annotate("%.2f%%" % err, (D[i], L[i]), textcoords="offset points",
                xytext=off, fontsize=8, color="tab:blue")
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("训练 token 数（OLMo-2-7B，stage 1）")
ax.set_ylabel("TriviaQA-wiki 评测交叉熵")
ax.set_title("≤1.0T token 拟合，外推至 3.9T（公开训练日志）")
ax.legend(fontsize=7, loc="upper right")
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("fig_olmo_fit.png", dpi=150)
print("fig_olmo_fit.png written")

P = np.array([8.0, 16, 32, 64, 128, 256, 512, 1024])
BL = np.array([0.538, 0.379, 0.274, 0.212, 0.169, 0.139, 0.120, 0.111])
bm = P <= 64
f2, a2, c2, r22 = fit(P[bm], BL[bm], l0=0.09)
pp = np.logspace(np.log10(8), np.log10(1024), 100)
fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(P[bm], BL[bm], "o", ms=5, color="tab:blue", label="实测（p≤64，参与拟合）")
ax.plot(P[~bm], BL[~bm], "s", ms=5, color="tab:green", label="实测（p≥128，留出）")
ax.plot(pp, predict((f2, a2, c2), pp), "-", color="tab:red", lw=1.5,
        label="拟合：ℓ∞=0.09（噪声地板），α=%.3f" % a2)
ax.axhline(0.09, ls=":", color="0.4", lw=1, label="不可约损失 0.09")
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("模型规模 p（学生：线性回归）")
ax.set_ylabel("测试损失")
ax.set_title("玩具表：4 点拟合、后 4 点外推（地板 0.09）")
ax.legend(fontsize=7)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("fig_book_table.png", dpi=150)
print("fig_book_table.png written")
